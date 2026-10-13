//! CLI 入口：`sunshine-ime-bridge <connect|disconnect|status|repair>`。
//!
//! 供 Sunshine `global_prep_cmd` 挂载：`do` → connect，`undo` → disconnect。
//! connect 自带链路重建（自愈）；repair 供人工在会话中途修复。

use std::process::ExitCode;

use sunshine_ime_bridge::{connect, disconnect, health, kwin, rebuild_chain, state, socket_path};

fn main() -> ExitCode {
    let sub = match std::env::args().nth(1).as_deref() {
        Some("connect") => Sub::Connect,
        Some("disconnect") => Sub::Disconnect,
        Some("status") => Sub::Status,
        Some("repair") => Sub::Repair,
        Some(other) => {
            eprintln!("unknown subcommand: {other}");
            eprintln!("usage: sunshine-ime-bridge <connect|disconnect|status|repair>");
            return ExitCode::from(2);
        }
        None => {
            eprintln!("usage: sunshine-ime-bridge <connect|disconnect|status|repair>");
            return ExitCode::from(2);
        }
    };
    match run(sub) {
        Ok(report) => {
            println!("{report}");
            ExitCode::SUCCESS
        }
        Err(e) => {
            eprintln!("error: {e}");
            ExitCode::FAILURE
        }
    }
}

enum Sub {
    Connect,
    Disconnect,
    Status,
    Repair,
}

fn run(sub: Sub) -> Result<String, sunshine_ime_bridge::error::Error> {
    let conn = kwin::connect()?;
    let path = state::state_path();
    match sub {
        Sub::Connect => Ok(connect(&conn, &path)?.describe()),
        Sub::Disconnect => Ok(disconnect(&conn, &path)?.describe()),
        Sub::Repair => {
            rebuild_chain(&conn)?;
            let ok = sunshine_ime_bridge::process::wait_socket(&socket_path(), 10_000);
            Ok(format!("repair: socket_ok={ok}"))
        }
        Sub::Status => {
            let h = health(&conn)?;
            let saved = state::load(&path)?;
            Ok(format!("{} takeover={}", h.describe(), saved.is_some()))
        }
    }
}
