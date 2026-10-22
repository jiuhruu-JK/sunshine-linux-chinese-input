/**
 * @file tests/unit/platform/linux/test_input_method.cpp
 * @brief Tests for the Linux input-method ownership bridge.
 *
 * Only the side-effect-free helpers and the no-op paths are tested here: the
 * /proc scan, the D-Bus switch writes and the real socket wait touch the live
 * desktop session and are covered by the VM acceptance matrix instead. The
 * restore path is deliberately not tested on arbitrary machines — it writes the
 * user's KWin VirtualKeyboard switch over the session bus.
 */

#ifdef __linux__

// test includes
#include "../../../tests_common.h"

// standard includes
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <optional>
#include <string>
#include <string_view>

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
   * @brief Fixture providing a private runtime directory for state file tests.
   */
  class InputMethodStateTest: public ProcessEnvironment {
  protected:
    void SetUp() override {
      ProcessEnvironment::SetUp();
      runtime_guard_.emplace("XDG_RUNTIME_DIR");
      test_dir = fs::temp_directory_path() / ("sunshine-input-test-" + std::to_string(getpid()));
      fs::remove_all(test_dir);
      fs::create_directories(test_dir);
      setenv("XDG_RUNTIME_DIR", test_dir.string().c_str(), 1);
      im::reset_takeover_state_for_testing();
    }

    void TearDown() override {
      im::reset_takeover_state_for_testing();
      fs::remove_all(test_dir);
      runtime_guard_.reset();
      ProcessEnvironment::TearDown();
    }

    /**
     * @brief Path of a state file inside the private runtime directory.
     */
    fs::path state_file() const {
      return test_dir / "sunshine-input-takeover.state";
    }

    std::optional<environment_guard_t> runtime_guard_;  ///< Restores XDG_RUNTIME_DIR.
    fs::path test_dir;  ///< Private runtime directory for the test.
  };
}  // namespace

// ---------------------------------------------------------------------------
// KWin托管判据 (AC4 / shift-10 lesson)
// ---------------------------------------------------------------------------

TEST(InputMethodKwinCriterion, KwinChildDetection_MatchesKwinWaylandParent) {
  const std::string cmdline("kwin_wayland\0--socket\0wayland-0\0", 30);
  EXPECT_TRUE(imd::cmdline_indicates_kwin_wayland(cmdline));
}

TEST(InputMethodKwinCriterion, KwinChildDetection_RejectsNonKwinParent) {
  const std::string cmdline("plasmashell\0", 12);
  EXPECT_FALSE(imd::cmdline_indicates_kwin_wayland(cmdline));
  EXPECT_FALSE(imd::cmdline_indicates_kwin_wayland("fcitx5"));
  EXPECT_FALSE(imd::cmdline_indicates_kwin_wayland(""));
}

TEST(InputMethodKwinCriterion, KwinChildDetection_MissingProcessIsFalse) {
  // pid 0 is never present in /proc; a vanished process must never count as hosted.
  EXPECT_FALSE(imd::is_kwin_child(0));
  EXPECT_FALSE(imd::is_kwin_child(4194303));
}

TEST_F(ProcessEnvironment, KwinChildDetection_RejectsWaylandSocketEnv) {
  // Regression for the 2026-10-14 night shift (progress.md, shift 10): the broken
  // criterion read WAYLAND_SOCKET, which the Wayland module consumes and clears,
  // so even a genuine KWin child tested as "not hosted". Every fcitx5 start then
  // cycled the switch, KWin killed its own instance, re-spawned it, forever.
  environment_guard_t wayland_socket_guard {"WAYLAND_SOCKET"};
  ASSERT_EQ(setenv("WAYLAND_SOCKET", "7", 1), 0);

  const std::string parent_cmdline("fcitx5\0", 6);
  EXPECT_FALSE(imd::cmdline_indicates_kwin_wayland(parent_cmdline));
  EXPECT_FALSE(imd::is_kwin_child(0));
  // The environment is irrelevant even when a real KWin parent is present:
  const std::string kwin_cmdline("kwin_wayland\0--socket\0", 21);
  EXPECT_TRUE(imd::cmdline_indicates_kwin_wayland(kwin_cmdline));
}

// ---------------------------------------------------------------------------
// /proc parsing helpers
// ---------------------------------------------------------------------------

TEST(InputMethodProcess, ParsePpid_SimpleComm) {
  EXPECT_EQ(imd::parse_ppid("99 (systemd) S 1 99 1").value_or(0), 1u);
}

TEST(InputMethodProcess, ParsePpid_CommWithSpacesAndParens) {
  // comm may contain spaces and parentheses; parsing must start after the last ')'.
  const auto stat = "1234 (fcitx5 (weird) name) S 5678 1234 1234 0 -1 4194560"sv;
  EXPECT_EQ(imd::parse_ppid(stat).value_or(-1), 5678);
}

TEST(InputMethodProcess, ParsePpid_NoParensReturnsNullopt) {
  EXPECT_FALSE(imd::parse_ppid("no parens here").has_value());
  EXPECT_FALSE(imd::parse_ppid("1234 (fcitx5) S").has_value());
}

TEST(InputMethodProcess, CmdlineIsFcitx5_MatchesBareName) {
  const std::string argv("fcitx5\0--replace\0", 18);
  EXPECT_TRUE(imd::cmdline_is_fcitx5(argv));
}

