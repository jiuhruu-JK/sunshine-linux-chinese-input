//! fcitx5 进程探测与处置。
//!
//! 健康判据：fcitx5 进程存在，且其父进程是 kwin_wayland
//! （KWin 托管实例才持有 Wayland 输入法角色；--replace 重启的
//! 实例拿不到角色，Wayland 原生应用因此失联——2026-10-14 实测踩坑）。

use std::path::Path;

/// 本机全部 fcitx5 进程 (pid, ppid, cmdline)。
pub fn processes() -> Vec<(u32, u32, String)> {
    let mut found = Vec::new();
    let entries = match std::fs::read_dir("/proc") {
        Ok(e) => e,
        Err(_) => return found,
    };
    for entry in entries.flatten() {
        let name = entry.file_name();
        let Some(name) = name.to_str() else { continue };
        let Ok(pid) = name.parse::<u32>() else { continue };
        let base = Path::new("/proc").join(name);
        let (Some(cmdline), Some(ppid)) = (read_cmdline(&base), read_ppid(&base)) else {
            continue;
        };
        if cmdline.split('\0').any(|a| a.ends_with("/fcitx5") || a == "fcitx5") {
            found.push((pid, ppid, cmdline.replace('\0', " ")));
        }
    }
    found
}

/// 健康检查：存在 KWin 托管的 fcitx5 实例。
pub fn kwin_managed_alive() -> bool {
    processes().iter().any(|&(_, ppid, _)| is_kwin_child(ppid))
}

/// 终止全部 fcitx5 实例并等待退场（最多 `timeout_ms`）。
pub fn kill_all(timeout_ms: u64) {
    for (pid, _, _) in processes() {
        unsafe { libc::kill(pid as i32, libc::SIGTERM) };
    }
    let deadline = std::time::Instant::now() + std::time::Duration::from_millis(timeout_ms);
    while std::time::Instant::now() < deadline {
        if processes().is_empty() {
            return;
        }
        std::thread::sleep(std::time::Duration::from_millis(100));
    }
}

/// 等待 socket 文件出现（扩展绑定成功的信号），最多 `timeout_ms`。
pub fn wait_socket(path: &Path, timeout_ms: u64) -> bool {
    let deadline = std::time::Instant::now() + std::time::Duration::from_millis(timeout_ms);
    while std::time::Instant::now() < deadline {
        if path.exists() {
            return true;
        }
        std::thread::sleep(std::time::Duration::from_millis(100));
    }
    path.exists()
}

fn is_kwin_child(ppid: u32) -> bool {
    let stat = Path::new("/proc").join(ppid.to_string()).join("cmdline");
    std::fs::read_to_string(stat)
        .map(|c| c.contains("kwin_wayland"))
        .unwrap_or(false)
}

fn read_cmdline(base: &Path) -> Option<String> {
    std::fs::read_to_string(base.join("cmdline")).ok()
}

fn read_ppid(base: &Path) -> Option<u32> {
    let stat = std::fs::read_to_string(base.join("stat")).ok()?;
    let after = stat.rsplit(')').next()?;
    let fields: Vec<&str> = after.split_whitespace().collect();
    fields.get(1)?.parse().ok()
}
