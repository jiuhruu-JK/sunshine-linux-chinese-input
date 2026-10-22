# sunshine-cn-input —— Sunshine 主体（含中文输入文本桥）
#
# packaging/ 层：只描述"怎么编译"，源码来自仓库根目录（src/、third-party/、cmake/ …）。
#
# 边界（见 docs/sunshine-cn-input-ARCHITECTURE.md 第 5 节）：
#   - 本文件只做"Nix 沙箱里编得过"必需的脚手架修补：npm、boost、systemd/udev 路径、
#     Qt wrapper、以及 FHS 路径修正；
#   - 不改抓屏方式、编码器、权限模型、输入设备、托盘、桌面图标、启动器语义；
#   - 文本输入的改动全部落在 src/ 里（第 4.2 节白名单），不靠打包层注入。
{
  lib,
  stdenv,
  fetchzip,
  fetchFromGitHub,
  buildNpmPackage,
  cmake,
  pkg-config,
  python3,
  boost,
  curl,
  miniupnpc,
  nlohmann_json,
  openssl,
  libopus,
  qt6,
  avahi,
  libevdev,
  libpulseaudio,
  libXtst,
  libXrandr,
  libXi,
  libXfixes,
  libXdmcp,
  libX11,
  libxcb,
  libdrm,
  wayland,
  wayland-scanner,
  libffi,
  libcap,
  libgbm,
  pcre2,
  libuuid,
  libselinux,
  libsepol,
  libthai,
  libdatrie,
  libxkbcommon,
  libepoxy,
  libva,
  libvdpau,
  libglvnd,
  numactl,
  amf-headers,
  svt-av1,
  shaderc,
  vulkan-loader,
  libnotify,
  pipewire,
  glib,
  udev,
  udevCheckHook,
  autoPatchelfHook,
  makeWrapper,
  systemd,
  coreutils,

  version ? "dev",
  commit ? "unknown",
  withTests ? false,
  src ? ../.,
}:
let
  # fork 基线钉住的 build-deps 子模块版本
  # （= LizardByte/build-deps tag v2026.1004.34232）
  buildDepsRev = "bd28fbdd5511da8fc2ef303c381627a390045a78";

  # 预编译 FFmpeg 必须与 build-deps 的 tag 对齐，
  # 因为 build-deps 的 package-lock.cmake 声明了 dav1d/libva/opus/nv-codec-headers 版本
  buildDepsTag = "v2026.1004.34232";

  ffmpegArch = {
    x86_64-linux = "Linux-x86_64";
    aarch64-linux = "Linux-aarch64";
  }.${stdenv.hostPlatform.system} or (throw "sunshine-cn-input: 不支持的系统 ${stdenv.hostPlatform.system}");

  # upstream 的 cmake 在 configure 阶段会去下载预编译 ffmpeg。Nix 构建期不能联网，
  # 所以用固定输出 derivation 取回来，通过 FFMPEG_PREPARED_BINARIES 指过去。
  ffmpegPrebuilt = fetchzip {
    url = "https://github.com/LizardByte/build-deps/releases/download/${buildDepsTag}/${ffmpegArch}-ffmpeg.tar.gz";
    hash = "sha256-YazOwRB6tI543SJ6ijolUKZBTR+o+Z8X3uJchuaArMg=";
  };

  # build-deps 只用到它的 package-lock.cmake（CPM 依赖锁文件），单独取。
  buildDeps = fetchFromGitHub {
    owner = "LizardByte";
    repo = "build-deps";
    rev = buildDepsRev;
    hash = "sha256-Ubr1EBguSQ3Ah81EaUIVO+f4mPYUzPoxK//8lAfj7Xw=";
  };
