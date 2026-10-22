# 中文输入桥 —— 实现说明与验收

> 配合 [`sunshine-cn-input-ARCHITECTURE.md`](sunshine-cn-input-ARCHITECTURE.md) 使用。
> 本文记录实现细节、已知坑与验收步骤。

## 1. 协议

套接字：`$XDG_RUNTIME_DIR/sunshine-input/sunshine-input.sock`；
`XDG_RUNTIME_DIR` 没设时回退到 `/tmp/sunshine-input-<uid>/sunshine-input.sock`。

帧格式：**4 字节大端长度前缀 + UTF-8 正文**。
回执：**1 字节**，`K` = 已提交，`E` = 拒绝。

扩展（`fcitx5-plugin/src/sunshineinput.cpp`）侧的校验：

- 拒绝空文本；
- 严格校验 UTF-8（拒绝非法字节序列、过长编码、代理区、越界码点）；
- 限制单条消息 1 MiB；
- 提交前确认 `InputContext::mostRecentInputContext()` 存在且 `hasFocus()`，
  否则回 `E`，**绝不把文本发给旧焦点窗口**；
- 监听套接字 backlog 4，连接数上限 8；
- 扩展重启竞争：bind 前先探测旧实例是否还活着（最多等 25 × 200ms），
  析构时按 inode 认领，只删自己建的那个 socket 文件。

## 2. 主机侧实现

### 2.1 `src/platform/linux/input_method.{h,cpp}`

- `connect()` —— 串流会话开始时调用。**只观察**：探测扩展 socket 在不在，
  记下「有会话在用文本桥」。不启动/停止/重启 fcitx5，
  不写 KWin 的 VirtualKeyboard 开关，不阻塞等待桌面会话。
- `disconnect()` —— 串流会话结束时调用。**只清会话记录**，桌面会话一个字节都没动过，
  所以缺调用或重复调用都无害。
- `submit_text(utf8)` —— 把整段文本发给扩展。
  返回三态：
  - `unavailable`：扩展没装或连不上 → 调用方**保留上游行为**（走虚拟键盘）；
  - `submitted`：扩展已提交；
  - `rejected`：扩展在但拒绝了（比如没有焦点窗口）→ 调用方**不要再回退**，
    回退只会把同样会乱码的字节再注入一遍。

  发送与接收都有 1 秒超时，输入线程不会被卡住。

### 2.2 `src/platform/virtualhid_input.cpp`

`platf::unicode()` 的最前面加一段（Linux 专属，其他平台行为不变）：

```
扩展可用 → 交给扩展，直接返回
扩展不可用 → 走上游 virtualhid::unicode()
```

### 2.3 会话钩子

`src/process.cpp` 在 `proc::proc_run()` 里、`proc::terminate()` 里各调一次
`connect()` / `disconnect()`；`src/stream.cpp` 在最后一个客户端断开时调
`disconnect()`（裸 Desktop 会话走 placebo 路径，不会走到 `proc::terminate()`）。

这两个钩子现在**没有任何副作用**，只是让会话生命周期在日志里可见。

### 2.4 单元测试

`tests/unit/platform/linux/test_input_method.cpp` 用一个桩扩展服务器
（真的 `bind`/`listen`/`accept` 一个 Unix 域套接字）验证：

- 帧格式：4 字节大端长度前缀；
- 回执解析：`K` → submitted，`E`/未知字节 → rejected；
- 扩展接受时文本原样送达；
- 扩展拒绝时返回 rejected；
- 没有扩展时返回 unavailable；
- 套接字路径跟随 `XDG_RUNTIME_DIR`，没有时回退 `/tmp/sunshine-input-<uid>`；
- `connect()` / `disconnect()` 只改会话记录，不创建任何文件。

跑法：

```bash
cmake -B build -DBUILD_TESTS=ON
cmake --build build -j$(nproc)
./build/tests/test_sunshine --gtest_filter='InputMethod*'
```

