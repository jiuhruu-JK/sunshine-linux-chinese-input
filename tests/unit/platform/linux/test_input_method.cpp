/**
 * @file tests/unit/platform/linux/test_input_method.cpp
 * @brief Tests for the Linux input method bridge.
 *
 * The bridge talks to the fcitx5 extension over a Unix domain socket, so the
 * tests drive a stub server that speaks the same 4 byte length prefixed
 * protocol. Nothing here touches the live desktop session: the bridge never
 * starts, stops or reconfigures fcitx5, and the tests assert exactly that.
 */

#ifdef __linux__

// test includes
#include "../../../tests_common.h"

// standard includes
#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <optional>
#include <string>
#include <string_view>
#include <thread>

// platform includes
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/un.h>
#include <unistd.h>

// local includes
#include "src/platform/linux/input_method.h"

using namespace std::literals;

namespace fs = std::filesystem;
namespace im = input_method;
namespace imd = input_method::detail;

namespace {
  /**
   * @brief Restore one environment variable when a test scope ends.
   */
  class environment_guard_t {
  public:
    explicit environment_guard_t(const char *name):
        name_ {name} {
      if (const char *value = std::getenv(name)) {
        value_ = value;
      }
    }

    ~environment_guard_t() {
      if (value_) {
        setenv(name_.c_str(), value_->c_str(), 1);
      } else {
        unsetenv(name_.c_str());
      }
    }

  private:
    std::string name_;  ///< Environment variable name.
    std::optional<std::string> value_;  ///< Value present before the test changed the environment.
  };

  /**
   * @brief Drain pending log records before a test mutates the environment.
   *
   * GoogleTest emits test-start records before fixture setup; formatting them
   * while setenv()/unsetenv() runs races with getenv() on older glibc.
   */
  class ProcessEnvironment: public testing::Test {
  protected:
    void SetUp() override {
      logging::log_flush();
    }
  };

  /**
   * @brief Fixture providing a private runtime directory for socket tests.
   */
  class InputMethodSocketTest: public ProcessEnvironment {
  protected:
    void SetUp() override {
      ProcessEnvironment::SetUp();
      runtime_guard_.emplace("XDG_RUNTIME_DIR");
      test_dir = fs::temp_directory_path() / ("sunshine-input-test-" + std::to_string(getpid()));
      fs::remove_all(test_dir);
      fs::create_directories(test_dir);
      setenv("XDG_RUNTIME_DIR", test_dir.string().c_str(), 1);
      im::reset_session_state_for_testing();
    }

    void TearDown() override {
      im::reset_session_state_for_testing();
      fs::remove_all(test_dir);
      runtime_guard_.reset();
      ProcessEnvironment::TearDown();
    }

    /**
     * @brief Path of the extension socket inside the private runtime directory.
     */
    fs::path socket_file() const {
      return test_dir / "sunshine-input" / "sunshine-input.sock";
    }

    std::optional<environment_guard_t> runtime_guard_;  ///< Restores XDG_RUNTIME_DIR.
    fs::path test_dir;  ///< Private runtime directory for the test.
  };

  /**
   * @brief Stub extension server that accepts one frame and answers with a byte.
   */
  class stub_extension_t {
  public:
    /**
     * @brief Start the stub server on a socket path.
     *
     * @param path Socket file the stub listens on.
     * @param reply Byte sent back to the client.
     */
    explicit stub_extension_t(const fs::path &path, char reply):
        reply_ {reply} {
      fs::create_directories(path.parent_path());
      listen_fd_ = ::socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC | SOCK_NONBLOCK, 0);
      EXPECT_GE(listen_fd_, 0);
      if (listen_fd_ < 0) {
        return;
      }

      sockaddr_un address {};
      address.sun_family = AF_UNIX;
      const auto text = path.string();
      EXPECT_LT(text.size(), sizeof(address.sun_path));
      if (text.size() >= sizeof(address.sun_path)) {
        return;
      }
      std::strncpy(address.sun_path, text.c_str(), sizeof(address.sun_path) - 1);
      EXPECT_EQ(::bind(listen_fd_, reinterpret_cast<sockaddr *>(&address), sizeof(address)), 0);
      EXPECT_EQ(::listen(listen_fd_, 4), 0);

