/**
 * @file src/platform/linux/input_method.h
 * @brief Declarations for the Linux input method bridge.
 */
#pragma once

// This module hands the text a remote client types over to the local fcitx5
// extension, which commits it to the focused input context in one piece. It is
// wired into Linux builds only; every other platform keeps upstream behavior.
#if defined(__linux__)

// standard includes
#include <filesystem>
#include <string>
#include <string_view>

namespace input_method {
  /**
   * @brief Outcome of a text submission to the fcitx5 extension.
   */
  enum class submit_result_e {
    unavailable,  ///< The extension is not installed or not reachable.
    submitted,    ///< The extension committed the text to the focused context.
    rejected,     ///< The extension refused the text (e.g. no focused context).
  };

  /**
   * @brief Snapshot of the input method bridge health.
   */
  struct health_t {
    bool socket_present {};  ///< The extension socket file exists.
    bool session_active {};  ///< A streaming session currently owns the bridge.

    /**
     * @brief Whether the extension can accept text right now.
     *
     * @return True when the extension socket is in place.
     */
    [[nodiscard]] bool is_healthy() const {
      return socket_present;
    }

    /**
     * @brief One-line human-readable description of the snapshot.
     *
     * @return Description suitable for a log record.
     */
    [[nodiscard]] std::string describe() const;
  };

  /**
   * @brief Take over the input method bridge for a starting stream.
   *
   * Call once when a streaming session begins, before the application prep
   * commands run. The call only observes the environment: it reports whether the
   * fcitx5 extension is reachable and remembers that a session owns the bridge.
   *
   * It never starts, stops or restarts fcitx5, never writes the KWin virtual
   * keyboard switch and never blocks on the desktop session. The keyboard
   * ownership stays exactly where the user put it; only the text path moves.
   *
   * @return True when the extension socket was in place.
   */
  bool connect();

  /**
   * @brief Hand the input method bridge back to the desktop session.
   *
   * Call once when a streaming session ends. The call only drops the session
   * record; nothing in the desktop session is touched, so a missing or repeated
   * call is harmless.
   */
  void disconnect();

  /**
   * @brief Hand a piece of text to the fcitx5 extension.
   *
   * The text is sent as one frame to the extension socket, which commits it to
   * the focused input context as a whole. Nothing is simulated as key presses
   * and the clipboard is not used.
   *
   * The caller must not fall back to the virtual keyboard when the result is
   * @ref submit_result_e::rejected: the extension is installed and refused the
   * text, so the upstream Ctrl+Shift+U path would only inject the same broken
   * bytes the bridge was introduced to replace.
   *
   * @param utf8 UTF-8 text to commit.
   * @return Outcome of the submission.
   */
  [[nodiscard]] submit_result_e submit_text(std::string_view utf8);

  /**
   * @brief Report the health of the input method bridge.
   *
   * @return Snapshot of the extension socket and the session record.
   */
  [[nodiscard]] health_t health();

  namespace detail {
    /**
     * @brief Per-user runtime directory used for the extension socket.
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
     * @brief Whether the fcitx5 extension is present on this host.
     *
     * Users without the extension never get the socket directory, so streaming
     * stays completely untouched for them.
     *
     * @param socket_file Path of the extension socket file.
     * @return True when the socket directory or the socket file exists.
     */
    [[nodiscard]] bool plugin_present(const std::filesystem::path &socket_file);

    /**
     * @brief Build the wire frame of a text submission.
     *
     * The frame is a 4 byte big endian length prefix followed by the UTF-8
     * payload, which is the protocol the fcitx5 extension reads.
     *
     * @param text UTF-8 payload.
     * @return Frame bytes ready to be written to the socket.
     */
    [[nodiscard]] std::string encode_frame(std::string_view text);

    /**
     * @brief Interpret the reply byte of the extension.
     *
     * @param reply Byte received from the extension.
     * @return Submitted for the acceptance byte, rejected for everything else.
     */
    [[nodiscard]] submit_result_e parse_reply(char reply);

    /**
     * @brief Send one text frame to an extension socket and read the reply.
     *
     * @param socket_file Path of the extension socket file.
     * @param text UTF-8 payload.
     * @return Outcome of the submission.
     */
    [[nodiscard]] submit_result_e submit_to_socket(const std::filesystem::path &socket_file, std::string_view text);
  }  // namespace detail

#ifdef SUNSHINE_TESTS
  /**
   * @brief Drop the session record (strictly for unit tests).
   */
  void reset_session_state_for_testing();
#endif
}  // namespace input_method

#endif  // __linux__
