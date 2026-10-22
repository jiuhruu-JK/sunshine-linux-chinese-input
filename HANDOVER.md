# 交接说明

> 记录本仓库当前状态、边界与后续动作。与
> [`docs/sunshine-cn-input-ARCHITECTURE.md`](docs/sunshine-cn-input-ARCHITECTURE.md) 配套阅读。

## 1. 仓库是什么

`jiuhruu-JK/sunshine-linux-chinese-input` 是 LizardByte/Sunshine 的 fork，
唯一的**功能**改动是 Linux 串流时的中文输入：远程文本不再走
`Ctrl+Shift+U` 合成（会被应用当成快捷键，表现为乱码丢字），
而是整段交给 fcitx5 扩展，由输入法用 `InputContext::commitString()` 上屏。

除文本输入外，抓屏、编码、权限、音频、网络、WebUI、配置项默认值等
一律沿用上游。

## 2. 当前状态

| 项 | 状态 |
|---|---|
| 基线 | 上游 `v2026.1018.5342`（commit `3d6e1d6`），祖先关系已接上（CI 里用 `-s ours` 接的） |
| 上游同步 | `.github/workflows/sync-upstream.yml` 每日合并上游最新 tag；子模块自动重新收录 |
| 边界门禁 | `ci/check-boundary.sh`，白名单之外有差异就失败 |
| 云端编译 | `.github/workflows/nix-build.yml` → nix build + 单元测试 + 推 Cachix |
| Nix 包 | `sunshine-cn-input`、`fcitx5-sunshine-input`、`sunshine-cn-input-tests` |
| 收录的第三方 | 按上游指定提交原样收录，清单见 `ci/vendored-submodules.txt` |

上游同步的分工：本机克隆上游是浅克隆，再往前的历史拉不下来，
带着上游祖先的提交推不上远端。所以仓库里只记基线（`upstream-baseline`），
祖先关系由云端 CI 用 `-s ours` 接上，再合并上游最新 tag。

## 3. 相对上游允许的差异

```
src/platform/linux/input_method.h
src/platform/linux/input_method.cpp
src/platform/virtualhid_input.cpp
src/process.cpp
src/stream.cpp
cmake/compile_definitions/linux.cmake
tests/unit/platform/linux/test_input_method.cpp
```

仓库自有内容（不与上游比对）：`README.md`、`flake.nix`、`flake.lock`、
`upstream-version`、`nix/`、`ci/`、`.github/`、`fcitx5-plugin/`、
`docs/UPSTREAM-README.md`、`docs/sunshine-cn-input-*.md`。

## 4. 已经踩过的坑（别再踩）

- **实现不许藏在收录的第三方依赖里。** 早先的文本桥被就地打进了
  `third-party/libvirtualhid` 的 `uhid_backend.cpp`：边界门禁看不见它，
  上游升级该子模块时它还会被覆盖。现在实现统一在
  `src/platform/linux/input_method.*`，门禁还会显式检查收录目录里
  有没有本仓库的实现。
- **不许接管用户的输入法进程。** 早先的实现会 `kill_all()` 掉所有 fcitx5 实例，
  再把 KWin 的 VirtualKeyboard 开关 `false → true` 翻一遍。
  这与社区结论相反（KDE 虚拟键盘应设为「无」，fcitx5 走 `text-input-v3`），
  会打断用户正在用的输入法。现在 `connect()` / `disconnect()` 只做观察。
- **不许用打包层改行为。** 打包层只做 Nix 沙箱必需的脚手架修补
  （npm、boost、systemd/udev 路径、Qt wrapper、FHS 路径）。
- **`callPackage` 会用 `pkgs` 里的同名属性覆盖函数默认值。**
  `src` 必须显式传，否则会拿到 `pkgs.src`（现在是个会抛异常的占位）。
- **`lib.getExe'` 要传 derivation，不是包名。**
- **`cmakeFeature` 只接受字符串**，布尔选项用 `lib.cmakeBool`。

## 5. 待办

1. **云端编译还没跑过。** 这套打包定义是照着 nixpkgs 的 sunshine 包改的，
   但云端 CI 从没成功构建过。第一次跑通前，不要假设它能用。
2. **本机零编译。** 编译只在云端 CI 跑（见仓库根目录的 `AGENTS.md`）。
   本机要验证行为，先 `nix build` 拉云端产物。
3. **桌面侧不用配合任何设置。** 文本桥与 KWin 的虚拟键盘开关无关；
   本方案也不去动 fcitx5 进程与 KWin 的 VirtualKeyboard 开关。
   KDE Plasma 6 Wayland 上，社区标准做法是「虚拟键盘 = Fcitx 5」（由 KWin 拉起
   fcitx5，ArchWiki《Fcitx5》与 Fcitx 官方 wiki《Setup Fcitx 5》都这么写），
   本机走的正是这条。设成「无」的话 KWin 就不拉 fcitx5，独立跑的 fcitx5
   拿不到 Wayland socket，就没有 IM 角色，浏览器会打不出中文。
4. **托盘的 Restart 有坑**：上游 `drop_elevated_privileges` 会把 CAP_PERMITTED
   一并清掉，重初始化之后抓屏权限永久丢失。需要重启时用
   `systemctl --user restart sunshine`。
5. **同步上游后如果白名单文件冲突**，流水线会失败，等人工合并；
   子模块升级由 `ci/vendor-submodules.sh` 自动重新收录。
