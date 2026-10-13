/**
 * @file tests/cpp/test_env.cpp
 * @brief Unit tests for environment variable helpers.
 */

// standard includes
#include <cerrno>
#include <cstdlib>
#include <string>
#include <utility>

// local includes
#include <lizardbyte/common/env.h>
#include <lizardbyte/common/testing.h>

namespace {
  constexpr auto test_env_name {"LIZARDBYTE_COMMON_TEST_ENV"};
  constexpr auto github_actions_env_name {"GITHUB_ACTIONS"};

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
}  // namespace

TEST(EnvTest, GitHubActionsIsFalseWhenEnvironmentVariableIsMissing) {
  EnvGuard guard {github_actions_env_name};

  EXPECT_FALSE(lizardbyte::common::is_github_actions());
}

TEST(EnvTest, GitHubActionsIsTrueWhenEnvironmentVariableExists) {
  EnvGuard guard {github_actions_env_name};

  ASSERT_EQ(lizardbyte::common::set_env(github_actions_env_name, "true"), 0);
  EXPECT_TRUE(lizardbyte::common::is_github_actions());
}

TEST(EnvTest, GetEnvReturnsFalseForMissingVariable) {
  EnvGuard guard {test_env_name};

  std::string value {"unchanged"};

  EXPECT_FALSE(lizardbyte::common::get_env(test_env_name, value));
  EXPECT_EQ(value, "unchanged");
  EXPECT_EQ(lizardbyte::common::get_env(test_env_name), "");
}

TEST(EnvTest, SetEnvUpdatesEnvironmentVariable) {
  EnvGuard guard {test_env_name};

  std::string value;

  EXPECT_EQ(lizardbyte::common::set_env(test_env_name, "alpha"), 0);
  EXPECT_TRUE(lizardbyte::common::get_env(test_env_name, value));
  EXPECT_EQ(value, "alpha");
  EXPECT_EQ(lizardbyte::common::get_env(test_env_name), "alpha");
  EXPECT_STREQ(std::getenv(test_env_name), "alpha");
}

TEST(EnvTest, AppendEnvSetsMissingEnvironmentVariable) {
  EnvGuard guard {test_env_name};

  std::string value;

  EXPECT_EQ(lizardbyte::common::append_env(test_env_name, "alpha", ";"), 0);
  EXPECT_TRUE(lizardbyte::common::get_env(test_env_name, value));
  EXPECT_EQ(value, "alpha");
}

TEST(EnvTest, AppendEnvAppendsWithSeparator) {
  EnvGuard guard {test_env_name};

  std::string value;

  EXPECT_EQ(lizardbyte::common::set_env(test_env_name, "alpha"), 0);
  EXPECT_EQ(lizardbyte::common::append_env(test_env_name, "beta", ";"), 0);
  EXPECT_TRUE(lizardbyte::common::get_env(test_env_name, value));
  EXPECT_EQ(value, "alpha;beta");
}

TEST(EnvTest, AppendEnvSkipsExistingValue) {
  EnvGuard guard {test_env_name};

  std::string value;

  EXPECT_EQ(lizardbyte::common::set_env(test_env_name, "alpha;beta"), 0);
  EXPECT_EQ(lizardbyte::common::append_env(test_env_name, "beta", ";"), 0);
  EXPECT_TRUE(lizardbyte::common::get_env(test_env_name, value));
  EXPECT_EQ(value, "alpha;beta");
}

TEST(EnvTest, AppendEnvMatchesSunshineCommaSeparatedUse) {
  EnvGuard guard {test_env_name};

  std::string value;

  EXPECT_EQ(lizardbyte::common::append_env(test_env_name, "video_encode", ","), 0);
  EXPECT_EQ(lizardbyte::common::append_env(test_env_name, "rt", ","), 0);
  EXPECT_EQ(lizardbyte::common::append_env(test_env_name, "video_encode", ","), 0);
  EXPECT_TRUE(lizardbyte::common::get_env(test_env_name, value));
  EXPECT_EQ(value, "video_encode,rt");
}

TEST(EnvTest, UnsetEnvRemovesEnvironmentVariable) {
  EnvGuard guard {test_env_name};

  std::string value;

  EXPECT_EQ(lizardbyte::common::set_env(test_env_name, "alpha"), 0);
  EXPECT_TRUE(lizardbyte::common::get_env(test_env_name, value));
  EXPECT_EQ(lizardbyte::common::unset_env(test_env_name), 0);
  EXPECT_FALSE(lizardbyte::common::get_env(test_env_name, value));
}

TEST(EnvTest, InvalidEnvNamesAreRejected) {
  std::string value {"unchanged"};

  EXPECT_FALSE(lizardbyte::common::get_env("", value));
  EXPECT_FALSE(lizardbyte::common::get_env("INVALID=NAME", value));
  EXPECT_EQ(lizardbyte::common::get_env(""), "");
  EXPECT_EQ(lizardbyte::common::get_env("INVALID=NAME"), "");
  EXPECT_EQ(lizardbyte::common::set_env("", "value"), EINVAL);
  EXPECT_EQ(lizardbyte::common::set_env("INVALID=NAME", "value"), EINVAL);
  EXPECT_EQ(lizardbyte::common::append_env("", ""), EINVAL);
  EXPECT_EQ(lizardbyte::common::append_env("INVALID=NAME", ""), EINVAL);
  EXPECT_EQ(lizardbyte::common::unset_env(""), EINVAL);
  EXPECT_EQ(lizardbyte::common::unset_env("INVALID=NAME"), EINVAL);
  EXPECT_EQ(value, "unchanged");
}