Nix 侧：`nix build .#sunshine-cn-input-tests`（云端 CI 里跑）。

## 3. 桌面侧不需要改动

文本桥不依赖 KWin 的虚拟键盘开关：

```
远程文本 → Sunshine → 套接字 → fcitx5 扩展 → commitString → 当前焦点窗口
```

这条链路完全在输入法进程内部完成，KWin 的 VirtualKeyboard 开关是什么值都不影响它。
远程键盘那条**不是第二个输入法**：它进的是同一个 fcitx5 进程里的插件，
不新建输入法实例，也就不存在两个输入法抢同一条 text-input 链路的问题。

### KDE Plasma 6 上的社区标准做法

KDE Plasma 6 Wayland 要求输入法进程**由 KWin 拉起**，因此社区的标准做法是把
「虚拟键盘」设成 Fcitx 5，而不是「无」：

- ArchWiki《Fcitx5》：
  「**KDE Plasma**: Plasma on Wayland requires the input method process to be
  invoked by KWin. To achieve that, quit any running Fcitx 5 process, head to
  **System Settings > Input & Output > Keyboard > Virtual Keyboard, then select
  Fcitx 5**.」
- Fcitx 官方 wiki《Setup Fcitx 5》：
  「Simply open systemsettings, go to the "Virtual Keyboard" section, change the
  input method from "None" to **"Fcitx 5"**.」

如果把虚拟键盘设成「无」，KWin 就不再拉起 fcitx5；独立启动的 fcitx5 必须自己
拿到 `WAYLAND_DISPLAY` / `WAYLAND_SOCKET` 才能连上合成器，否则拿不到 IM 角色，
原生 Wayland 应用会没有输入上下文（浏览器打不出中文）。

所以：

- 本方案**不去碰**这一项：既不杀 fcitx5，也不改 KWin 的 VirtualKeyboard 开关；
- 桌面会话的输入法归桌面会话管，是使用方自己的选择；
- 需要调整时，由使用方在自己的桌面配置里改，不要塞进 Sunshine 或打包层。

> 历史教训：早先的实现会在会话开始时 `kill_all()` 掉所有 fcitx5 实例，
> 再把 KWin 的 VirtualKeyboard 开关 `false → true` 翻一遍。
> 这会打断用户正在用的输入法，删掉。

## 4. 已知坑

- **扩展没跑就静默回退。** 没装扩展（或 fcitx5 没起）时，文本仍走
  `Ctrl+Shift+U`，表现与改动前一致。要确认扩展状态，看 Sunshine 日志里的
  `input method: ...` 那几行。
- **扩展在但没有焦点窗口时文本会被拒绝。** 这是有意的：宁可不打字，
  也不把文本塞进上一个焦点窗口。
- **fcitx5 重启期间文本会丢。** 扩展退场到重启完成之间，连接会失败，
  该条文本按 `unavailable` 处理。

## 5. 验收

### 5.1 扩展装上了吗

```bash
ls -la $XDG_RUNTIME_DIR/sunshine-input/
# 目录 0700，sunshine-input.sock 0600
```

### 5.2 扩展能提交文本吗

```python
import os, socket, struct
p = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "sunshine-input/sunshine-input.sock")
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect(p)
data = "中文测试".encode()
s.sendall(struct.pack(">I", len(data)) + data)
print(s.recv(1))   # b'K' 成功，b'E' 拒绝（没有焦点窗口）
s.close()
```

### 5.3 端到端

1. 手机 Moonlight 连上主机；
2. 手机端调出键盘，输入中文；
3. 主机上的文本框里应当一次出现整段中文，没有乱码、没有丢字；
4. Sunshine 日志里应能看到 `input method: text committed by the fcitx5 extension`。

### 5.4 没有扩展时的行为

把扩展卸掉（或停掉 fcitx5），重复 5.3：文本退回上游的 `Ctrl+Shift+U` 路径，
表现与改动前一致 —— 即老问题，不应有新的崩溃或卡顿。