in
stdenv.mkDerivation (finalAttrs: {
  pname = "sunshine-cn-input";
  inherit version src;

  # ---- WebUI：单独用 npm 构建，再把产物搬进主构建目录 ----
  ui = buildNpmPackage {
    inherit (finalAttrs) src version;
    pname = "sunshine-cn-input-ui";
    npmDepsHash = "sha256-eOhQxVEV4Nhps1WzN4igI8xdOjXPvGn/fOFCvGemKjc=";

    # vite 输出落在 <源码根>/build/assets/web，整份源码树搬进 $out，
    # 主构建再从 $out/build/assets/web 取。
    installPhase = ''
      runHook preInstall

      mkdir -p "$out"
      cp -a . "$out"/

      runHook postInstall
    '';
  };

  nativeBuildInputs = [
    cmake
    pkg-config
    # glad 的生成器在 configure 阶段需要 Jinja2 / setuptools；
    # GLAD_SKIP_PIP_INSTALL=ON 让 cmake 不要临时 pip 安装。
    (python3.withPackages (ps: [
      ps.jinja2
      ps.setuptools
    ]))
    makeWrapper
    qt6.wrapQtAppsHook
    wayland-scanner
    shaderc # configure 阶段编译着色器需要 glslc
    # 避免与上游 vendored ffmpeg 的库打架
    autoPatchelfHook
  ];

  buildInputs = [
    boost
    curl
    miniupnpc
    nlohmann_json
    openssl
    libopus
    qt6.qtbase
    qt6.qtsvg
    avahi
    libevdev
    libpulseaudio
    libXtst
    libXrandr
    libXi
    libXfixes
    libXdmcp
    libX11
    libxcb
    libdrm
    wayland
    libffi
    libcap
    libgbm
    pcre2
    libuuid
    libselinux
    libsepol
    libthai
    libdatrie
    libxkbcommon
    libepoxy
    libva
    libvdpau
    libglvnd
    numactl
    amf-headers
    svt-av1
    vulkan-loader
    libnotify
    pipewire
    glib
  ];

  # WebUI 单独构建，主构建不再需要 npm。
  postPatch = ''
    substituteInPlace cmake/targets/common.cmake \
      --replace-fail 'find_program(NPM npm REQUIRED)' ""
  ''
  # 用 nixpkgs 的 boost 代替 FetchContent；FETCH_CONTENT_BOOST_USED 阻止
  # Simple-Web-Server 再次 find_package boost。
  + ''
    sed -i -E 's/set\(BOOST_VERSION "[^"]*"\)/set(BOOST_VERSION "${boost.version}")/' \
      cmake/dependencies/Boost_Sunshine.cmake
    echo 'set(FETCH_CONTENT_BOOST_USED TRUE)' >> cmake/dependencies/Boost_Sunshine.cmake
  ''
  # 沙箱里没有 systemd/udev 的 FHS 目录，改为直接给出安装路径。
  + lib.optionalString stdenv.hostPlatform.isLinux ''
    substituteInPlace cmake/packaging/linux.cmake \
      --replace-fail 'find_package(Systemd)' "" \
      --replace-fail 'find_package(Udev)' ""

    # systemd 单元里的 /bin/sleep 是 FHS 路径。
    substituteInPlace packaging/linux/app-dev.lizardbyte.app.Sunshine.service.in \
      --replace-fail '/bin/sleep' '${lib.getExe' coreutils "sleep"}'

    # 桌面项的 Exec 走 systemd 用户单元，机制保持上游不变，只把 FHS 的
    # /usr/bin/env systemctl 换成 Nix store 里的 systemctl。
    substituteInPlace packaging/linux/dev.lizardbyte.app.Sunshine.desktop \
      --replace-fail '/usr/bin/env systemctl' '${lib.getExe' systemd "systemctl"}'
  '';

  cmakeFlags = [
    # nixpkgs 的 boost 只提供动态库
    (lib.cmakeBool "BOOST_USE_STATIC" false)
    (lib.cmakeBool "BUILD_DOCS" false)
    (lib.cmakeBool "BUILD_TESTS" withTests)
    (lib.cmakeBool "SUNSHINE_ENABLE_TRAY" true)
    (lib.cmakeBool "SUNSHINE_ENABLE_CUDA" false)
    # 用系统装的 vulkan-headers，不用上游子模块
    (lib.cmakeBool "SUNSHINE_SYSTEM_VULKAN_HEADERS" true)
    # 本仓库自己的发布信息
    (lib.cmakeFeature "SUNSHINE_PUBLISHER_NAME" "jiuhruu-JK")
    (lib.cmakeFeature "SUNSHINE_PUBLISHER_WEBSITE" "https://github.com/jiuhruu-JK/sunshine-linux-chinese-input")
    (lib.cmakeFeature "SUNSHINE_PUBLISHER_ISSUE_URL" "https://github.com/jiuhruu-JK/sunshine-linux-chinese-input/issues")
    # 避免 cmake 在 configure 阶段去下载预编译 ffmpeg
    (lib.cmakeFeature "FFMPEG_PREPARED_BINARIES" "${ffmpegPrebuilt}")
    # we provide Jinja2/setuptools via python3.withPackages; don't pip-install
    (lib.cmakeBool "GLAD_SKIP_PIP_INSTALL" true)
  ]
  ++ lib.optionals stdenv.hostPlatform.isLinux [
    (lib.cmakeBool "UDEV_FOUND" true)
    (lib.cmakeBool "SYSTEMD_FOUND" true)
    (lib.cmakeFeature "UDEV_RULES_INSTALL_DIR" "lib/udev/rules.d")
    (lib.cmakeFeature "SYSTEMD_USER_UNIT_INSTALL_DIR" "lib/systemd/user")
    (lib.cmakeFeature "SYSTEMD_MODULES_LOAD_DIR" "lib/modules-load.d")
    # 生成的 systemd 单元里的 ExecStart 指向被 wrap 之后的可执行文件
    (lib.cmakeFeature "SUNSHINE_EXECUTABLE_PATH" "${placeholder "out"}/bin/sunshine")
  ];

  env = {
    # 触发 cmake 的版本计算
    BUILD_VERSION = finalAttrs.version;
    BRANCH = "master";
    COMMIT = commit;
  };

  # build-deps 子模块没有收录进仓库（只用到它的 package-lock.cmake）。
  prePatch = ''
    mkdir -p third-party/build-deps
    cp ${buildDeps}/package-lock.cmake third-party/build-deps/package-lock.cmake
  '';

  # 把 WebUI 产物搬进 cmake 构建目录（上游从
  # ${CMAKE_CURRENT_BINARY_DIR}/assets/web 安装它）。
  preBuild = ''
    cp -r ${finalAttrs.ui}/build/assets/web ../build/assets/
  '';

  buildFlags = [
    "sunshine"
  ] ++ lib.optional withTests [
    "test_sunshine"
  ];

  # 绕开上游的 WebUI 构建（已经单独用 npm 构建过）。
  # 单元测试变体：跑与文本输入桥相关的用例，并把结果装进 $out。
  installPhase = if withTests then ''
    runHook preInstall

    # tee 会把管道退出码变成自己的；没有 pipefail 时测试失败也会被吞掉。
    set -o pipefail
    mkdir -p "$out/share/sunshine-cn-input"
    ./tests/test_sunshine --gtest_filter='InputMethod*' 2>&1 | tee "$out/share/sunshine-cn-input/test-results.txt"

    runHook postInstall
  '' else ''
    runHook preInstall

    cmake --install .

    runHook postInstall
  '';

  # 上游的测试工程没有注册 ctest 用例，make check 会因为「没找到测试」而失败；
  # 我们自己在 installPhase 里直接跑测试二进制。
  dontCheck = withTests;

  # udev 规则由上游原样安装，校验一下（与 nixpkgs 的 sunshine 包一致）。
  doInstallCheck = stdenv.hostPlatform.isLinux && !withTests;
  nativeInstallCheckInputs = [ udevCheckHook ];

  dontWrapQtApps = true;

  # 单元测试变体不产出 sunshine 可执行文件，不用 wrap。
  postFixup = lib.optionalString (!withTests) ''
    wrapProgram $out/bin/sunshine \
      "''${qtWrapperArgs[@]}"

    # KWin 的 zkde_screencast 按 .desktop 里的 Exec 与 /proc/<pid>/exe 比对，
    # wrap 之后真实路径是 .sunshine-wrapped，这里同步改掉，
    # 否则 KWin 会拒绝给 Sunshine 抓屏权限。
    if [ -f "$out/share/applications/dev.lizardbyte.app.Sunshine.kwin.desktop" ]; then
      substituteInPlace "$out/share/applications/dev.lizardbyte.app.Sunshine.kwin.desktop" \
        --replace-fail "$out/bin/sunshine" "$out/bin/.sunshine-wrapped"
    fi
  '';

  # dlopen 的库（avahi 等）不会被 autoPatchelf 发现，必须显式写进 RUNPATH；
  # 与 nixpkgs 的 sunshine 包保持一致。
  runtimeDependencies = [
    libglvnd
  ] ++ lib.optionals stdenv.hostPlatform.isLinux [
    avahi
    libgbm
    libXrandr
    libxcb
  ];

  meta = {
    description = "Game stream host for Moonlight, with a fcitx5 text input bridge";
    homepage = "https://github.com/jiuhruu-JK/sunshine-linux-chinese-input";
    license = lib.licenses.gpl3Only;
    platforms = [
      "x86_64-linux"
      "aarch64-linux"
    ];
    mainProgram = "sunshine";
  };
})