      worker_ = std::thread {[this] { serve(); }};
    }

    ~stub_extension_t() {
      stop_.store(true);
      if (worker_.joinable()) {
        worker_.join();
      }
      if (listen_fd_ >= 0) {
        ::close(listen_fd_);
      }
    }

    /**
     * @brief The payload the stub received.
     */
    std::string received() {
      if (worker_.joinable()) {
        worker_.join();
      }
      return received_;
    }

  private:
    void serve() {
      int client = -1;
      // The listener is non blocking so the stub can always be torn down, even
      // when no client ever connects.
      while (client < 0 && !stop_.load()) {
        client = ::accept(listen_fd_, nullptr, nullptr);
        if (client < 0) {
          std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
      }
      if (client < 0) {
        return;
      }

      // The client socket is blocking; a receive timeout keeps the stub
      // tearable down even when a client connects without sending anything.
      const timeval timeout {2, 0};
      ::setsockopt(client, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));

      unsigned char header[4] {};
      if (::recv(client, header, sizeof(header), MSG_WAITALL) == static_cast<ssize_t>(sizeof(header))) {
        const auto length = (static_cast<std::uint32_t>(header[0]) << 24) |
                            (static_cast<std::uint32_t>(header[1]) << 16) |
                            (static_cast<std::uint32_t>(header[2]) << 8) |
                            static_cast<std::uint32_t>(header[3]);
        std::string payload(length, '\0');
        if (length > 0 && ::recv(client, payload.data(), length, MSG_WAITALL) == static_cast<ssize_t>(length)) {
          received_ = payload;
        }
      }
      const char answer = reply_;
      ::send(client, &answer, 1, MSG_NOSIGNAL);
      ::close(client);
    }

    char reply_;  ///< Byte sent back to the client.
    int listen_fd_ = -1;  ///< Listening socket.
    std::atomic<bool> stop_ {false};  ///< Set when the stub is torn down.
    std::thread worker_;  ///< Thread serving one client.
    std::string received_;  ///< Payload the stub received.
  };
}  // namespace

TEST_F(InputMethodSocketTest, SocketPaths_FollowRuntimeDir) {
  EXPECT_EQ(imd::socket_path(), socket_file());
  EXPECT_EQ(imd::runtime_dir(), test_dir);
}

TEST_F(InputMethodSocketTest, SocketPaths_FallBackToTmpWithoutRuntimeDir) {
  unsetenv("XDG_RUNTIME_DIR");
  EXPECT_EQ(imd::runtime_dir(), fs::path {"/tmp"});
  EXPECT_EQ(imd::socket_dir(), fs::path {"/tmp"} / ("sunshine-input-"s + std::to_string(getuid())));
  EXPECT_EQ(imd::socket_path(), imd::socket_dir() / "sunshine-input.sock");
}

TEST_F(InputMethodSocketTest, PluginPresent_FollowsSocketDirectory) {
  const auto socket = socket_file();
  EXPECT_FALSE(imd::plugin_present(socket)) << "no extension installed yet";
  fs::create_directories(socket.parent_path());
  EXPECT_TRUE(imd::plugin_present(socket));
  fs::remove_all(socket.parent_path());
  EXPECT_FALSE(imd::plugin_present(socket));
}

TEST(InputMethodFrame, EncodeFrame_UsesBigEndianLengthPrefix) {
  const auto frame = imd::encode_frame("中文"sv);
  ASSERT_EQ(frame.size(), 4u + 6u);
  EXPECT_EQ(static_cast<unsigned char>(frame[0]), 0u);
  EXPECT_EQ(static_cast<unsigned char>(frame[1]), 0u);
  EXPECT_EQ(static_cast<unsigned char>(frame[2]), 0u);
  EXPECT_EQ(static_cast<unsigned char>(frame[3]), 6u);
  EXPECT_EQ(frame.substr(4), "中文"sv);
}

