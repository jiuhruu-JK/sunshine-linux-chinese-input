/**
 * @file src/common/env.cpp
 * @brief Environment variable helper implementation.
 */

// standard includes
#include <cerrno>
#include <cstdlib>

// local includes
#include <lizardbyte/common/env.h>

namespace lizardbyte::common {
  namespace {
    [[nodiscard]] bool is_valid_name(const std::string &name) {
      return !name.empty() && name.find('=') == std::string::npos;
    }
  }  // namespace

  bool is_github_actions() {
    std::string value;
    return get_env("GITHUB_ACTIONS", value);
  }

  bool get_env(const std::string &name, std::string &value) {
    if (!is_valid_name(name)) {
      return false;
    }

#if defined(_WIN32) && defined(_MSC_VER)
    char *buffer {};
    std::size_t buffer_size {};
    if (_dupenv_s(&buffer, &buffer_size, name.c_str()) != 0 || buffer == nullptr) {
      return false;
    }

    value = buffer;
    std::free(buffer);
    return true;
#else
    const auto *env_value = std::getenv(name.c_str());
    if (env_value == nullptr) {
      return false;
    }

    value = env_value;
    return true;
#endif
  }

  std::string get_env(const std::string &name) {
    std::string value;
    static_cast<void>(get_env(name, value));
    return value;
  }

  int set_env(const std::string &name, const std::string &value) {
    if (!is_valid_name(name)) {
      return EINVAL;
    }

#if defined(_WIN32)
    return _putenv_s(name.c_str(), value.c_str());
#else
    return setenv(name.c_str(), value.c_str(), 1);
#endif
  }

  int append_env(const std::string &name, const std::string &value, const std::string &separator) {
    if (!is_valid_name(name)) {
      return EINVAL;
    }

    std::string old_value;
    static_cast<void>(get_env(name, old_value));

    if (old_value.find(value) != std::string::npos) {
      return 0;
    }

    if (old_value.empty()) {
      return set_env(name, value);
    }

    return set_env(name, old_value + separator + value);
  }

  int unset_env(const std::string &name) {
    if (!is_valid_name(name)) {
      return EINVAL;
    }

#if defined(_WIN32)
    return _putenv_s(name.c_str(), "");
#else
    return unsetenv(name.c_str());
#endif
  }
}  // namespace lizardbyte::common
