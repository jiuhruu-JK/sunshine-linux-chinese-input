# fcitx5-sunshine-input —— Sunshine 中文输入方案的 fcitx5 原生扩展
#
# packaging/ 层：只描述"怎么编译"，源码来自同级目录 ./fcitx5-plugin。
#
# addon 布局遵循 fcitx5 约定：
#   $out/lib/fcitx5/libsunshineinput.so
#   $out/share/fcitx5/addon/sunshineinput.conf
{
  lib,
  stdenv,
  cmake,
  fcitx5,

  src ? ../fcitx5-plugin,
  version ? "dev",
}:

stdenv.mkDerivation (finalAttrs: {
  pname = "fcitx5-sunshine-input";
  inherit version src;

  cmakeBuildDir = "build-plugin";
  cmakeDir = "${finalAttrs.src}";

  nativeBuildInputs = [ cmake ];
  buildInputs = [ fcitx5 ];

  cmakeFlags = [
    (lib.cmakeFeature "CMAKE_BUILD_TYPE" "Release")
  ];

  doInstallCheck = false;

  meta = {
    description = "Sunshine 中文输入方案的 fcitx5 原生扩展";
    homepage = "https://github.com/jiuhruu-JK/sunshine-linux-chinese-input";
    license = lib.licenses.gpl3Only;
    platforms = [ "x86_64-linux" "aarch64-linux" ];
  };
})
