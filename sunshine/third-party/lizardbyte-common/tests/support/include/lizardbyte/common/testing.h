/**
 * @file tests/support/include/lizardbyte/common/testing.h
 * @brief Shared GoogleTest support helpers.
 */
#pragma once

// standard includes
#include <optional>
#include <sstream>
#include <string>
#include <vector>

// lib includes
#include <gtest/gtest.h>

namespace lizardbyte::common::testing {
  /**
   * @brief Base class used by default for shared tests.
   *
   * ``cout``, ``cerr``, ``stdout``, and ``stderr`` are redirected during tests and printed when a test fails.
   */
  class BaseTest: public ::testing::Test {
  protected:
    /**
     * @brief Tear down the test base.
     */
    ~BaseTest() override = default;

    /**
     * @brief Set up the test.
     */
    void SetUp() override;

    /**
     * @brief Tear down the test.
     */
    void TearDown() override;

    /**
     * @brief Get available command line arguments.
     * @return Command line args from GoogleTest.
     */
    [[nodiscard]] virtual const std::vector<std::string> &getArgs() const;

    /**
     * @brief Get the command line argument that matches the pattern.
     * @param pattern Pattern to look for.
     * @param remove_match Specify if the matched pattern should be removed before returning the argument.
     * @return Matching command line argument, or null optional if nothing matched.
     */
    [[nodiscard]] virtual std::optional<std::string> getArgWithMatchingPattern(
      const std::string &pattern,
      bool remove_match
    ) const;

    /**
     * @brief Check if test output should be printed only when the test fails.
     * @return True if output is suppressed, false otherwise.
     */
    [[nodiscard]] virtual bool isOutputSuppressed() const;

    /**
     * @brief Check if the test interacts with system settings.
     * @return True if it does, false otherwise.
     *
     * Set ``SKIP_SYSTEM_TESTS=1`` to skip tests that return true here.
     */
    [[nodiscard]] virtual bool isSystemTest() const;

    /**
     * @brief Skip the test by specifying the reason.
     * @return A non-empty string if the test needs to be skipped, empty string otherwise.
     */
    [[nodiscard]] virtual std::string skipTest() const;

    /**
     * @brief Get captured cout.
     * @return Captured cout stream.
     */
    [[nodiscard]] std::stringstream &coutBuffer();

    /**
     * @brief Get captured cerr.
     * @return Captured cerr stream.
     */
    [[nodiscard]] std::stringstream &cerrBuffer();

    /**
     * @brief Get captured stdout.
     * @return Captured stdout stream.
     */
    [[nodiscard]] std::stringstream &stdoutBuffer();

    /**
     * @brief Get captured stderr.
     * @return Captured stderr stream.
     */
    [[nodiscard]] std::stringstream &stderrBuffer();

  private:
    std::stringstream cout_buffer_; /**< Stores cout while output is suppressed. */
    std::stringstream cerr_buffer_; /**< Stores cerr while output is suppressed. */
    std::stringstream stdout_buffer_; /**< Stores stdout while output is suppressed. */
    std::stringstream stderr_buffer_; /**< Stores stderr while output is suppressed. */
    std::streambuf *cout_streambuf_ {nullptr}; /**< Original cout stream buffer. */
    std::streambuf *cerr_streambuf_ {nullptr}; /**< Original cerr stream buffer. */
    bool test_skipped_at_setup_ {false}; /**< True when SetUp skipped before redirection. */
    bool output_suppressed_ {false}; /**< True when output capture was enabled in SetUp. */
    bool stdout_capture_active_ {false}; /**< True when GoogleTest stdout capture is active. */
    bool stderr_capture_active_ {false}; /**< True when GoogleTest stderr capture is active. */
  };

  /**
   * @brief Base class for Linux-only tests.
   */
  class LinuxTest: public BaseTest {
  protected:
    /**
     * @brief Set up the test.
     */
    void SetUp() override;

    /**
     * @brief Check that a Linux device node is readable and writable.
     * @param path Device node path.
     * @return GoogleTest assertion result.
     */
    static ::testing::AssertionResult HasReadableWritableDeviceNode(const char *path);
  };

  /**
   * @brief Base class for macOS-only tests.
   */
  class MacOSTest: public BaseTest {
  protected:
    /**
     * @brief Set up the test.
     */
    void SetUp() override;
  };

  /**
   * @brief Base class for Windows-only tests.
   */
  class WindowsTest: public BaseTest {
  protected:
    /**
     * @brief Set up the test.
     */
    void SetUp() override;
  };

  /**
   * @brief GoogleTest event listener that buffers test log output until a test fails.
   */
  class BufferedTestEventListener: public ::testing::EmptyTestEventListener {
  public:
    /**
     * @brief Handle the start of a test.
     * @param test_info GoogleTest test information.
     */
    void OnTestStart(const ::testing::TestInfo &test_info) override;

    /**
     * @brief Handle a test assertion result.
     * @param test_part_result GoogleTest assertion result.
     */
    void OnTestPartResult(const ::testing::TestPartResult &test_part_result) override;

    /**
     * @brief Handle the end of a test.
     * @param test_info GoogleTest test information.
     */
    void OnTestEnd(const ::testing::TestInfo &test_info) override;

  protected:
    /**
     * @brief Add a test event line to the buffer.
     * @param message Message to buffer.
     */
    virtual void logTestEvent(const std::string &message);

    /**
     * @brief Get buffered test output.
     * @return Buffered output.
     */
    [[nodiscard]] virtual std::string bufferedTestOutput() const;

    /**
     * @brief Clear buffered test output.
     */
    virtual void clearBufferedTestOutput();

  private:
    std::stringstream event_buffer_; /**< Stores event log output while tests run. */
  };
}  // namespace lizardbyte::common::testing

#if !defined(LIZARDBYTE_COMMON_TESTING_NO_GLOBAL_ALIASES)
/**
 * @brief Global compatibility alias for the shared base test fixture.
 */
using BaseTest = ::lizardbyte::common::testing::BaseTest;

/**
 * @brief Global compatibility alias for the shared Linux-only test fixture.
 */
using LinuxTest = ::lizardbyte::common::testing::LinuxTest;

/**
 * @brief Global compatibility alias for the shared macOS-only test fixture.
 */
using MacOSTest = ::lizardbyte::common::testing::MacOSTest;

/**
 * @brief Global compatibility alias for the shared Windows-only test fixture.
 */
using WindowsTest = ::lizardbyte::common::testing::WindowsTest;

/**
 * @brief Global compatibility alias for the shared buffered test event listener.
 */
using BufferedTestEventListener = ::lizardbyte::common::testing::BufferedTestEventListener;
#endif

#if !defined(LIZARDBYTE_COMMON_TESTING_KEEP_GTEST_TEST)
  #undef TEST  // NOSONAR(cpp:S959): Tests intentionally wrap TEST to use BaseTest.

  /**
   * @brief Redefine TEST to automatically use the shared BaseTest fixture.
   */
  #define TEST(test_case_name, test_name) \
    GTEST_TEST_( \
      test_case_name, \
      test_name, \
      ::lizardbyte::common::testing::BaseTest, \
      ::testing::internal::GetTypeId<::lizardbyte::common::testing::BaseTest>() \
    )
#endif