TEST(InputMethodProcess, CmdlineIsFcitx5_MatchesAbsolutePath) {
  const std::string argv("/usr/bin/fcitx5\0", 17);
  EXPECT_TRUE(imd::cmdline_is_fcitx5(argv));
}

TEST(InputMethodProcess, CmdlineIsFcitx5_RejectsUnrelated) {
  const std::string argv("bash\0-l\0", 8);
  EXPECT_FALSE(imd::cmdline_is_fcitx5(argv));
}

TEST(InputMethodProcess, CmdlineIsFcitx5_NoSubstringFalsePositive) {
  // "notfcitx5x" contains "fcitx5" but not as a whole argv element.
  const std::string argv("notfcitx5x\0", 11);
  EXPECT_FALSE(imd::cmdline_is_fcitx5(argv));
  const std::string argv2("editor\0help/fcitx5x.txt\0", 23);
  EXPECT_FALSE(imd::cmdline_is_fcitx5(argv2));
}

// ---------------------------------------------------------------------------
// 状态存取
// ---------------------------------------------------------------------------

TEST_F(InputMethodStateTest, StateRoundTrip_SaveLoadClear) {
  for (bool original : {true, false}) {
    ASSERT_TRUE(imd::save_takeover_state(state_file(), original));
    ASSERT_EQ(imd::load_takeover_state(state_file()).value_or(!original), original);
  }
  ASSERT_TRUE(imd::clear_takeover_state(state_file()));
  EXPECT_FALSE(imd::load_takeover_state(state_file()).has_value());
  // A missing file is always a successful clear (idempotent disconnect).
  EXPECT_TRUE(imd::clear_takeover_state(state_file()));
}

TEST_F(InputMethodStateTest, StateFormat_ParsesWhatSaveWrote) {
  for (bool original : {true, false}) {
    ASSERT_EQ(imd::parse_state(imd::format_state(original)).value_or(!original), original);
  }
}

TEST(InputMethodState, ParseState_TrimsWhitespace) {
  EXPECT_EQ(imd::parse_state("enabled=true\n").value_or(false), true);
  EXPECT_EQ(imd::parse_state("enabled=false\r\n").value_or(true), false);
  EXPECT_EQ(imd::parse_state("  enabled=true  \n").value_or(false), true);
}

TEST(InputMethodState, ParseState_GarbageReturnsNullopt) {
  EXPECT_FALSE(imd::parse_state("garbage").has_value());
  EXPECT_FALSE(imd::parse_state("").has_value());
  EXPECT_FALSE(imd::parse_state("enabled=maybe").has_value());
}

TEST_F(InputMethodStateTest, StateSave_CreatesMissingDirectory) {
  const auto nested = test_dir / "nested" / "dir" / "sunshine-input-takeover.state";
  EXPECT_TRUE(imd::save_takeover_state(nested, true));
  EXPECT_EQ(imd::load_takeover_state(nested).value_or(false), true);
}

// ---------------------------------------------------------------------------
// socket 路径与等待
// ---------------------------------------------------------------------------

TEST_F(InputMethodStateTest, SocketPaths_FollowRuntimeDir) {
  const auto socket = imd::socket_path();
  EXPECT_EQ(socket, test_dir / "sunshine-input" / "sunshine-input.sock");
  EXPECT_EQ(imd::state_path(), test_dir / "sunshine-input-takeover.state");
}

TEST_F(InputMethodStateTest, PluginPresent_FollowsSocketDirectory) {
  const auto socket = imd::socket_path();
  EXPECT_FALSE(imd::plugin_present(socket)) << "no extension installed yet";
  fs::create_directories(socket.parent_path());
  EXPECT_TRUE(imd::plugin_present(socket));
  fs::remove_all(socket.parent_path());
  EXPECT_FALSE(imd::plugin_present(socket));
}

TEST(InputMethodSocket, WaitSocket_AppearsWithinTimeout) {
  const auto path = fs::temp_directory_path() / ("sunshine-input-wait-" + std::to_string(getpid()) + ".sock");
  fs::remove(path);
  {
    std::ofstream file {path};
    file << "stub";
  }
  EXPECT_TRUE(imd::wait_socket(path, 2000ms));
  fs::remove(path);
}

TEST(InputMethodSocket, WaitSocket_TimeoutReturnsFalse) {
  const auto path = fs::temp_directory_path() / ("sunshine-input-wait-missing-" + std::to_string(getpid()) + ".sock");
  fs::remove(path);
  EXPECT_FALSE(imd::wait_socket(path, 250ms));
}

// ---------------------------------------------------------------------------
// disconnect 空操作语义 (AC3)
// ---------------------------------------------------------------------------

TEST_F(InputMethodStateTest, DisconnectWithoutTakeoverIsNoop) {
  // No takeover record anywhere: disconnect must not touch the switch, must not
  // kill anything and must not create files. Anything else would replay a
  // mid-session undo against a user who never streamed.
  im::disconnect();
  EXPECT_FALSE(fs::exists(state_file()));
  EXPECT_FALSE(fs::exists(test_dir / "sunshine-input"));

  // A recorded-but-missing state file behaves the same as no record.
  EXPECT_TRUE(imd::save_takeover_state(state_file(), true));
  EXPECT_TRUE(imd::clear_takeover_state(state_file()));
  im::reset_takeover_state_for_testing();
  im::disconnect();
  EXPECT_FALSE(fs::exists(state_file()));
}

#endif  // __linux__
