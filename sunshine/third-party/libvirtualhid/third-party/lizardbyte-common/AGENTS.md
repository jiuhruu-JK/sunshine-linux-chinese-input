On Windows we use msys2 and ucrt64 to compile.
You need to prefix commands with `C:\msys64\msys2_shell.cmd -defterm -here -no-start -ucrt64 -c`.

Prefix build directories with `cmake-build-`.

The test executable is named `test_lizardbyte_common` and will be located inside the `tests` directory within
the build directory.

The project uses gtest as a test framework. GoogleTest is vendored as a submodule under `third-party/googletest`.

Keep the public c++ API platform-neutral. Project-specific details from consuming projects should not leak into
consumer code.

The production c++ target is `lizardbyte::common`; keep it free of project-specific dependencies.

The reusable gtest support target is `lizardbyte::test_support`; it may depend on GoogleTest, but should not depend
on project-specific libraries from Sunshine, tray, libvirtualhid, libdisplaydevice, or Moonlight-XboxOG.

Public production headers live under `src/include/lizardbyte/common/`.

Shared test-support headers live under `tests/support/include/lizardbyte/common/`.

Documentation uses the shared `third-party/doxyconfig` submodule and Read the Docs configuration.

Always update public documentation when changing headers or consumer-facing behavior.

Always follow the style guidelines defined in .clang-format for c/c++ code when that file is present.
