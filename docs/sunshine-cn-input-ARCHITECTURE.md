# 中文输入桥 —— 架构

> 本文是 `sunshine-linux-chinese-input` 的架构说明，也是边界门禁的依据。
> 改动与本文冲突时，先改本文，再改代码。

## 1. 问题

Moonlight 客户端把远程文字作为 UTF-8 文本发给主机。Sunshine 收到后走
`platf::unicode()` → libvirtualhid 的 `type_text()` → Linux 下合成 `Ctrl+Shift+U`
+ 十六进制码点 + 回车。

接收方应用（浏览器、编辑器、聊天工具）通常把 `Ctrl+Shift+U` 当成自己的快捷键，
于是这段文本变成乱码、丢字，或者干脆被吞掉。

Windows 版 Sunshine 没有这个问题：它走 `SendInput` 的 Unicode 事件，
接收方按正常文字处理。**要修的只是 Linux 这一条路径。**

## 2. 方案

```
手机 Moonlight 打字
   → Sunshine 收到 UTF-8 文本（NV_UNICODE_PACKET）
   → platf::unicode()
   → input_method::submit_text()      ← 本仓库的改动
   → Unix 域套接字（4 字节大端长度前缀 + UTF-8 正文）
   → fcitx5 扩展（fcitx5-plugin/）
   → InputContext::commitString()     ← 输入法公开 API
   → 当前焦点窗口
```

要点：

- 整段 UTF-8 一次提交，不逐字符模拟键盘；
- 不碰剪贴板；
- 扩展在 fcitx5 自己的事件循环里执行，提交前校验焦点，
  没有有效焦点就明确拒绝，绝不把文本发给旧焦点窗口；
- 套接字文件 0600、目录 0700，只有当前用户能连。

## 3. 为什么走输入法而不是自己合成

社区已经验证过的做法是：让系统输入法按输入法协议接管文字输入，
应用收到的是标准文字事件，而不是键盘快捷键。自己再合成一遍按键，
既要处理各应用的快捷键冲突，又躲不开 IME 候选窗与焦点切换的时序问题。

所以本方案只做一件事：**把文本交给输入法**，其余一概不碰。

## 4. 改动范围

### 4.1 仓库布局

标准 fork 布局：上游源码树就在仓库根目录。

```
src/                上游 Sunshine 源码（唯一有改动的地方）
fcitx5-plugin/      fcitx5 原生扩展（本仓库新增）
nix/                Nix 打包定义（本仓库新增）
ci/                 边界门禁与上游同步脚本（本仓库新增）
third-party/        上游子模块，按上游指定提交原样收录
```

### 4.2 白名单：唯一允许与上游不同的文件

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

`src/platform/virtualhid_input.cpp` 是后补进白名单的：文本注入的唯一入口在
`platf::unicode()`，不改它就接不上输入法通道。允许的改动只有一处 ——
在函数体最前面加一段「优先交给输入法扩展，没有扩展才走原来的虚拟键盘」。

### 4.3 挂钩文件只准新增行

`src/process.cpp`、`src/stream.cpp`、`src/platform/virtualhid_input.cpp`、
`cmake/compile_definitions/linux.cmake` 里的改动必须是**新增**的 `#ifdef __linux__` 块，
不允许修改、删除、重排任何已有代码。评审只看 diff：只应有 `+`，不应有 `-`。

### 4.4 收录的第三方依赖

上游的子模块按上游指定提交**原样收录**进仓库（目录形态，不是 git submodule），
克隆下来就能直接构建，不需要 `git submodule update --init --recursive`。

- 收录清单：`ci/vendored-submodules.txt`（每行 `<提交> <路径>`）
- 核对：`ci/vendor-submodules.sh check <上游 ref>`
- 重新收录：`ci/vendor-submodules.sh apply <上游 ref>`
- 有意不收录的：`third-party/build-deps`（只用它的 `package-lock.cmake`，
  打包时单独取）、`third-party/ViGEmClient`（只有 Windows 端用）、
  `third-party/TPCircularBuffer`（收录版 moonlight-common-c 不引用它）

**收录目录里不许藏本仓库的实现。** 边界门禁会显式检查这一点：
一旦文本输入的实现被塞进 `third-party/`，它对门禁就不可见，
上游升级该子模块时还会被静默覆盖。

## 5. 打包层的边界

`nix/` 只描述「怎么编译」，不许借打包之名改行为。

允许：npm 单独构建并搬产物、boost 走 nixpkgs 的包、systemd/udev 安装路径、
Qt wrapper、FHS 路径修正（`/bin/sleep`、`/usr/bin/env systemctl`）。

不许：

- 改抓屏方式、编码器、权限模型、输入设备、托盘、桌面图标、启动器语义；
- `substituteInPlace` 改源码逻辑（只允许改路径）；
- `postInstall` 改桌面文件。

## 6. 上游同步

```
每日 CI → 拉上游最新 tag
        → 按上游指定提交重新收录被升级的子模块
        → git merge
        → 冲突处理：
             .github/workflows/  保持删除（上游 CI 与本仓库无关）
             third-party/ 等      保留重新收录后的内容
             其它（白名单文件）   流水线失败，交人工合并
        → 边界门禁
        → 通过才提交推送
```

门禁命令：`ci/check-boundary.sh <上游 ref>`。

## 7. 不做的事

- 不杀 fcitx5，不重启输入法；
- 不改 KWin 的 VirtualKeyboard 开关；
- 不动 KDE 的「虚拟键盘 = 无」这一项 —— 那是桌面会话自己的事，
  本仓库不越界去改用户的桌面配置；
- 不改抓屏、编码、权限、音频、网络、WebUI、配置项默认值；
- 不在本机编译（本机零编译，只在云端 CI 编）。

## 8. 验收

见 [`sunshine-cn-input-IMPLEMENTATION.md`](sunshine-cn-input-IMPLEMENTATION.md)。
