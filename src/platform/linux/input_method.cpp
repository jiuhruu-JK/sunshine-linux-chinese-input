/**
 * @file src/platform/linux/input_method.cpp
 * @brief Definitions for input method ownership during streaming sessions.
 */

// standard includes
#include <algorithm>
#include <cerrno>
#include <chrono>
#include <csignal>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iterator>
#include <optional>
#include <string>
#include <string_view>
#include <thread>
#include <vector>

// platform includes
#include <gio/gio.h>
#include <sys/types.h>
#include <unistd.h>

// local includes
#include "src/logging.h"
#include "input_method.h"

using namespace std::literals;

namespace input_method {
  namespace {
    // KWin VirtualKeyboard D-Bus coordinates; kept in sync with the reference
    // implementation (kwin.rs) so the compositor interface cannot drift.
    constexpr auto kwin_destination = "org.kde.KWin";
    constexpr auto kwin_path = "/VirtualKeyboard";
    constexpr auto kwin_interface = "org.kde.kwin.VirtualKeyboard";
    constexpr auto kwin_property = "enabled";
    constexpr auto dbus_properties_interface = "org.freedesktop.DBus.Properties";

    constexpr auto dbus_timeout_ms = 2000;         ///< Per-call D-Bus timeout, in milliseconds.
    constexpr auto kill_timeout = 5000ms;          ///< Bounded wait for fcitx5 instances to exit.
    constexpr auto socket_timeout = 10000ms;       ///< Bounded wait for the extension socket.
    constexpr auto poll_interval = 100ms;          ///< Polling interval for both waits.
    constexpr auto socket_dir_name = "sunshine-input";     ///< Extension socket directory name.
    constexpr auto socket_file_name = "sunshine-input.sock";  ///< Extension socket file name.
    constexpr auto state_file_name = "sunshine-input-takeover.state";  ///< Takeover record file name.
    constexpr auto kwin_wayland_marker = "kwin_wayland";  ///< Marker in a parent's cmdline that means KWin.

    /// In-memory mirror of the takeover record; the runtime-dir file survives Sunshine restarts.
    std::optional<bool> takeover_original;

    /**
     * @brief Read a small /proc file into a string.
     *
     * @param path File to read.
     * @return File contents, or nullopt when the file could not be read.
     */
    std::optional<std::string> read_proc_file(const std::filesystem::path &path) {
      std::ifstream file {path, std::ios::binary};
      if (!file) {
        return std::nullopt;
      }
      std::string content {std::istreambuf_iterator<char> {file}, std::istreambuf_iterator<char> {}};
      if (file.bad()) {
        return std::nullopt;
      }
      return content;
    }

    /**
     * @brief List every fcitx5 instance on this machine.
     *
     * @return One entry per running fcitx5 process.
     */
    std::vector<process_info_t> processes() {
      std::vector<process_info_t> found;
      std::error_code ec;
      std::filesystem::directory_iterator entries {"/proc", ec};
      if (ec) {
        BOOST_LOG(warning) << "input method: cannot scan /proc: "sv << ec.message();
        return found;
      }
      for (const auto &entry : entries) {
        const auto name = entry.path().filename().string();
        std::uint32_t pid = 0;
        const auto [pid_end, pid_ec] = std::from_chars(name.data(), name.data() + name.size(), pid);
        if (pid_ec != std::errc {} || pid_end != name.data() + name.size()) {
          continue;
        }
        const auto cmdline = read_proc_file(entry.path() / "cmdline");
        const auto stat = read_proc_file(entry.path() / "stat");
        const auto ppid = stat ? detail::parse_ppid(*stat) : std::nullopt;
        if (!cmdline || !ppid || !detail::cmdline_is_fcitx5(*cmdline)) {
          continue;
        }
        process_info_t info {};
        info.pid = pid;
        info.ppid = *ppid;
        info.cmdline = std::move(*cmdline);
        std::replace(info.cmdline.begin(), info.cmdline.end(), '\0', ' ');
        found.push_back(std::move(info));
      }
      return found;
    }

    /**
     * @brief Terminate every fcitx5 instance and wait, bounded, for the exit.
     *
     * @param timeout Maximum time to wait for the instances to disappear.
     */
    void kill_all(std::chrono::milliseconds timeout) {
      for (const auto &proc : processes()) {
        if (::kill(static_cast<pid_t>(proc.pid), SIGTERM) != 0 && errno != ESRCH) {
          BOOST_LOG(warning) << "input method: could not signal fcitx5 pid ["sv << proc.pid << "]: "sv << strerror(errno);
        }
      }
      const auto deadline = std::chrono::steady_clock::now() + timeout;
      while (std::chrono::steady_clock::now() < deadline) {
        if (processes().empty()) {
          return;
        }
        std::this_thread::sleep_for(poll_interval);
      }
    }

