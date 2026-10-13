# 已知限制 / 第二版待修清单

> 第二版开发以此为起点。顺序不代表优先级。

1. **跨机适配未验证**：本仓库仅在作者当前环境（Ubuntu 26.04 + KDE Plasma 6 Wayland +
   fcitx5 5.1.19）验证。其他发行版/桌面/版本未测；安装路径（`/usr/lib/x86_64-linux-gnu/fcitx5/`）
   在其他架构/发行版可能不同。
2. **Wayland 原生 Electron/Chromium 应用的输入法依赖合成器托管**：Plasma 6 需在
   系统设置 → 键盘 → 虚拟键盘 选 Fcitx 5（KWin 托管）。部分 Chromium 版本可能还需要
   启动参数 `--enable-wayland-ime`，未逐一验证。
3. **X11/XWayland 应用路径未系统验证**：XWayland 应用理论上经 XIM（`XMODIFIERS=@im=fcitx`）
   走 fcitx5，未做长文字节级验证。
4. **安装覆盖不完整**：cmake install 不包含 Web UI assets 到 `/usr/local/assets/`，
   需手动复制（`build/assets/` → `/usr/local/assets/`），否则 Web UI 图标缺失（不影响功能）。
5. **插件无热重载**：更换 `libsunshineinput.so` 后需重启 fcitx5 生效。
6. **单用户模型**：套接字 `0600` 仅同 UID 可连；sunshine 以其他用户运行时需用
   `SUNSHINE_INPUT_SOCKET` 指到可访问路径并自行评估安全边界。
7. **无打包产物**：未提供 deb/AppImage/CI 打包，纯手动编译安装。
8. **注入语义是「提交文本」不是「键入」**：文本直接经 `commitString` 上屏，不经过
   Rime 等输入法引擎处理；本地方打字（Rime）与远程注入是两条并行路径。
9. **多显示器/焦点语义**：提交目标是 `mostRecentInputContext()` 且要求持焦；
   焦点落在无文本输入能力的窗口时请求被拒绝（设计行为，但提示仅走日志）。
10. **上游同步**：快照基于上游 master `d1fc311`，后续上游改动需手动 rebase。
