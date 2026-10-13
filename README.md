# sunshine-input-method

## 解决什么问题

Linux 版 Sunshine 远程输入中文 → 乱码、丢字。
本仓库解决它。

## 解决方案（两个东西，都要装）

```
sunshine-input-method
├── 魔改版 Sunshine        ← 文本改走输入法通道，不再走会乱码的 Ctrl+Shift+U
└── fcitx5 插件            ← 接收整段文本，从输入法标准接口一次上屏
```

## 原理

```
手机 Moonlight 打字 → 魔改版 Sunshine → 本机套接字 → fcitx5 插件 → 当前窗口上屏
```

不模拟键盘、不碰剪贴板。整段 UTF-8 一次提交，2210 字实测零丢失。

**不占用剪贴板**：剪贴板粘贴类方案会覆盖你复制的内容；本方案完全不动剪贴板，
远程输入的同时，剪贴板照常用。

## 怎么用

仅限 Linux + fcitx5。只在 Ubuntu 26.04 + KDE(Wayland) 验证过，别的机器能不能用不知道。

**1. 装魔改版 Sunshine**

```bash
git clone https://github.com/jiuhruu-JK/sunshine-input-method.git
cd sunshine-input-method
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release && make -j$(nproc)
sudo install -m755 sunshine /usr/local/bin/
sudo cp -r assets /usr/local/          # Web UI 资源；漏了这步登录后白屏
```

**2. 装 fcitx5 插件**

```bash
cd ../plugin/sunshineinput
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