    /**
     * @brief Read the KWin virtual keyboard (input method hosting) switch.
     *
     * @return Switch state, or nullopt when the property could not be read.
     */
    std::optional<bool> kwin_enabled() {
      g_autoptr(GError) err = nullptr;
      g_autoptr(GDBusConnection) conn = g_bus_get_sync(G_BUS_TYPE_SESSION, nullptr, &err);
      if (!conn) {
        BOOST_LOG(warning) << "input method: no session bus to read KWin VirtualKeyboard: "sv << (err ? err->message : "unknown error");
        return std::nullopt;
      }
      g_autoptr(GVariant) reply = g_dbus_connection_call_sync(
        conn,
        kwin_destination,
        kwin_path,
        dbus_properties_interface,
        "Get",
        g_variant_new("(ss)", kwin_interface, kwin_property),
        G_VARIANT_TYPE("(v)"),
        G_DBUS_CALL_FLAGS_NO_AUTO_START,
        dbus_timeout_ms,
        nullptr,
        &err
      );
      if (!reply) {
        BOOST_LOG(warning) << "input method: KWin VirtualKeyboard read failed: "sv << (err ? err->message : "unknown error");
        return std::nullopt;
      }
      g_autoptr(GVariant) value = nullptr;
      g_variant_get(reply, "(v)", &value);
      if (!value) {
        BOOST_LOG(warning) << "input method: KWin VirtualKeyboard returned an empty property"sv;
        return std::nullopt;
      }
      return g_variant_get_boolean(value);
    }

    /**
     * @brief Write the KWin virtual keyboard (input method hosting) switch.
     *
     * @param value Switch state to apply.
     * @return True when the property write succeeded.
     */
    bool set_kwin_enabled(bool value) {
      g_autoptr(GError) err = nullptr;
      g_autoptr(GDBusConnection) conn = g_bus_get_sync(G_BUS_TYPE_SESSION, nullptr, &err);
      if (!conn) {
        BOOST_LOG(warning) << "input method: no session bus to write KWin VirtualKeyboard: "sv << (err ? err->message : "unknown error");
        return false;
      }
      g_dbus_connection_call_sync(
        conn,
        kwin_destination,
        kwin_path,
        dbus_properties_interface,
        "Set",
        g_variant_new("(ssv)", kwin_interface, kwin_property, g_variant_new_boolean(value)),
        nullptr,
        G_DBUS_CALL_FLAGS_NO_AUTO_START,
        dbus_timeout_ms,
        nullptr,
        &err
      );
      if (err) {
        BOOST_LOG(warning) << "input method: KWin VirtualKeyboard write failed: "sv << err->message;
        return false;
      }
      return true;
    }

    /**
     * @brief Rebuild the healthy chain: no fcitx5 processes, then KWin re-hosting.
     *
     * @return True when the switch was successfully cycled off and back on.
     */
    bool rebuild_chain() {
      kill_all(kill_timeout);
      // Cycling the switch forces KWin to re-spawn fcitx5 and to re-grant the
      // Wayland text-input role, which a --replace restart from the tray loses.
      if (!set_kwin_enabled(false)) {
        return false;
      }
      return set_kwin_enabled(true);
    }

    /**
     * @brief Whether at least one fcitx5 instance is parented by kwin_wayland.
     *
     * @return True when a KWin-managed instance is running.
     */
    bool kwin_managed_alive() {
      for (const auto &proc : processes()) {
        if (detail::is_kwin_child(proc.ppid)) {
          return true;
        }
      }
      return false;
    }

    /**
     * @brief Read the takeover record: memory first, then the runtime-dir file.
     *
     * @param path State file to consult when memory holds no record.
     * @return Recorded original switch value, or nullopt when not taking over.
     */
    std::optional<bool> load_takeover(const std::filesystem::path &path) {
      if (takeover_original) {
        return takeover_original;
      }
      return detail::load_takeover_state(path);
    }

    /**
     * @brief Record the takeover in memory and in the runtime directory.
     *
     * @param path State file to write.
     * @param original Switch value recorded before the takeover.
     * @return True when the record was persisted.
     */
    bool save_takeover(const std::filesystem::path &path, bool original) {
      if (!detail::save_takeover_state(path, original)) {
        return false;
      }
      takeover_original = original;
      return true;
    }

