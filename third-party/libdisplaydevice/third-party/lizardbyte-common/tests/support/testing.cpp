/**
 * @file tests/support/testing.cpp
 * @brief Shared GoogleTest support helper definitions.
 */

// standard includes
#include <cstdio>
#include <iostream>
#include <iterator>
#include <regex>

// lib includes
#include <gtest/internal/gtest-port.h>

// platform includes
#if defined(__linux__)
  #include <unistd.h>
#endif

// local includes
#include <lizardbyte/common/env.h>
#include <lizardbyte/common/testing.h>

namespace lizardbyte::common::testing {
  void BaseTest::SetUp() {
    test_skipped_at_setup_ = false;
    output_suppressed_ = false;
    stdout_capture_active_ = false;
    stderr_capture_active_ = false;

    cout_buffer_.str({});
    cout_buffer_.clear();
    cerr_buffer_.str({});
    cerr_buffer_.clear();
    stdout_buffer_.str({});
    stdout_buffer_.clear();
    stderr_buffer_.str({});
    stderr_buffer_.clear();

    if (const auto skip_reason {skipTest()}; !skip_reason.empty()) {
      test_skipped_at_setup_ = true;
      GTEST_SKIP() << skip_reason;
    }

    output_suppressed_ = isOutputSuppressed();
    if (output_suppressed_) {
      ::testing::internal::CaptureStdout();
      stdout_capture_active_ = true;
      ::testing::internal::CaptureStderr();
      stderr_capture_active_ = true;

      cout_streambuf_ = std::cout.rdbuf();
      cerr_streambuf_ = std::cerr.rdbuf();
      std::cout.rdbuf(cout_buffer_.rdbuf());
      std::cerr.rdbuf(cerr_buffer_.rdbuf());
    }
  }

  void BaseTest::TearDown() {
    if (test_skipped_at_setup_) {
      return;
    }

    if (output_suppressed_) {
      std::cout.flush();
      std::cerr.flush();
      std::fflush(stdout);
      std::fflush(stderr);

      if (cout_streambuf_ != nullptr) {
        std::cout.rdbuf(cout_streambuf_);
        cout_streambuf_ = nullptr;
      }

      if (cerr_streambuf_ != nullptr) {
        std::cerr.rdbuf(cerr_streambuf_);
        cerr_streambuf_ = nullptr;
      }

      if (stdout_capture_active_) {
        stdout_buffer_ << ::testing::internal::GetCapturedStdout();
        stdout_capture_active_ = false;
      }

      if (stderr_capture_active_) {
        stderr_buffer_ << ::testing::internal::GetCapturedStderr();
        stderr_capture_active_ = false;
      }

      const auto *test_info = ::testing::UnitTest::GetInstance()->current_test_info();
      if (test_info != nullptr && test_info->result()->Failed()) {
        std::cout << std::endl
                  << "Test failed: " << test_info->name() << std::endl
                  << std::endl
                  << "Captured cout:" << std::endl
                  << cout_buffer_.str() << std::endl
                  << "Captured cerr:" << std::endl
                  << cerr_buffer_.str() << std::endl
                  << "Captured stdout:" << std::endl
                  << stdout_buffer_.str() << std::endl
                  << "Captured stderr:" << std::endl
                  << stderr_buffer_.str() << std::endl;
      }

      output_suppressed_ = false;
    }
  }

  const std::vector<std::string> &BaseTest::getArgs() const {
    static const auto args {::testing::internal::GetArgvs()};
    return args;
  }

  std::optional<std::string> BaseTest::getArgWithMatchingPattern(
    const std::string &pattern,
    const bool remove_match
  ) const {
    if (const auto &args {getArgs()}; !args.empty()) {
      const std::regex re_pattern {pattern};

      for (auto it {std::next(std::begin(args))}; it != std::end(args); ++it) {
        if (std::smatch match; std::regex_search(*it, match, re_pattern)) {
          return remove_match ? std::regex_replace(*it, re_pattern, "") : *it;
        }
      }
    }

    return std::nullopt;
  }

