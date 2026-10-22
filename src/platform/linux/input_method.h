/**
 * @file src/platform/linux/input_method.h
 * @brief Declarations for input method ownership during streaming sessions.
 */
#pragma once

// This module manages desktop input method ownership (KWin hosting + fcitx5) and
// is wired into Linux builds only; every other platform keeps upstream behavior.
#if defined(__linux__)

// standard includes
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace input_method {
  /**
   * @brief Snapshot of the input method chain health.
   */
  struct health_t {
    bool kwin_enabled {};    ///< KWin virtual keyboard (input method hosting) switch state.
    bool managed_alive {};   ///< A KWin-managed fcitx5 instance is running.
    bool socket_present {};  ///< The fcitx5 extension socket file exists.

    /**
     * @brief Whether every element of the healthy chain is in place.
     *
     * @return True when the switch is on, a managed fcitx5 runs and the socket exists.
     */
    [[nodiscard]] bool is_healthy() const {
      return kwin_enabled && managed_alive && socket_present;
    }

    /**
     * @brief One-line human-readable description of the snapshot.
     *
     * @return Description suitable for a log record.
     */
    [[nodiscard]] std::string describe() const;
  };

  /**
   * @brief One running fcitx5 instance as observed in /proc.
   */
  struct process_info_t {
    std::uint32_t pid {};   ///< Process id of the fcitx5 instance.
    std::uint32_t ppid {};  ///< Parent process id (KWin for a managed instance).
    std::string cmdline;    ///< Command line with NUL separators replaced by spaces.
  };

  /**
   * @brief Take over input method ownership for a starting stream.
   *
   * Call once when a streaming session begins, before the application prep
   * commands run. The takeover converges the chain to a known healthy state —
   * KWin-managed fcitx5 plus a live extension socket — no matter how the desktop
   * broke it earlier (tray restart with --replace, crash, ...):
   *
   * - users without the fcitx5 extension socket directory are never touched;
   * - the original KWin VirtualKeyboard.enabled value is recorded;
   * - all fcitx5 instances are terminated (bounded wait);
   * - the KWin switch is cycled false -> true to force re-hosting;
   * - the socket file is awaited (bounded, seconds);
   * - the takeover is recorded in memory and in the runtime directory.
   *
   * Failures only log a warning; nothing propagates to the caller.
   *
   * @return True when the extension socket was in place at the end.
   */
  bool connect();

  /**
   * @brief Hand input method ownership back to the desktop session.
   *
   * Call once when a streaming session ends. With a takeover record the
   * original switch value is restored and the record cleared; without a record
   * this is a no-op — mid-session undo commands and manual replays must never
   * touch the user's switch or kill processes. Failures only log a warning and
   * keep the record so the restore is retried on the next call.
   */
  void disconnect();

  /**
   * @brief Report the health of the input method chain.
   *
   * Each field is queried independently; a field that cannot be queried logs a
   * warning and reports false.
   *
   * @return Snapshot of the switch, the managed fcitx5 instance and the socket.
   */
  [[nodiscard]] health_t health();

  namespace detail {
    /**
     * @brief Per-user runtime directory used for the socket and the state file.
     *
     * @return XDG_RUNTIME_DIR when set, /tmp otherwise.
     */
    [[nodiscard]] std::filesystem::path runtime_dir();

    /**
     * @brief Directory holding the extension socket.
     *
     * Mirrors the layout the fcitx5 extension creates, including the
     * /tmp/sunshine-input-<uid> fallback when XDG_RUNTIME_DIR is unset.
     *
     * @return Directory that contains sunshine-input.sock.
     */
    [[nodiscard]] std::filesystem::path socket_dir();

    /**
     * @brief Path of the extension socket file.
     *
     * @return socket_dir()/sunshine-input.sock.
     */
    [[nodiscard]] std::filesystem::path socket_path();

    /**
     * @brief Path of the takeover state file in the runtime directory.
     *
     * @return runtime_dir()/sunshine-input-takeover.state.
     */
    [[nodiscard]] std::filesystem::path state_path();

    /**
     * @brief Whether the fcitx5 extension plugin is present on this host.
     *
     * Users without the extension never get the socket directory, so streaming
     * stays completely untouched for them.
     *
     * @param socket_file Path of the extension socket file.
     * @return True when the socket directory or the socket file exists.
     */
    [[nodiscard]] bool plugin_present(const std::filesystem::path &socket_file);

    /**
     * @brief Whether a /proc/<pid>/cmdline payload belongs to KWin's Wayland compositor.
     *
     * KWin grants the Wayland text-input role only to processes it spawned
     * itself, so the parent of a healthy fcitx5 instance is kwin_wayland.
     * The WAYLAND_SOCKET environment variable must never be used as a
     * substitute criterion: the Wayland stack consumes and clears it, and
     * trusting it caused a respawn loop during the 2026-10-14 night shift.
     *
     * @param cmdline Contents of /proc/<ppid>/cmdline.
     * @return True when the parent process command line mentions kwin_wayland.
     */
    [[nodiscard]] bool cmdline_indicates_kwin_wayland(std::string_view cmdline);

    /**
     * @brief Whether a /proc/<pid>/cmdline payload belongs to an fcitx5 process.
     *
     * An argument equal to "fcitx5" or ending in "/fcitx5" identifies the
     * process, so unrelated matches (e.g. an editor showing an fcitx5 config
     * file) never qualify.
     *
     * @param cmdline Contents of /proc/<pid>/cmdline.
     * @return True when one of the arguments names fcitx5.
     */
    [[nodiscard]] bool cmdline_is_fcitx5(std::string_view cmdline);

    /**
     * @brief Whether the parent of a process is KWin's Wayland compositor.
     *
     * @param ppid Parent process id to inspect.
     * @return True when /proc/<ppid>/cmdline mentions kwin_wayland; a missing process yields false.
     */
    [[nodiscard]] bool is_kwin_child(std::uint32_t ppid);

    /**
     * @brief Extract the parent process id from a /proc/<pid>/stat payload.
     *
     * The comm field may contain spaces and parentheses, so the parser anchors
     * on the final ')' of the record like the reference implementation.
     *
     * @param stat Contents of /proc/<pid>/stat.
     * @return Parent process id, or nullopt when the payload cannot be parsed.
     */
    [[nodiscard]] std::optional<std::uint32_t> parse_ppid(std::string_view stat);

    /**
     * @brief Read the takeover record from a state file.
     *
     * @param path State file to read.
     * @return Recorded original switch value, or nullopt when missing or unparsable.
     */
    [[nodiscard]] std::optional<bool> load_takeover_state(const std::filesystem::path &path);

    /**
     * @brief Serialize a takeover record.
     *
     * @param original Switch value recorded before the takeover.
     * @return One-line state file payload.
     */
    [[nodiscard]] std::string format_state(bool original);

    /**
     * @brief Parse a takeover record payload.
     *
     * @param content State file payload.
     * @return Recorded original switch value, or nullopt when the payload is not a record.
     */
    [[nodiscard]] std::optional<bool> parse_state(std::string_view content);

    /**
     * @brief Write the takeover record to a state file.
     *
     * @param path State file to write.
     * @param original Switch value recorded before the takeover.
     * @return True when the file was written.
     */
    [[nodiscard]] bool save_takeover_state(const std::filesystem::path &path, bool original);

    /**
     * @brief Remove a takeover state file.
     *
     * @param path State file to remove.
     * @return True when the file is gone afterwards (a missing file counts as success).
     */
    [[nodiscard]] bool clear_takeover_state(const std::filesystem::path &path);

    /**
     * @brief Wait, bounded, for the extension socket file to appear.
     *
     * @param path Socket file to await.
     * @param timeout Maximum time to wait.
     * @return True when the file exists at the end of the wait.
     */
    [[nodiscard]] bool wait_socket(const std::filesystem::path &path, std::chrono::milliseconds timeout);
  }  // namespace detail

#ifdef SUNSHINE_TESTS
  /**
   * @brief Drop the in-memory takeover record (strictly for unit tests).
   */
  void reset_takeover_state_for_testing();
#endif
}  // namespace input_method

#endif  // __linux__
