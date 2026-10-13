//! KWin 虚拟键盘开关（Plasma Wayland 的输入法托管权）。
//!
//! 唯一职责：读写 `org.kde.kwin.VirtualKeyboard` 的 `enabled` 属性。
//! 这是合成器级热切换：不走环境变量，已开应用即时生效（本班实战验证）。
//! 薄封装不测（逻辑在调用方），DBus 细节交给成熟实现 zbus。

use zbus::blocking::Connection;
use zbus::blocking::Proxy;

use crate::error::Result;

const DEST: &str = "org.kde.KWin";
const PATH: &str = "/VirtualKeyboard";
const IFACE: &str = "org.kde.kwin.VirtualKeyboard";
const PROP: &str = "enabled";

fn proxy(conn: &Connection) -> zbus::Result<Proxy<'_>> {
    Proxy::new(conn, DEST, PATH, IFACE)
}

/// 读取当前虚拟键盘（输入法托管）开关。
pub fn enabled(conn: &Connection) -> Result<bool> {
    Ok(proxy(conn)?.get_property(PROP)?)
}

/// 设置虚拟键盘（输入法托管）开关。
pub fn set_enabled(conn: &Connection, value: bool) -> Result<()> {
    Ok(proxy(conn)?.set_property(PROP, value)?)
}

/// 建立会话总线连接；供多次读写复用。
pub fn connect() -> Result<Connection> {
    Ok(Connection::session()?)
}

#[cfg(test)]
mod tests {
    /// 常量与 KWin 官方接口一致，防止重构时漂移。
    #[test]
    fn dbus_coordinates_match_kwin() {
        assert_eq!(super::DEST, "org.kde.KWin");
        assert_eq!(super::PATH, "/VirtualKeyboard");
        assert_eq!(super::IFACE, "org.kde.kwin.VirtualKeyboard");
        assert_eq!(super::PROP, "enabled");
    }
}