  bool BaseTest::isOutputSuppressed() const {
    return true;
  }

  bool BaseTest::isSystemTest() const {
    return false;
  }

  std::string BaseTest::skipTest() const {
    if (isSystemTest() && get_env("SKIP_SYSTEM_TESTS") == "1") {
      return "Skipping, this system test is disabled via SKIP_SYSTEM_TESTS=1 env.";
    }

    return {};
  }

  std::stringstream &BaseTest::coutBuffer() {
    return cout_buffer_;
  }

  std::stringstream &BaseTest::cerrBuffer() {
    return cerr_buffer_;
  }

  std::stringstream &BaseTest::stdoutBuffer() {
    return stdout_buffer_;
  }

  std::stringstream &BaseTest::stderrBuffer() {
    return stderr_buffer_;
  }

  void LinuxTest::SetUp() {
#if !defined(__linux__)
    GTEST_SKIP() << "Skipping, this test is for Linux only.";
#else
    BaseTest::SetUp();
#endif
  }

  ::testing::AssertionResult LinuxTest::HasReadableWritableDeviceNode(const char *path) {
#if defined(__linux__)
    if (::access(path, R_OK | W_OK) == 0) {
      return ::testing::AssertionSuccess();
    }

    return ::testing::AssertionFailure() << path << " must be readable and writable";
#else
    static_cast<void>(path);
    return ::testing::AssertionSuccess();
#endif
  }

  void MacOSTest::SetUp() {
#if !defined(__APPLE__) || !defined(__MACH__)
    GTEST_SKIP() << "Skipping, this test is for macOS only.";
#else
    BaseTest::SetUp();
#endif
  }

  void WindowsTest::SetUp() {
#if !defined(_WIN32)
    GTEST_SKIP() << "Skipping, this test is for Windows only.";
#else
    BaseTest::SetUp();
#endif
  }

  void BufferedTestEventListener::OnTestStart(const ::testing::TestInfo &test_info) {
    const std::string file {test_info.file() == nullptr ? "" : test_info.file()};
    logTestEvent("From " + file + ":" + std::to_string(test_info.line()));
    logTestEvent("  " + std::string {test_info.test_suite_name()} + "/" + test_info.name() + " started");
  }

  void BufferedTestEventListener::OnTestPartResult(const ::testing::TestPartResult &test_part_result) {
    const std::string file {test_part_result.file_name() == nullptr ? "" : test_part_result.file_name()};
    logTestEvent("At " + file + ":" + std::to_string(test_part_result.line_number()));

    const std::string result_text {
      test_part_result.passed()            ? "Success" :
      test_part_result.nonfatally_failed() ? "Non-fatal failure" :
      test_part_result.fatally_failed()    ? "Failure" :
                                             "Skip"
    };

    const std::string summary {test_part_result.summary()};
    const std::string message {test_part_result.message()};
    logTestEvent("  " + result_text + ": " + summary);
    if (message != summary) {
      logTestEvent("  " + message);
    }
  }

  void BufferedTestEventListener::OnTestEnd(const ::testing::TestInfo &test_info) {
    const auto &result {*test_info.result()};
    const std::string result_text {result.Passed() ? "passed" : result.Skipped() ? "skipped" :
                                                                                   "failed"};
    logTestEvent(std::string {test_info.test_suite_name()} + "/" + test_info.name() + " " + result_text);

    if (result.Failed()) {
      std::cout << bufferedTestOutput();
    }

    clearBufferedTestOutput();
  }

  void BufferedTestEventListener::logTestEvent(const std::string &message) {
    event_buffer_ << message << std::endl;
  }

  std::string BufferedTestEventListener::bufferedTestOutput() const {
    return event_buffer_.str();
  }

  void BufferedTestEventListener::clearBufferedTestOutput() {
    event_buffer_.str({});
    event_buffer_.clear();
  }
}  // namespace lizardbyte::common::testing
