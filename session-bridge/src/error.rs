//! 本 crate 的错误类型。
//!
//! 范式：`thiserror` 定义枚举，调用方 `?` 传播；
//! `unwrap` / `expect` / `panic!` 只许出现在测试里。

use std::path::PathBuf;

/// 桥接器全部错误。
#[derive(Debug, thiserror::Error)]
pub enum Error {
    /// DBus 通信失败（连接 KWin / 读写属性）。
    #[error("dbus: {0}")]
    Dbus(#[from] zbus::Error),

    /// DBus 方法调用被对端拒绝（fdo 层，如属性不存在）。
    #[error("dbus fdo: {0}")]
    Fdo(#[from] zbus::fdo::Error),

    /// 状态文件读写失败。
    #[error("io ({path}): {source}")]
    Io {
        path: PathBuf,
        #[source]
        source: std::io::Error,
    },

    /// 状态文件内容非法（无法解析为已记录的接管状态）。
    #[error("corrupt state file: {0}")]
    CorruptState(PathBuf),
}

/// 便捷别名。
pub type Result<T> = std::result::Result<T, Error>;
