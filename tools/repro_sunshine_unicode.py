#!/usr/bin/env python3
"""repro_sunshine_unicode.py —— 复现原版 Sunshine Linux 的 Unicode 注入路径。

原版行为（上游 Issue #5274 / libvirtualhid uhid_backend.cpp）：
  对每个 Unicode 码点合成键序：Ctrl↓ Shift↓ 'u'↓↑ 4~6位hex逐键 Ctrl↑ Shift↑ Enter↓↑
  本脚本用 uinput 原样合成同一键序，把 U+4E2D（中）打进聚焦应用，
  观察应用实际收到什么（对照新方案的 commitString 路径）。
仅用于 MVP 对比实验，在沙盒虚拟机内运行。
"""
import re
import asyncio
import sys
import time

# Linux 用 evdev uinput；需要 sudo（/dev/uinput 权限）
import evdev
from evdev import UInput, ecodes as e

KEY_MAP = {
    '0': (e.KEY_KP0, None), '1': (e.KEY_1, None), '2': (e.KEY_2, None),
    '3': (e.KEY_3, None), '4': (e.KEY_4, None), '5': (e.KEY_5, None),
    '6': (e.KEY_6, None), '7': (e.KEY_7, None), '8': (e.KEY_8, None),
    '9': (e.KEY_9, None),
    'a': (e.KEY_A, None), 'b': (e.KEY_B, None), 'c': (e.KEY_C, None),
    'd': (e.KEY_D, None), 'e': (e.KEY_E, None), 'f': (e.KEY_F, None),
    'u': (e.KEY_U, None),
    'enter': (e.KEY_ENTER, None),
    'lctrl': (e.KEY_LEFTCTRL, None),
    'lshift': (e.KEY_LEFTSHIFT, None),
}

ui = UInput(name="repro-sunshine-unicode", events={e.EV_KEY: list(set(k for k, _ in KEY_MAP.values()))})


def tap(key, delay=0.03):
    k = KEY_MAP[key][0]
    ui.write(e.EV_KEY, k, 1)
    ui.syn()
    time.sleep(delay)
    ui.write(e.EV_KEY, k, 0)
    ui.syn()
    time.sleep(delay)


def down(key):
    ui.write(e.EV_KEY, KEY_MAP[key][0], 1)
    ui.syn()
    time.sleep(0.03)


def up(key):
    ui.write(e.EV_KEY, KEY_MAP[key][0], 0)
    ui.syn()
    time.sleep(0.03)


def type_unicode_hex(cp: int):
    """原版键序：Ctrl+Shift+U + hex + Enter"""
    down('lctrl')
    down('lshift')
    tap('u')
    up('lshift')
    for ch in format(cp, 'x'):
        tap(ch)
    up('lctrl')
    tap('enter')


if __name__ == '__main__':
    cps = sys.argv[1] if len(sys.argv) > 1 else '4e2d'  # 默认「中」
    time.sleep(3)  # 给聚焦留时间
    for c in cps.split(','):
        type_unicode_hex(int(c, 16))
        time.sleep(0.2)
    ui.close()
    print(f"done: typed {cps} via ctrl+shift+u path")
