# Linux Sunshine 中文输入方案

给 Linux 版 Sunshine 补上中文远程输入：手机 Moonlight 打中文，原版乱码丢字，这套不乱。

方案 = **魔改版 Sunshine + fcitx5 插件**，不只是插件——Sunshine 本体也改了，两个都要装。

**仅限 Linux（fcitx5）。Windows/macOS 用不了。**

## 方案（两个东西，都要装）

```
sunshine-linux-chinese-input
├── sunshine/          魔改版 Sunshine   ← 文本改走输入法通道，不再走会乱码的 Ctrl+Shift+U
└── fcitx5-plugin/     fcitx5 插件       ← 接收整段文本，从输入法标准接口一次上屏
```

## 原理

```
手机 Moonlight 打字 → 魔改版 Sunshine → 本机套接字 → fcitx5 插件 → 当前窗口上屏
```

不模拟键盘、不碰剪贴板。整段 UTF-8 一次提交，2210 字实测零丢失。

**不占用剪贴板**：剪贴板粘贴类方案会覆盖你复制的内容；本方案完全不动剪贴板，
远程输入的同时，剪贴板照常用。

## 版本

- 基于 [LizardByte/Sunshine](https://github.com/LizardByte/Sunshine)
  **v2026.1011.160319**（commit `d1fc311`，2026-10-11）。
- 本仓库只配套这个版本，不跟上游更新。
- 原版在 Windows/macOS 的中文输入一直正常，需要修的只是 Linux 远程中文输入；
  上游若在 Linux 补上了，直接用上游即可。

## 怎么用

只在 Ubuntu 26.04 + KDE(Wayland) 验证过，别的机器能不能用不知道。

**1. 装魔改版 Sunshine**

```bash
git clone https://github.com/jiuhruu-JK/sunshine-linux-chinese-input.git
cd sunshine-linux-chinese-input/sunshine
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release && make -j$(nproc)
sudo install -m755 sunshine /usr/local/bin/
sudo cp -r assets /usr/local/          # Web UI 资源；漏了这步登录后白屏
```

**2. 装 fcitx5 插件**

```bash
cd ../../fcitx5-plugin
mkdir build && cd build
cmake .. && make
sudo install -m755 libsunshineinput.so /usr/lib/x86_64-linux-gnu/fcitx5/
sudo install -m644 ../sunshineinput.conf /usr/share/fcitx5/addon/
```

**3. 用**

重启 fcitx5，焦点放到任意文本框，尽情输入文字就行。
随便输、大量输——原版方案是输多了才乱码丢字，本方案不会。

## 许可

GPL-3.0（继承上游 LizardByte/Sunshine）。
