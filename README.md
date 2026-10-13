# sunshine-input-method

魔改版 Sunshine + fcitx5 输入法插件 —— 解决 Moonlight 远程连接 Linux 桌面时，
中文（Unicode）文本注入乱码/丢失的问题。

## ⚠️ 环境声明（务必先读）

**本仓库是「当前环境快照」版本，不是通用发行版。**

只在下列环境验证过可用；**当前是 Linux，只符合当前条件**。
其他机器、发行版、桌面环境、内核、依赖版本 —— **能不能用不知道，未经验证，不承诺适配**。

| 项 | 验证过的值 |
|---|---|
| 系统 | 原生 Linux，Ubuntu 26.04（内核 7.0.0-38-generic） |
| 桌面 | KDE Plasma 6（Wayland 会话），KWin 托管 fcitx5 |
| 输入法框架 | fcitx5 5.1.19 + fcitx5-rime 5.1.13 |
| 客户端 | Moonlight Android（手机真机，局域网直连） |
| 硬件编码 | Vulkan（h264/hevc/av1） |

快照基线：基于 [LizardByte/Sunshine](https://github.com/LizardByte/Sunshine) master
（commit `d1fc311`）的当前工作树整树收录，未保留上游子模块结构，
`third-party/` 按 magicked 当前状态原样收录（其中 `libvirtualhid` 含本项目的
unicode IPC 修改；`TPCircularBuffer` 为空目录 —— macOS/iOS 专用，Linux 构建不需要）。

## 原理

原版 Sunshine 在 Linux 上收到 Moonlight 的 Unicode 文本时，走 `Ctrl+Shift+U`
hex 合成路径，中文会乱码/丢失。

本方案改为：文本 → 输入法框架的标准文字提交接口，整段一次上屏：

```
手机 Moonlight（软键盘文本输入）
  → 魔改版 Sunshine（patches/0002：unicode IPC divert）
  → Unix 域套接字  $XDG_RUNTIME_DIR/sunshine-input/sunshine-input.sock
  → fcitx5 插件 sunshineinput（addon，监听套接字，运行在 fcitx5 事件循环中）
  → InputContext::commitString（整段 UTF-8 文本）
  → 当前聚焦应用上屏
```

设计要点：

- 走 fcitx5 公开 API `commitString`；**不**模拟逐字符键盘事件、**不**用剪贴板粘贴
- 无聚焦输入上下文时明确拒绝（回 `E`），绝不把文本发给旧焦点窗口
- 严格 UTF-8 校验、1 MiB 消息上限、空文本拒绝
- 套接字安全：`0700` 目录 + `0600` 文件，仅同 UID 可连；支持 `SUNSHINE_INPUT_SOCKET` 覆盖路径
- fcitx5 重启竞争防护：bind 前探测活跃监听者（有界等待接管），析构按 inode 认领只删自己的 socket
- 实测：2210 字中英混合文本一次 `commitString`，回读**逐字节一致**（零丢失零乱码）

## 组成

```
/                     魔改版 Sunshine（含 patches/0001 显示电源管理，已应用在工作树）
patches/0001-*.patch  显示电源管理：客户端串流期间保持显示器唤醒（相对上游 Sunshine）
patches/0002-*.patch  unicode IPC divert（相对 third-party/libvirtualhid 子模块）
plugin/sunshineinput/ fcitx5 原生插件 + sunshine-input-test 测试客户端
tools/                原版 Ctrl+Shift+U 中文乱码复现脚本
docs/UPSTREAM-README.md   上游原始 README
docs/KNOWN-ISSUES.md      已知限制 / 第二版待修清单
```

## 构建（当前环境实测流程）

依赖参考 [docs/building.md](docs/building.md)（Ubuntu 依赖清单见 `packaging/linux/`）；
Web UI 构建需要 Node.js/npm（cmake 会自动拉取 npm 依赖）。

### 1. Sunshine（魔改版）

```bash
git clone https://github.com/jiuhruu-JK/sunshine-input-method.git
cd sunshine-input-method
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
sudo install -m755 sunshine /usr/local/bin/
```

### 2. fcitx5 插件

```bash
cd plugin/sunshineinput
mkdir build && cd build
cmake .. && make
sudo install -m755 libsunshineinput.so /usr/lib/x86_64-linux-gnu/fcitx5/
sudo install -m644 ../sunshineinput.conf /usr/share/fcitx5/addon/
sudo install -m755 sunshine-input-test /usr/local/bin/
# 重启 fcitx5 后，日志出现 "sunshine-input listening on ..." 即加载成功
```

Wayland 原生应用（Electron/Chromium 等）需要桌面合成器托管输入法：
Plasma 6 为 系统设置 → 键盘 → 虚拟键盘 → 选 Fcitx 5（KWin 会自己拉起 fcitx5）。

### 3. 验证

```bash
# 先把焦点放到任意文本编辑器（Kate 等）的文本区，再执行：
sunshine-input-test --text "测试注入hello2026"
# 输出 OK: request accepted and committed 即链路通；
# 在目标应用中目验文本逐字一致
```

## 许可

继承上游 [GPL-3.0](LICENSE)。基于 LizardByte/Sunshine、libvirtualhid、fcitx5，
感谢上游项目。本仓库的修改部分同样以 GPL-3.0 发布。
