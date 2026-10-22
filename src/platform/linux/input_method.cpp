/**
 * @file src/platform/linux/input_method.cpp
 * @brief Definitions for the Linux input method bridge.
 */

// standard includes
#include <cerrno>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <string>
#include <string_view>

// platform includes
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/un.h>
#include <unistd.h>

// local includes
#include "src/logging.h"
#include "input_method.h"

using namespace std::literals;

namespace input_method {
  namespace {
    constexpr auto socket_dir_name = "sunshine-input";  ///< Extension socket directory name.
    constexpr auto socket_file_name = "sunshine-input.sock";  ///< Extension socket file name.

    /// Bounded wait for the extension to accept the text, in seconds.
    constexpr int socket_timeout_seconds = 1;

    /// Session record: true while a streaming session owns the bridge.
    bool session_active = false;

    /**
     * @brief Write a buffer to a socket, retrying on partial writes.
     *
     * @param fd Socket file descriptor.
     * @param data Bytes to write.
     * @return True when every byte was written.
     */
    bool write_all(int fd, std::string_view data) {
      std::size_t written = 0;
      while (written < data.size()) {
        const auto count = ::send(fd, data.data() + written, data.size() - written, MSG_NOSIGNAL);
        if (count > 0) {
          written += static_cast<std::size_t>(count);
          continue;
        }
        if (count < 0 && errno == EINTR) {
          continue;
        }
        // Everything else, including a send timeout, means the extension is not
        // draining the socket.
        return false;
      }
      return true;
    }
  }  // namespace

  namespace detail {
    std::filesystem::path runtime_dir() {
      if (const char *runtime = std::getenv("XDG_RUNTIME_DIR"); runtime && *runtime) {
        return std::filesystem::path {runtime};
      }
      return std::filesystem::path {"/tmp"};
    }

    std::filesystem::path socket_dir() {
      // Same layout the fcitx5 extension creates (fcitx5-plugin/src/sunshineinput.cpp),
      // including its /tmp fallback when the session sets no XDG_RUNTIME_DIR.
      if (const char *runtime = std::getenv("XDG_RUNTIME_DIR"); runtime && *runtime) {
        return std::filesystem::path {runtime} / socket_dir_name;
      }
      return std::filesystem::path {"/tmp"} / (std::string {socket_dir_name} + "-"s + std::to_string(::getuid()));
    }

    std::filesystem::path socket_path() {
      return socket_dir() / socket_file_name;
    }

    bool plugin_present(const std::filesystem::path &socket_file) {
      std::error_code ec;
      if (std::filesystem::exists(socket_file, ec)) {
        return true;
      }
      ec.clear();
      const auto parent = socket_file.parent_path();
      if (!parent.empty() && std::filesystem::is_directory(parent, ec)) {
        return true;
      }
      return false;
    }

    std::string encode_frame(std::string_view text) {
      const auto size = static_cast<std::uint32_t>(text.size());
      std::string frame;
      frame.reserve(sizeof(size) + text.size());
      frame.push_back(static_cast<char>((size >> 24) & 0xFFU));
      frame.push_back(static_cast<char>((size >> 16) & 0xFFU));
      frame.push_back(static_cast<char>((size >> 8) & 0xFFU));
      frame.push_back(static_cast<char>(size & 0xFFU));
      frame.append(text);
      return frame;
    }

    submit_result_e parse_reply(char reply) {
      if (reply == 'K') {
        return submit_result_e::submitted;
      }
      if (reply == 'E') {
        return submit_result_e::rejected;
      }
      BOOST_LOG(warning) << "input method: unknown reply byte from the fcitx5 extension: "sv << static_cast<int>(reply);
      return submit_result_e::rejected;
    }

    submit_result_e submit_to_socket(const std::filesystem::path &socket_file, std::string_view text) {
      if (text.empty()) {
        return submit_result_e::rejected;
      }

      const auto path = socket_file.string();
      sockaddr_un address {};
      if (path.size() >= sizeof(address.sun_path)) {
        BOOST_LOG(warning) << "input method: extension socket path is too long: "sv << path;
        return submit_result_e::unavailable;
      }

      const int fd = ::socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0);
      if (fd < 0) {
        BOOST_LOG(warning) << "input method: cannot create a socket: "sv << strerror(errno);
        return submit_result_e::unavailable;
      }

      // The input thread must never block on a stuck extension.
      const timeval timeout {socket_timeout_seconds, 0};
      ::setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));
      ::setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));

      address.sun_family = AF_UNIX;
      std::strncpy(address.sun_path, path.c_str(), sizeof(address.sun_path) - 1);
      if (::connect(fd, reinterpret_cast<sockaddr *>(&address), sizeof(address)) != 0) {
        const int error = errno;
        ::close(fd);
        if (error == ENOENT || error == ECONNREFUSED || error == EACCES) {
          // No extension is listening: the caller keeps the upstream text path.
          return submit_result_e::unavailable;
        }
        BOOST_LOG(warning) << "input method: cannot reach the fcitx5 extension socket: "sv << strerror(error);
        return submit_result_e::unavailable;
      }

      const auto frame = encode_frame(text);
      if (!write_all(fd, frame)) {
        ::close(fd);
        BOOST_LOG(warning) << "input method: could not send the text to the fcitx5 extension";
        return submit_result_e::rejected;
      }

      char reply = 0;
      const auto received = ::recv(fd, &reply, 1, 0);
      ::close(fd);
      if (received != 1) {
        BOOST_LOG(warning) << "input method: the fcitx5 extension closed the connection without a reply";
        return submit_result_e::rejected;
      }
      return parse_reply(reply);
    }
  }  // namespace detail

  bool connect() {
    const auto socket_file = detail::socket_path();
    const bool present = detail::plugin_present(socket_file);
    session_active = true;
    if (present) {
      BOOST_LOG(info) << "input method: fcitx5 extension reachable at "sv << socket_file;
    } else {
      BOOST_LOG(info) << "input method: no fcitx5 extension at "sv << socket_file << ", text keeps the upstream path"sv;
    }
    return present;
  }

  void disconnect() {
    // The desktop session was never touched, so there is nothing to restore.
    session_active = false;
  }

  submit_result_e submit_text(std::string_view utf8) {
    const auto result = detail::submit_to_socket(detail::socket_path(), utf8);
    switch (result) {
      case submit_result_e::submitted:
        BOOST_LOG(debug) << "input method: text committed by the fcitx5 extension";
        break;
      case submit_result_e::rejected:
        BOOST_LOG(warning) << "input method: the fcitx5 extension refused the text";
        break;
      case submit_result_e::unavailable:
        BOOST_LOG(debug) << "input method: no fcitx5 extension, text keeps the upstream path";
        break;
    }
    return result;
  }

  health_t health() {
    health_t snapshot {};
    std::error_code ec;
    snapshot.socket_present = std::filesystem::exists(detail::socket_path(), ec);
    snapshot.session_active = session_active;
    BOOST_LOG(debug) << "input method: "sv << snapshot.describe();
    return snapshot;
  }

  std::string health_t::describe() const {
    const auto flag = [](bool value) {
      return value ? "true" : "false";
    };
    return "socket="s + std::string {flag(socket_present)} +
           " session=" + std::string {flag(session_active)} +
           " healthy=" + std::string {flag(is_healthy())};
  }

#ifdef SUNSHINE_TESTS
  void reset_session_state_for_testing() {
    session_active = false;
  }
#endif
}  // namespace input_method
