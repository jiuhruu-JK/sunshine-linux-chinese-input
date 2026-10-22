# sunshine-cn-input —— Sunshine + Linux 中文输入接管
#
# packaging/ 层：只描述"怎么编译"，不改任何源码。
# 源码来自仓库根目录（= 上游 + 文本输入改动），由 flake.nix 传入。
#
# 允许写在这里：源、依赖、构建参数、以及在 Nix 沙箱里编过所需的构建脚手架修补
# （build-deps 子模块、npm、systemd/udev 路径、Qt wrapper）。
# 不允许：改抓屏、编码、权限、输入设备、托盘、桌面启动行为。
{
  lib,
  stdenv,
  cmake,
  fetchFromGitHub,
  fetchzip,
  autoPatchelfHook,
  makeWrapper,
  buildNpmPackage,
  pkg-config,
  python3,
  coreutils,
  wayland-scanner,
  shaderc,
  vulkan-loader,
  vulkan-headers,
  boost,
  curl,
  miniupnpc,
  nlohmann_json,
  openssl,
  libopus,
  glib,
  qt6,
  avahi,
  libevdev,
  libpulseaudio,
  libx11,
  libxcb,
  libxfixes,
  libxrandr,
  libxtst,
  libxi,
  libdrm,
  wayland,
  libffi,
  libcap,
  pcre2,
  libuuid,
  libselinux,
  libsepol,
  libthai,
  libdatrie,
  libxdmcp,
  libxkbcommon,
  libepoxy,
  libva,
  libvdpau,
  numactl,
  libgbm,
  amf-headers,
  svt-av1,
  pipewire,
  libnotify,
  nix-update-script,

  # 由 flake.nix 传入
  src ? ../.,
  version ? "dev",
  commit ? "unknown",
}:

let
  inherit (lib) optionals optionalString;

  # fork 基线 v2026.1011.160319 钉住的 build-deps 子模块版本
  # （= LizardByte/build-deps tag v2026.1004.34232）
  buildDepsRev = "bd28fbdd5511da8fc2ef303c381627a390045a78";

  # 预编译 FFmpeg 必须与 build-deps 的 tag 对齐，
  # 因为 build-deps 的 package-lock.cmake 声明了 dav1d/libva/opus/nv-codec-headers 版本
  buildDepsTag = "v2026.1004.34232";

  ffmpegArch = {
    x86_64-linux = "Linux-x86_64";
    aarch64-linux = "Linux-aarch64";
  }.${stdenv.hostPlatform.system} or (throw "sunshine-cn-input: 不支持的系统 ${stdenv.hostPlatform.system}");

  ffmpegPrebuilt = fetchzip {
    url = "https://github.com/LizardByte/build-deps/releases/download/${buildDepsTag}/${ffmpegArch}-ffmpeg.tar.gz";
    # 与 nix-prefetch-url --unpack 的结果一致
    hash = "sha256-YazOwRB6tI543SJ6ijolUKZBTR+o+Z8X3uJchuaArMg=";
  };

  buildDeps = fetchFromGitHub {
    owner = "LizardByte";
    repo = "build-deps";
    rev = buildDepsRev;
    hash = "sha256-Ubr1EBguSQ3Ah81EaUIVO+f4mPYUzPoxK//8lAfj7Xw=";
  };
