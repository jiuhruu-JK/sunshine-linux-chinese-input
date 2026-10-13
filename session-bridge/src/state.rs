//! 接管状态文件：记录「接管前」KWin 虚拟键盘开关的原始值。
//!
//! 位置 `$XDG_STATE_HOME/sunshine-ime-bridge/state`（缺省 `~/.local/state/...`）。
//! 文件存在 = 当前处于接管期；内容为接管前的开关值（`enabled=true|false`）。
//! connect 写入、disconnect 读取后清除；断电残留的旧文件由下一次
//! disconnect 消费，幂等不叠加。

use std::fs;
use std::path::{Path, PathBuf};

use crate::error::{Error, Result};

/// 状态文件路径：`$XDG_STATE_HOME/sunshine-ime-bridge/state`。
///
/// 环境变量缺失时按 XDG 规范回退 `~/.local/state`。
pub fn state_path() -> PathBuf {
    let base = std::env::var_os("XDG_STATE_HOME")
        .map(PathBuf::from)
        .filter(|p| p.is_absolute())
        .or_else(|| home_dir().map(|h| h.join(".local").join("state")))
        .unwrap_or_else(|| PathBuf::from("/tmp"));
    base.join("sunshine-ime-bridge").join("state")
}

fn home_dir() -> Option<PathBuf> {
    std::env::var_os("HOME").map(PathBuf::from)
}

/// 读取接管期前的原始开关值；文件不存在 = 当前未接管。
pub fn load(path: &Path) -> Result<Option<bool>> {
    match fs::read_to_string(path) {
        Ok(content) => parse_state(path, &content).map(Some),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(e) => Err(Error::Io { path: path.to_path_buf(), source: e }),
    }
}

/// 写入接管期前的原始开关值；connect 时调用，幂等（覆盖同值）。
pub fn save(path: &Path, original: bool) -> Result<()> {
    if let Some(dir) = path.parent() {
        fs::create_dir_all(dir)
            .map_err(|e| Error::Io { path: dir.to_path_buf(), source: e })?;
    }
    let line = format_state(original);
    fs::write(path, line).map_err(|e| Error::Io { path: path.to_path_buf(), source: e })
}

/// 清除接管状态；disconnect 消费后调用，文件不存在亦视为成功。
pub fn clear(path: &Path) -> Result<()> {
    match fs::remove_file(path) {
        Ok(()) => Ok(()),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(()),
        Err(e) => Err(Error::Io { path: path.to_path_buf(), source: e }),
    }
}

fn format_state(original: bool) -> String {
    format!("enabled={original}\n")
}

fn parse_state(path: &Path, content: &str) -> Result<bool> {
    let line = content.trim();
    match line.strip_prefix("enabled=") {
        Some("true") => Ok(true),
        Some("false") => Ok(false),
        _ => Err(Error::CorruptState(path.to_path_buf())),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn temp_path(tag: &str) -> PathBuf {
        let mut p = std::env::temp_dir();
        p.push(format!(
            "sib-test-{tag}-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.subsec_nanos())
                .unwrap_or(0)
        ));
        p
    }

    #[test]
    fn missing_file_means_not_taking_over() {
        let p = temp_path("missing");
        assert_eq!(load(&p).unwrap(), None);
    }

    #[test]
    fn save_then_load_roundtrip() {
        for original in [true, false] {
            let p = temp_path("roundtrip");
            save(&p, original).unwrap();
            assert_eq!(load(&p).unwrap(), Some(original));
            clear(&p).unwrap();
            assert_eq!(load(&p).unwrap(), None);
        }
    }

    #[test]
    fn clear_without_file_is_ok() {
        let p = temp_path("clear-missing");
        clear(&p).unwrap();
    }

    #[test]
    fn corrupt_content_is_reported() {
        let p = temp_path("corrupt");
        std::fs::write(&p, "garbage").unwrap();
        assert!(matches!(load(&p), Err(Error::CorruptState(_))));
        clear(&p).unwrap();
    }

    #[test]
    fn save_is_idempotent() {
        let p = temp_path("idempotent");
        save(&p, false).unwrap();
        save(&p, false).unwrap();
        assert_eq!(load(&p).unwrap(), Some(false));
        clear(&p).unwrap();
    }
}