    /**
     * @brief Drop the takeover record from memory and from the runtime directory.
     *
     * @param path State file to remove.
     * @return True when the record is gone.
     */
    bool clear_takeover(const std::filesystem::path &path) {
      takeover_original.reset();
      return detail::clear_takeover_state(path);
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
      return std::filesystem::path {"/tmp"} / (socket_dir_name + "-"s + std::to_string(::getuid()));
    }

    std::filesystem::path socket_path() {
      return socket_dir() / socket_file_name;
    }

    std::filesystem::path state_path() {
      return runtime_dir() / state_file_name;
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

    bool cmdline_indicates_kwin_wayland(std::string_view cmdline) {
      // Criterion is the parent command line only. The 2026-10-14 respawn loop
      // (progress.md, shift 10) came from reading WAYLAND_SOCKET instead: the
      // Wayland module consumes the descriptor and clears the variable, so even
      // a genuine KWin child tested as "not hosted".
      return cmdline.find(kwin_wayland_marker) != std::string_view::npos;
    }

    bool cmdline_is_fcitx5(std::string_view cmdline) {
      std::size_t begin = 0;
      while (begin <= cmdline.size()) {
        const auto end = cmdline.find('\0', begin);
        const auto arg = cmdline.substr(begin, end == std::string_view::npos ? std::string_view::npos : end - begin);
        if (arg == "fcitx5"sv || arg.ends_with("/fcitx5"sv)) {
          return true;
        }
        if (end == std::string_view::npos) {
          break;
        }
        begin = end + 1;
      }
      return false;
    }

    bool is_kwin_child(std::uint32_t ppid) {
      // A pid without a /proc entry (pid 0 included) is never a KWin child.
      const auto cmdline = read_proc_file(std::filesystem::path {"/proc"} / std::to_string(ppid) / "cmdline");
      if (!cmdline) {
        return false;
      }
      return cmdline_indicates_kwin_wayland(*cmdline);
    }

    std::optional<std::uint32_t> parse_ppid(std::string_view stat) {
      constexpr auto whitespace = " \t\n\r\v\f"sv;
      const auto close = stat.rfind(')');
      if (close == std::string_view::npos) {
        return std::nullopt;
      }
      const auto fields = stat.substr(close + 1);
      const auto state_begin = fields.find_first_not_of(whitespace);
      if (state_begin == std::string_view::npos) {
        return std::nullopt;
      }
      const auto state_end = fields.find_first_of(whitespace, state_begin);
      if (state_end == std::string_view::npos) {
        return std::nullopt;
      }
      const auto ppid_begin = fields.find_first_not_of(whitespace, state_end);
      if (ppid_begin == std::string_view::npos) {
        return std::nullopt;
      }
      const auto ppid_end = fields.find_first_of(whitespace, ppid_begin);
      const auto ppid_stop = ppid_end == std::string_view::npos ? fields.size() : ppid_end;
      const auto ppid_field = fields.substr(ppid_begin, ppid_stop - ppid_begin);
      std::uint32_t ppid = 0;
      const auto [parse_end, parse_ec] = std::from_chars(ppid_field.data(), ppid_field.data() + ppid_field.size(), ppid);
      if (parse_ec != std::errc {} || parse_end != ppid_field.data() + ppid_field.size()) {
        return std::nullopt;
      }
      return ppid;
    }

    std::optional<bool> load_takeover_state(const std::filesystem::path &path) {
      std::ifstream file {path};
      if (!file) {
        // A missing file means "no takeover in progress".
        return std::nullopt;
      }
      std::string line;
      std::getline(file, line);
      const auto state = parse_state(line);
      if (!state) {
        BOOST_LOG(warning) << "input method: ignoring unparsable takeover state file: "sv << path;
      }
      return state;
    }

    std::string format_state(bool original) {
      // One boolean per line — no credentials, no hosts.
      return original ? "enabled=true\n" : "enabled=false\n";
    }

    std::optional<bool> parse_state(std::string_view content) {
      // Trim ASCII whitespace without any throwing path (an all-blank line yields "").
      constexpr auto blank = " \t\r\n"sv;
      while (!content.empty() && blank.find(content.front()) != std::string_view::npos) {
        content.remove_prefix(1);
      }
      while (!content.empty() && blank.find(content.back()) != std::string_view::npos) {
        content.remove_suffix(1);
      }
      if (content == "enabled=true"sv) {
        return true;
      }
      if (content == "enabled=false"sv) {
        return false;
      }
      return std::nullopt;
    }

    bool save_takeover_state(const std::filesystem::path &path, bool original) {
      const auto parent = path.parent_path();
      if (!parent.empty()) {
        std::error_code ec;
        std::filesystem::create_directories(parent, ec);
        if (ec) {
          BOOST_LOG(warning) << "input method: could not create state directory ["sv << parent << "]: "sv << ec.message();
          return false;
        }
      }
      std::ofstream file {path, std::ios::trunc};
      if (!file) {
        BOOST_LOG(warning) << "input method: could not open state file ["sv << path << "] for writing"sv;
        return false;
      }
      file << format_state(original);
      file.flush();
      if (!file) {
        BOOST_LOG(warning) << "input method: could not write state file ["sv << path << ']';
        return false;
      }
      return true;
    }

    bool clear_takeover_state(const std::filesystem::path &path) {
      std::error_code ec;
      std::filesystem::remove(path, ec);
      if (ec && ec != std::errc::no_such_file_or_directory) {
        BOOST_LOG(warning) << "input method: could not remove state file ["sv << path << "]: "sv << ec.message();
        return false;
      }
      return true;
    }

    bool wait_socket(const std::filesystem::path &path, std::chrono::milliseconds timeout) {
      const auto deadline = std::chrono::steady_clock::now() + timeout;
      std::error_code ec;
      while (std::chrono::steady_clock::now() < deadline) {
        if (std::filesystem::exists(path, ec)) {
          return true;
        }
        std::this_thread::sleep_for(poll_interval);
      }
      return std::filesystem::exists(path, ec);
    }
  }  // namespace detail

