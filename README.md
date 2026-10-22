# Linux Sunshine 中文输入方案

Linux 版 Sunshine 远程输入中文会乱码丢字。这套方案修好它。

仅限 Linux（fcitx5）。Windows/macOS 用不了。

## 装什么

两个东西，同时装：

```
sunshine-linux-chinese-input/     ← 标准 fork 布局：上游源码树就在仓库根目录
├── src/             魔改版 Sunshine 源码   ← 文本改走输入法通道，不再走会乱码的 Ctrl+Shift+U
├── fcitx5-plugin/   fcitx5 原生扩展        ← 接收整段文本，从输入法标准接口一次上屏
├── nix/             Nix 打包定义
└── ci/              边界门禁与上游同步脚本
```

## 原理

```
手机 Moonlight 打字 → Sunshine → 本机 Unix 套接字 → fcitx5 扩展 → 当前输入上下文上屏
```

不模拟键盘，不碰剪贴板，整段 UTF-8 一次上屏。

关键改动只有一处，在 `src/platform/` 里：

| 文件 | 作用 |
|---|---|
| `src/platform/linux/input_method.{h,cpp}` | 套接字客户端：把整段 UTF-8 文本发给 fcitx5 扩展 |
| `src/platform/virtualhid_input.cpp` | `platf::unicode()` 优先走上面的通道；没有扩展时保持上游行为 |

上游把远程文本走成 `Ctrl+Shift+U` 十六进制合成，接收方应用会把它当成快捷键，
于是变成乱码。改完之后文本直接交给输入法，由输入法用 `InputContext::commitString()`
提交到当前焦点。

## 桌面侧不用改

文本桥完全在输入法进程内部完成（远程文本 → 套接字 → fcitx5 扩展 →
`commitString` → 当前焦点窗口），与 KWin 的虚拟键盘开关无关。

本方案**不会**去动输入法进程：既不杀 fcitx5，也不改 KWin 的 VirtualKeyboard
开关。桌面会话的输入法归桌面会话管，是使用方自己的选择。

## 版本

- 基于 [LizardByte/Sunshine](https://github.com/LizardByte/Sunshine)
  的 `v2026.1018.5342`（commit `3d6e1d6`），版本号记在 [`upstream-version`](upstream-version)
- 上游的子模块按上游指定提交**原样收录**进仓库（不保留 git submodule 结构），
  克隆下来就能直接构建；收录清单见 `ci/vendored-submodules.txt`
- 每日同步上游最新 tag：子模块自动重新收录，源码差异必须通过边界门禁

## 边界：只改文本输入

相对上游，本仓库只允许有下面这些差异：

```
src/platform/linux/input_method.h
src/platform/linux/input_method.cpp
src/platform/virtualhid_input.cpp
src/process.cpp
src/stream.cpp
cmake/compile_definitions/linux.cmake
tests/unit/platform/linux/test_input_method.cpp
```

`ci/check-boundary.sh <上游 ref>` 是门禁：白名单之外的文件一旦与上游不同就报错；
白名单里的挂钩文件只允许**新增行**，不允许删改上游已有代码；
收录的第三方依赖里也不许藏本仓库的实现。

打包层（`nix/`）同样有边界：只做「Nix 沙箱里编得过」必需的脚手架修补
（npm、boost、systemd/udev 路径、Qt wrapper、FHS 路径），
不改抓屏方式、编码器、权限模型、输入设备、托盘、桌面图标、启动器语义。

详见 [`docs/sunshine-cn-input-ARCHITECTURE.md`](docs/sunshine-cn-input-ARCHITECTURE.md)。

## 怎么用

### Nix（推荐）

```nix
{
  inputs.sunshine-cn-input.url = "github:jiuhruu-JK/sunshine-linux-chinese-input";

  outputs = { nixpkgs, sunshine-cn-input, ... }: {
    nixosConfigurations.myhost = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        {
          nixpkgs.overlays = [ sunshine-cn-input.overlays.default ];
          # ...
        }
      ];
    };
  };
}
```

包：

- `sunshine-cn-input` —— Sunshine 主体
- `fcitx5-sunshine-input` —— fcitx5 扩展，加进 `i18n.inputMethod.fcitx5.addons`
- `sunshine-cn-input-tests` —— 单元测试变体（跑文本输入桥的用例）

### 源码构建

```bash
git clone https://github.com/jiuhruu-JK/sunshine-linux-chinese-input.git
cd sunshine-linux-chinese-input
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j$(nproc)
```

单元测试：

```bash
cmake -B build -DBUILD_TESTS=ON
cmake --build build -j$(nproc)
./build/tests/test_sunshine --gtest_filter='InputMethod*'
```

fcitx5 扩展单独构建：

```bash
cmake -B build-plugin -S fcitx5-plugin
cmake --build build-plugin -j$(nproc)
```

装好扩展后重启 fcitx5，焦点放到任意文本框即可。

## 许可

GPL-3.0（继承上游 LizardByte/Sunshine）。
