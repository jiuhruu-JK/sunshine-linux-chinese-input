//! 输入法主动权随串流会话切换（自愈式）。
//!
//! **保证**：每次 `connect`（串流开始）都把链路收敛到已知健康态——
//! KWin 托管的 fcitx5 + 扩展 socket 在位——无论之前 fcitx5 是被
//! 托盘重启、`--replace`、崩溃还是其他方式破坏的。串流开始即重建，
//! 不依赖现场恰好健康。
//!
//! - `connect`（Sunshine `global_prep_cmd` 的 `do`）：
//!   记录原始开关 → 重建健康链路 → 置为接管。
//! - `disconnect`（`undo`）：还原原始开关，主动权交还。
//! - `status`：报告链路健康与接管状态。
//!
//! 健康链路三要素：KWin 托管的 fcitx5 进程、扩展 socket 文件、
//! 托管开关 enabled=true。重建动作有界（秒级），发生在串流开始的
//! 冷启动窗口，代价可接受。

pub mod error;
pub mod kwin;
pub mod process;
pub mod state;

use error::Result;

/// 健康链路的 socket 路径（与 fcitx5 扩展约定一致）。
pub fn socket_path() -> std::path::PathBuf {
    let runtime = std::env::var_os("XDG_RUNTIME_DIR").map(std::path::PathBuf::from);
    match runtime {
        Some(dir) => dir.join("sunshine-input").join("sunshine-input.sock"),
        None => std::path::PathBuf::from(format!(
            "/tmp/sunshine-input-{}/sunshine-input.sock",
            unsafe { libc::getuid() }
        )),
    }
}

/// 串流开始：重建健康链路并接管。
///
/// 顺序有讲究：先记原始开关（还原依据），再无条件重建
/// （杀尽 fcitx5 → KWin 开关 false→true 强制重托管 → 等 socket），
/// 最后确保接管态。
pub fn connect(conn: &zbus::blocking::Connection, path: &std::path::Path) -> Result<Action> {
    let original = kwin::enabled(conn)?;
    rebuild_chain(conn)?;
    kwin::set_enabled(conn, true)?;
    let socket_ok = process::wait_socket(&socket_path(), 10_000);
    state::save(path, original)?;
    Ok(Action::TookOver { original, socket_ok })
}

/// 串流结束：交还主动权。
pub fn disconnect(conn: &zbus::blocking::Connection, path: &std::path::Path) -> Result<Action> {
    match state::load(path)? {
        Some(original) => {
            kwin::set_enabled(conn, original)?;
            state::clear(path)?;
            Ok(Action::Restored { original })
        }
        None => Ok(Action::Idle),
    }
}

/// 链路健康自检：托管实例存活 + socket 在位 + 开关为开。
pub fn health(conn: &zbus::blocking::Connection) -> Result<Health> {
    Ok(Health {
        kwin_enabled: kwin::enabled(conn)?,
        managed_alive: process::kwin_managed_alive(),
        socket_present: socket_path().exists(),
    })
}

/// 重建健康链路：杀尽 fcitx5 → KWin 开关 false→true 强制重托管。
///
/// 供 connect 内部与 CLI 的 `repair` 子命令使用。
pub fn rebuild_chain(conn: &zbus::blocking::Connection) -> Result<()> {
    process::kill_all(5_000);
    kwin::set_enabled(conn, false)?;
    kwin::set_enabled(conn, true)?;
    Ok(())
}

/// 健康状态快照。
#[derive(Debug, PartialEq, Eq)]
pub struct Health {
    /// KWin 托管开关。
    pub kwin_enabled: bool,
    /// 存在 KWin 托管的 fcitx5 实例。
    pub managed_alive: bool,
    /// 扩展 socket 在位。
    pub socket_present: bool,
}

impl Health {
    /// 全部要素齐备 = 健康。
    pub fn is_healthy(&self) -> bool {
        self.kwin_enabled && self.managed_alive && self.socket_present
    }

    /// 人类可读的一行描述。
    pub fn describe(&self) -> String {
        format!(
            "kwin_enabled={} managed_fcitx5={} socket={} healthy={}",
            self.kwin_enabled,
            self.managed_alive,
            self.socket_present,
            self.is_healthy()
        )
    }
}

/// 一次调用的结果，供 CLI 报告。
#[derive(Debug, PartialEq, Eq)]
pub enum Action {
    /// connect：接管完成；`original` 为接管前开关；`socket_ok` 为重建结果。
    TookOver { original: bool, socket_ok: bool },
    /// disconnect：已还原；`original` 为还原到的开关值。
    Restored { original: bool },
    /// disconnect：本无接管状态，空操作。
    Idle,
}

impl Action {
    /// 人类可读的一行描述。
    pub fn describe(&self) -> String {
        match self {
            Action::TookOver { original, socket_ok } => format!(
                "takeover: enabled=true (was {original}) socket_ok={socket_ok}"
            ),
            Action::Restored { original } => format!("restore: enabled={original}"),
            Action::Idle => "restore: no takeover in progress, no-op".to_string(),
        }
    }
}