  bool connect() {
    // Ordinary Linux users without the extension never get touched: the
    // extension creates its socket directory when it loads.
    if (!detail::plugin_present(detail::socket_path())) {
      BOOST_LOG(debug) << "input method: no sunshine-input plugin socket directory, nothing to take over"sv;
      return false;
    }

    const auto original = kwin_enabled();
    if (!original) {
      BOOST_LOG(warning) << "input method: could not read the original KWin VirtualKeyboard.enabled, takeover skipped"sv;
      return false;
    }

    BOOST_LOG(info) << "input method: rebuilding the managed fcitx5 chain (was enabled="sv << (*original ? "true" : "false") << ')';
    if (!rebuild_chain()) {
      // Never leave the user's switch flipped by a half-finished rebuild.
      BOOST_LOG(warning) << "input method: chain rebuild failed, restoring the original switch"sv;
      if (!set_kwin_enabled(*original)) {
        BOOST_LOG(warning) << "input method: could not restore the original switch"sv;
      }
      return false;
    }

    const bool socket_ready = detail::wait_socket(detail::socket_path(), socket_timeout);
    if (!save_takeover(detail::state_path(), *original)) {
      // Without a record nothing could be restored later, so undo the switch.
      BOOST_LOG(warning) << "input method: could not record the takeover state, restoring the original switch"sv;
      if (!set_kwin_enabled(*original)) {
        BOOST_LOG(warning) << "input method: could not restore the original switch"sv;
      }
      return false;
    }

    BOOST_LOG(info) << "input method: takeover complete (enabled=true, socket_ready="sv << (socket_ready ? "true" : "false") << ')';
    return socket_ready;
  }

  void disconnect() {
    const auto original = load_takeover(detail::state_path());
    if (!original) {
      // No takeover in progress: idle by design. Mid-session undo commands and
      // manual replays must not touch the user's switch or kill processes.
      return;
    }
    BOOST_LOG(info) << "input method: restoring KWin VirtualKeyboard.enabled="sv << (*original ? "true" : "false") << " after the session"sv;
    if (!set_kwin_enabled(*original)) {
      // Keep the record so the next disconnect retries the restore.
      BOOST_LOG(warning) << "input method: restore failed, takeover state kept for retry"sv;
      return;
    }
    clear_takeover(detail::state_path());
  }

  health_t health() {
    health_t snapshot {};
    const auto enabled = kwin_enabled();
    if (!enabled) {
      BOOST_LOG(warning) << "input method: could not read KWin VirtualKeyboard.enabled"sv;
    }
    snapshot.kwin_enabled = enabled.value_or(false);
    snapshot.managed_alive = kwin_managed_alive();
    std::error_code ec;
    snapshot.socket_present = std::filesystem::exists(detail::socket_path(), ec);
    BOOST_LOG(debug) << "input method: "sv << snapshot.describe();
    return snapshot;
  }

  std::string health_t::describe() const {
    const auto flag = [](bool value) {
      return value ? "true" : "false";
    };
    return "kwin_enabled="s + std::string {flag(kwin_enabled)} +
           " managed_fcitx5=" + std::string {flag(managed_alive)} +
           " socket=" + std::string {flag(socket_present)} +
           " healthy=" + std::string {flag(is_healthy())};
  }

#ifdef SUNSHINE_TESTS
  void reset_takeover_state_for_testing() {
    takeover_original.reset();
  }
#endif
}  // namespace input_method
