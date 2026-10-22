/**
 * @file tests/cpp/test_testing.cpp
 * @brief Unit tests for shared GoogleTest support helpers.
 */

// standard includes
#include <cstdio>
#include <iostream>
#include <optional>
#include <string>

// local includes
#include <lizardbyte/common/env.h>
#include <lizardbyte/common/testing.h>

namespace {
  class TestableBaseTest: public BaseTest {
  public:
    using BaseTest::cerrBuffer;
    using BaseTest::coutBuffer;
    using BaseTest::getArgWithMatchingPattern;
    using BaseTest::isOutputSuppressed;
    using BaseTest::isSystemTest;
    using BaseTest::skipTest;
    using BaseTest::stderrBuffer;
    using BaseTest::stdoutBuffer;
  };

  class EnvGuard {
  public:
    explicit EnvGuard(std::string name):
        name_ {std::move(name)},
        had_value_ {lizardbyte::common::get_env(name_, old_value_)} {
      static_cast<void>(lizardbyte::common::unset_env(name_));
    }

    ~EnvGuard() {
      if (had_value_) {
        static_cast<void>(lizardbyte::common::set_env(name_, old_value_));
      } else {
        static_cast<void>(lizardbyte::common::unset_env(name_));
      }
    }

  private:
    std::string name_;
    std::string old_value_;
    bool had_value_;
  };

  class SystemTestFixture: public BaseTest {
  protected:
    void SetUp() override {
      skip_system_tests_guard_.emplace("SKIP_SYSTEM_TESTS");
      BaseTest::SetUp();
    }

    [[nodiscard]] bool isSystemTest() const override {
      return true;
    }

  private:
    std::optional<EnvGuard> skip_system_tests_guard_;
  };

  class OutputVisibleFixture: public BaseTest {
  protected:
    [[nodiscard]] bool isOutputSuppressed() const override {
      return false;
    }
  };

  class StdioCaptureFixture: public TestableBaseTest {
  protected:
    void TearDown() override {
      BaseTest::TearDown();
      EXPECT_EQ(stdoutBuffer().str(), "captured stdout");
      EXPECT_EQ(stderrBuffer().str(), "captured stderr");
    }
  };

  class TestableBufferedTestEventListener: public BufferedTestEventListener {
  public:
    using BufferedTestEventListener::clearBufferedTestOutput;
    using BufferedTestEventListener::logTestEvent;

    [[nodiscard]] std::string output() const {
      return bufferedTestOutput();
    }
  };
}  // namespace

TEST(TestingSupportTest, DefaultTestMacroUsesBaseFixture) {
  EXPECT_TRUE(isOutputSuppressed());
  std::cout << "captured cout";
  std::cerr << "captured cerr";
  EXPECT_EQ(coutBuffer().str(), "captured cout");
  EXPECT_EQ(cerrBuffer().str(), "captured cerr");
}

TEST_F(StdioCaptureFixture, CapturesStdoutAndStderr) {
  std::printf("captured stdout");
  std::fprintf(stderr, "captured stderr");
  std::fflush(stdout);
  std::fflush(stderr);
}

TEST(TestingSupportTest, ArgumentMatchingCanReturnFullArgument) {
  EXPECT_TRUE(getArgWithMatchingPattern("--gtest_", false).has_value());
}

TEST(TestingSupportTest, ArgumentMatchingCanRemoveMatchedPrefix) {
  const auto argument = getArgWithMatchingPattern("--gtest_", true);

  ASSERT_TRUE(argument.has_value());
  EXPECT_FALSE(argument->empty());
}

TEST(TestingSupportTest, DefaultBaseTestIsNotSystemTest) {
  EXPECT_FALSE(isSystemTest());
  EXPECT_EQ(skipTest(), "");
}

TEST_F(OutputVisibleFixture, CanDisableOutputSuppression) {
  EXPECT_FALSE(isOutputSuppressed());
}

TEST_F(SystemTestFixture, RespectsSkipSystemTestsEnvironment) {
  EXPECT_EQ(skipTest(), "");
  EXPECT_EQ(lizardbyte::common::set_env("SKIP_SYSTEM_TESTS", "1"), 0);
  EXPECT_NE(skipTest(), "");
}

TEST_F(TestableBaseTest, HelpersAreAvailableOnDerivedFixtures) {
  EXPECT_TRUE(isOutputSuppressed());
  EXPECT_FALSE(isSystemTest());
}

TEST(TestingSupportTest, BufferedEventListenerOutputCanBeCustomized) {
  TestableBufferedTestEventListener listener;

  listener.logTestEvent("first line");
  listener.logTestEvent("second line");
  EXPECT_EQ(listener.output(), "first line\nsecond line\n");

  listener.clearBufferedTestOutput();
  EXPECT_TRUE(listener.output().empty());
}

TEST_F(LinuxTest, SkipsOrRunsLinuxFixture) {
#if defined(__linux__)
  SUCCEED();
#else
  GTEST_FAIL() << "LinuxTest should skip before the test body on non-Linux platforms.";
#endif
}

TEST_F(MacOSTest, SkipsOrRunsMacOSFixture) {
#if defined(__APPLE__) && defined(__MACH__)
  SUCCEED();
#else
  GTEST_FAIL() << "MacOSTest should skip before the test body on non-macOS platforms.";
#endif
}

TEST_F(WindowsTest, SkipsOrRunsWindowsFixture) {
#if defined(_WIN32)
  SUCCEED();
#else
  GTEST_FAIL() << "WindowsTest should skip before the test body on non-Windows platforms.";
#endif
}