TEST(InputMethodFrame, EncodeFrame_EmptyPayload) {
  const auto frame = imd::encode_frame(""sv);
  ASSERT_EQ(frame.size(), 4u);
  for (const auto byte : frame) {
    EXPECT_EQ(static_cast<unsigned char>(byte), 0u);
  }
}

TEST(InputMethodReply, ParseReply_AcceptanceByteIsSubmitted) {
  EXPECT_EQ(imd::parse_reply('K'), im::submit_result_e::submitted);
}

TEST(InputMethodReply, ParseReply_RejectionByteIsRejected) {
  EXPECT_EQ(imd::parse_reply('E'), im::submit_result_e::rejected);
}

TEST(InputMethodReply, ParseReply_UnknownByteIsRejected) {
  EXPECT_EQ(imd::parse_reply('?'), im::submit_result_e::rejected);
}

TEST_F(InputMethodSocketTest, SubmitToSocket_ExtensionAcceptsTheText) {
  stub_extension_t stub {socket_file(), 'K'};
  const auto result = imd::submit_to_socket(socket_file(), "中文测试"sv);
  EXPECT_EQ(result, im::submit_result_e::submitted);
  EXPECT_EQ(stub.received(), "中文测试"sv);
}

TEST_F(InputMethodSocketTest, SubmitToSocket_ExtensionRefusesTheText) {
  stub_extension_t stub {socket_file(), 'E'};
  const auto result = imd::submit_to_socket(socket_file(), "中文测试"sv);
  EXPECT_EQ(result, im::submit_result_e::rejected);
  EXPECT_EQ(stub.received(), "中文测试"sv);
}

TEST_F(InputMethodSocketTest, SubmitToSocket_MissingSocketIsUnavailable) {
  // No extension listening: the caller keeps the upstream text path.
  const auto result = imd::submit_to_socket(socket_file(), "中文"sv);
  EXPECT_EQ(result, im::submit_result_e::unavailable);
}

TEST_F(InputMethodSocketTest, SubmitToSocket_EmptyTextIsRejected) {
  stub_extension_t stub {socket_file(), 'K'};
  EXPECT_EQ(imd::submit_to_socket(socket_file(), ""sv), im::submit_result_e::rejected);
}

TEST_F(InputMethodSocketTest, SubmitText_UsesTheExtensionSocket) {
  stub_extension_t stub {socket_file(), 'K'};
  EXPECT_EQ(im::submit_text("你好"sv), im::submit_result_e::submitted);
  EXPECT_EQ(stub.received(), "你好"sv);
}

TEST_F(InputMethodSocketTest, SubmitText_WithoutExtensionIsUnavailable) {
  EXPECT_EQ(im::submit_text("你好"sv), im::submit_result_e::unavailable);
}

TEST_F(InputMethodSocketTest, ConnectAndDisconnect_OnlyTrackTheSession) {
  EXPECT_FALSE(im::health().session_active);
  EXPECT_FALSE(im::connect()) << "no extension installed";
  EXPECT_TRUE(im::health().session_active);

  im::disconnect();
  EXPECT_FALSE(im::health().session_active);
}

TEST_F(InputMethodSocketTest, Connect_ReportsTheExtensionWhenPresent) {
  stub_extension_t stub {socket_file(), 'K'};
  EXPECT_TRUE(im::connect());
  EXPECT_TRUE(im::health().socket_present);
  EXPECT_TRUE(im::health().is_healthy());
}

TEST_F(InputMethodSocketTest, Health_DescribesTheSnapshot) {
  const auto description = im::health().describe();
  EXPECT_NE(description.find("socket="), std::string::npos);
  EXPECT_NE(description.find("session="), std::string::npos);
  EXPECT_NE(description.find("healthy="), std::string::npos);
}

#endif  // __linux__