in
stdenv.mkDerivation (finalAttrs: {
  pname = "sunshine-cn-input";
  inherit version;

  __structuredAttrs = true;
  strictDeps = true;

  # WebUI 单独构建：fork 仓库的 vite 输出落在 <src>/build/assets/web
  ui = buildNpmPackage {
    inherit (finalAttrs) version;
    pname = "sunshine-cn-input-ui";
    # 仓库根目录没有 package-lock.json，WebUI 实际位于 sunshine/ 子目录
    src = "${finalAttrs.src}";
    npmDepsHash = "sha256-3y0tSlJhOVBJ7KbGmukpF9s78UX3cPtbhj0cU3OZwP0=";

    installPhase = ''
      runHook preInstall

      mkdir -p "$out"
      cp -a . "$out"/

      runHook postInstall
    '';
  };

  postPatch = ''
    # --- 1. 补上缺失的 build-deps 子模块内容 ---------------------------------
    # fork 仓库没有提交 third-party/build-deps，但 CMakeLists.txt:83 强制 include
    # 它的 package-lock.cmake。该文件声明 dav1d/libva/opus/nv-codec-headers 的
    # CPM 依赖；这些在 Linux 下都由预编译 FFmpeg 自带，故只需声明不被触发下载。
    mkdir -p third-party/build-deps
    cp ${buildDeps}/package-lock.cmake third-party/build-deps/package-lock.cmake

    # --- 2. WebUI：摘掉 npm 查找，改为单独构建后拷入 -----------------------
    substituteInPlace cmake/targets/common.cmake \
      --replace-fail 'find_program(NPM npm REQUIRED)' ""

    # --- 3. Boost：fork 用 find_package(Boost <min> CONFIG COMPONENTS ...) -----
    # nixpkgs 的 boost 1.89.0 恰好满足 fork 的 BOOST_MINIMUM_VERSION，
    # 但只提供共享库，必须关掉静态链接。
    # 同时阻止 Simple-Web-Server 再次 find_package 出 Boost::system。
    echo 'set(FETCH_CONTENT_BOOST_USED TRUE)' >> cmake/dependencies/Boost_Sunshine.cmake

    # --- 4. 摘掉 systemd / udev 的 FHS 路径查找 -----------------------------
    substituteInPlace cmake/packaging/linux.cmake \
      --replace-fail 'find_package(Systemd)' "" \
      --replace-fail 'find_package(Udev)' ""

    # 桌面图标不再直接 exec sunshine。直接启动会拉起第二个实例去抢
    # 47984/47989/47990 端口，而它没有 cap_sys_admin，抓屏必然失败，
    # 还会把正在跑的服务搞得看起来"挂了"。
    # 改成：确保后台服务在跑 → 打开配置界面。点几次都安全，幂等。
    substituteInPlace packaging/linux/dev.lizardbyte.app.Sunshine.desktop       --replace-fail '/usr/bin/env systemctl start --u app-@PROJECT_FQDN@' 'sunshine'

    substituteInPlace packaging/linux/app-dev.lizardbyte.app.Sunshine.service.in \
      --replace-fail '/bin/sleep' '${lib.getExe' coreutils "sleep"}'


  '';

  nativeBuildInputs = [
    cmake
    pkg-config
    # glad 的生成器需要 jinja2 + setuptools
    (python3.withPackages (ps: [
      ps.jinja2
      ps.setuptools
    ]))
    makeWrapper
    qt6.wrapQtAppsHook
    wayland-scanner
    shaderc
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
    # input_method.cpp 通过 GIO 与 KWin 的 org.kde.Kwin.VirtualKeyboard 通信
    glib
  ]
  ++ optionals stdenv.hostPlatform.isLinux [
    avahi
    libevdev
    libpulseaudio
    libx11
    libxcb
    libxfixes
    libxrandr
    libxtst
    libxi
    libdrm
    wayland
    libffi
    libcap
    pcre2
    libuuid
    libselinux
    libsepol
    libthai
    libdatrie
    libxdmcp
    libxkbcommon
    libepoxy
    libva
    libvdpau
    numactl
    libgbm
    amf-headers
    svt-av1
    vulkan-loader
    pipewire
    libnotify
  ];

  runtimeDependencies = optionals stdenv.hostPlatform.isLinux [
    avahi
    libgbm
    libxrandr
    libxcb
  ];

  cmakeFlags = [
    "-Wno-dev"
    (lib.cmakeBool "BOOST_USE_STATIC" false)
    (lib.cmakeBool "BUILD_DOCS" false)
    (lib.cmakeBool "BUILD_TESTS" false)
    # 用系统的 vulkan-headers，避开 build-deps 里的 Vulkan-Headers 子模块
    (lib.cmakeBool "SUNSHINE_SYSTEM_VULKAN_HEADERS" true)
    (lib.cmakeFeature "SUNSHINE_PUBLISHER_NAME" "jiuhruu-JK")
    (lib.cmakeFeature "SUNSHINE_PUBLISHER_WEBSITE" "https://github.com/jiuhruu-JK")
    (lib.cmakeFeature "SUNSHINE_PUBLISHER_ISSUE_URL" "https://github.com/jiuhruu-JK/sunshine-linux-chinese-input/issues")
    # 避免 cmake 在 configure 阶段联网下载 build-deps 的 ffmpeg tarball
    (lib.cmakeFeature "FFMPEG_PREPARED_BINARIES" "${ffmpegPrebuilt}")
    # 我们已经提供带 jinja2 的 python，不要 pip 安装
    (lib.cmakeBool "GLAD_SKIP_PIP_INSTALL" true)
  ]
  ++ optionals stdenv.hostPlatform.isLinux [
    (lib.cmakeBool "UDEV_FOUND" true)
    (lib.cmakeBool "SYSTEMD_FOUND" true)
    (lib.cmakeFeature "UDEV_RULES_INSTALL_DIR" "lib/udev/rules.d")
    (lib.cmakeFeature "SYSTEMD_USER_UNIT_INSTALL_DIR" "lib/systemd/user")
    (lib.cmakeFeature "SYSTEMD_MODULES_LOAD_DIR" "lib/modules-load.d")
    # 生成的 systemd unit 的 ExecStart= 用它
    (lib.cmakeFeature "SUNSHINE_EXECUTABLE_PATH" "${placeholder "out"}/bin/sunshine")
  ]
  # 本机是 AMD，始终关 CUDA（fork 默认 SUNSHINE_ENABLE_CUDA=ON，
  # 找不到 CUDA 编译器时 cmake 会 FATAL_ERROR）
  ++ [
    (lib.cmakeBool "SUNSHINE_ENABLE_CUDA" false)
  ];

  env = {
    # 触发 cmake 的版本配置
    BUILD_VERSION = finalAttrs.version;
    BRANCH = "master";
    COMMIT = commit;
  };

  # 把 WebUI 产物放到 cmake 期望的位置
  preBuild = ''
    mkdir -p assets
    cp -r ${finalAttrs.ui}/build/assets/web assets/web
  '';

  buildFlags = [ "sunshine" ];

  # 改写 installPhase，避免构建 webui
  installPhase = ''
    runHook preInstall

    cmake --install .

    runHook postInstall
  '';

  dontWrapQtApps = true;

  postFixup = ''
    wrapProgram $out/bin/sunshine \
      "''${qtWrapperArgs[@]}" \
      --set LD_LIBRARY_PATH ${lib.makeLibraryPath [ vulkan-loader ]}

    # KWin 对 zkde_screencast_unstable_v1 做权限校验：拿 /proc/<pid>/exe 的
    # 真实路径去匹配 XDG data 里 .desktop 的 Exec=。wrapProgram 之后进程真实
    # 可执行文件是 bin/.sunshine-wrapped，而包自带的 kwin.desktop 写的是
    # bin/sunshine，两者对不上 → KWin 拒绝绑定 → Sunshine 报
    # "zkde_screencast_unstable_v1 not found in registry"。
    substituteInPlace $out/share/applications/dev.lizardbyte.app.Sunshine.kwin.desktop \
      --replace-fail "$out/bin/sunshine" "$out/bin/.sunshine-wrapped"
  '';

  doInstallCheck = false;

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "魔改版 Sunshine：带自愈式输入法接管桥的游戏串流主机";
    homepage = "https://github.com/jiuhruu-JK/sunshine-linux-chinese-input";
    license = lib.licenses.gpl3Only;
    mainProgram = "sunshine";
    platforms = [ "x86_64-linux" "aarch64-linux" ];
  };
})
