#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright"]
# ///
"""
Tencent Meeting Transcript Exporter

Playwright-based exporter — opens a recording URL, scroll-collects the full
transcript, saves the result as TXT / Markdown / JSON.

- Reuses system Chrome / Edge (no Chromium download for most users)
- Persistent login cache under ~/.tencent-meeting-transcript/chrome-profile
- Auto-escalates to a visible window when login / password is required,
  shows a yellow bottom banner, polls until the user is through, then
  minimises the window and continues scraping in the background
- Fast adaptive MutationObserver scraper by default; `--safe` falls back
  to the slower but more thorough legacy path
- Auto-detects system locale for Chinese / English CLI output

Version: 1.0.0
Author:  Babywbx
Repo:    https://github.com/babywbx/Tencent-Meeting-Transcript-Exporter

Usage:
    uv run tencent_meeting_transcript.py <url> [options]

Run with `-h` / `--help` for the full argument list.
"""

import argparse
import atexit
import json
import locale
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

# ---------- never leave a __pycache__ next to the script ----------
# `uv run` and module-style imports can drop a .pyc into __pycache__/
# right beside this file. Belt-and-braces: stop new bytecode writes
# immediately, and sweep any pre-existing cache directory on exit so
# the repo root stays tidy even if a previous run left one behind.
sys.dont_write_bytecode = True


def _cleanup_script_pycache() -> None:
    cache_dir = Path(__file__).resolve().parent / "__pycache__"
    if cache_dir.is_dir():
        shutil.rmtree(cache_dir, ignore_errors=True)


atexit.register(_cleanup_script_pycache)


from playwright.sync_api import (
    sync_playwright,
    BrowserContext,
    Page,
    TimeoutError as PwTimeout,
)


# ---------- constants ----------

NAME = "Tencent Meeting Transcript Exporter"
VERSION = "1.0.0"
AUTHOR = "Babywbx"

PROFILE_DIR = Path.home() / ".tencent-meeting-transcript" / "chrome-profile"
POLL_INTERVAL_SEC = 3.0
AUTH_TIMEOUT_SEC = 600.0
WINDOW_W, WINDOW_H = 1200, 820  # outer window size (includes chrome in headed mode)
NAV_TIMEOUT_MS = 30_000


# ---------- output styling ----------

def _configure_stdio() -> None:
    """Avoid UnicodeEncodeError on legacy Windows consoles."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except Exception:
            pass


def _enable_windows_virtual_terminal() -> bool:
    """Best-effort ANSI support on Windows terminals."""
    if os.name != "nt":
        return True
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        enabled = False
        for handle_id in (-11, -12):  # stdout, stderr
            handle = kernel32.GetStdHandle(handle_id)
            if handle in (0, -1):
                continue
            mode = ctypes.c_uint32()
            if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                continue
            if kernel32.SetConsoleMode(handle, mode.value | 0x0004):
                enabled = True
        return enabled
    except Exception:
        return False


def _stream_supports_text(stream, text: str) -> bool:
    encoding = getattr(stream, "encoding", None)
    if not encoding:
        return True
    try:
        text.encode(encoding)
    except (LookupError, UnicodeEncodeError):
        return False
    return True


_configure_stdio()
SUPPORTS_COLOR = (
    sys.stdout.isatty()
    and "NO_COLOR" not in os.environ
    and _enable_windows_virtual_terminal()
)
SUPPORTS_UNICODE_SYMBOLS = all(
    _stream_supports_text(stream, "✓⚠✗→")
    for stream in (sys.stdout, sys.stderr)
)


def _ansi(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if SUPPORTS_COLOR else text


def dim(t: str) -> str: return _ansi("2", t)
def bold(t: str) -> str: return _ansi("1", t)
def green(t: str) -> str: return _ansi("32", t)
def yellow(t: str) -> str: return _ansi("33", t)
def red(t: str) -> str: return _ansi("31", t)
def cyan(t: str) -> str: return _ansi("36", t)


OK_SYM = green("✓" if SUPPORTS_UNICODE_SYMBOLS else "OK")
WARN_SYM = yellow("⚠" if SUPPORTS_UNICODE_SYMBOLS else "!")
ERR_SYM = red("✗" if SUPPORTS_UNICODE_SYMBOLS else "X")
ARROW_SYM = cyan("→" if SUPPORTS_UNICODE_SYMBOLS else "->")


def step(n: int, total: int, label: str) -> None:
    print(f"{dim(f'[{n}/{total}]')} {ARROW_SYM} {label}")


def info(label: str, indent: int = 2) -> None:
    print(f"{' ' * indent}{dim(label)}")


def detail(label: str, indent: int = 2) -> None:
    print(f"{' ' * indent}{label}")


def ok(label: str, indent: int = 2) -> None:
    print(f"{' ' * indent}{OK_SYM} {label}")


def warn(label: str, indent: int = 2) -> None:
    print(f"{' ' * indent}{WARN_SYM} {yellow(label)}")


def err(label: str) -> None:
    print(f"{ERR_SYM} {red(bold(label))}", file=sys.stderr)


def print_header() -> None:
    """Script title / version / author banner shown at startup."""
    print(f"{bold(cyan(NAME))} {dim(f'v{VERSION} · by {AUTHOR}')}")
    print()


# ---------- exceptions ----------

class ScriptCancelled(Exception):
    """Known failure with a translated message key — exits cleanly."""

    def __init__(self, msg_key: str, code: int = 1, detail: str = ""):
        self.msg_key = msg_key
        self.code = code
        self.detail = detail


# Playwright errors that indicate the browser / page has gone away.
_BROWSER_CLOSED_MARKERS = (
    "target page, context or browser has been closed",
    "target closed",
    "connection closed",
    "browser has been closed",
    "page has been closed",
)

_TRANSIENT_PAGE_MARKERS = (
    "execution context was destroyed",
    "cannot find context with specified id",
    "frame was detached",
    "most likely because of a navigation",
)


def _is_browser_closed(exc: BaseException) -> bool:
    s = str(exc).lower()
    return any(m in s for m in _BROWSER_CLOSED_MARKERS)


def _is_transient_page_error(exc: BaseException) -> bool:
    s = str(exc).lower()
    return any(m in s for m in _TRANSIENT_PAGE_MARKERS)


def _first_non_empty_line(*parts: str) -> str:
    for part in parts:
        for line in part.splitlines():
            stripped = line.strip()
            if stripped:
                return stripped
    return ""


def _format_exception_detail(exc: BaseException) -> str:
    short = _first_non_empty_line(str(exc))
    return f"{type(exc).__name__}: {short}" if short else type(exc).__name__


# ---------- i18n ----------

def detect_lang() -> str:
    """Return 'zh' or 'en' based on LC_* / LANG / Python locale."""
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        v = os.environ.get(var, "")
        if v:
            low = v.lower()
            if low.startswith("zh"):
                return "zh"
            if low.startswith("en"):
                return "en"
    try:
        code = locale.getlocale()[0] or ""
        if code.lower().startswith("zh"):
            return "zh"
    except Exception:
        pass
    return "en"


MSGS = {
    "en": {
        "opening": "Opening recording page",
        "checking": "Checking login state",
        "auth_need_login": "Authentication required",
        "auth_opening_window": "Opening browser window ...",
        "auth_please_login": "Please log in or enter the meeting password in the browser window",
        "auth_polling": f"Polling every {int(POLL_INTERVAL_SEC)}s (max {int(AUTH_TIMEOUT_SEC / 60)} min)",
        "auth_success": "Logged in",
        "auth_timeout": f"Login timed out after {int(AUTH_TIMEOUT_SEC / 60)} minutes",
        "auth_check_failed": "Authentication check failed",
        "expanding": "Expanding Transcription panel",
        "expand_warn": "Transcription toggle not found, continuing anyway",
        "collecting": "Scrolling & collecting transcript entries",
        "collected": "Collected {count} entries",
        "collect_incomplete": "Transcript collection did not reach a stable end; export aborted to avoid incomplete output",
        "saving": "Saving files",
        "done": "Done",
        "no_browser": "No system Chrome / Edge found — downloading Playwright Chromium (~170 MB, one-time)",
        "chromium_install_failed": "Failed to install Playwright Chromium automatically",
        "cancelled_user": "Cancelled by user (Ctrl+C)",
        "browser_closed": "Browser window was closed before finishing",
        "timeout_op": "Operation timed out",
        "unreachable": "Cannot reach the recording page — check your network connection and the URL",
        "empty_transcript": "This recording has no transcript (transcription was not enabled for the meeting)",
        "unexpected": "Unexpected error",
        "banner_title": "Please log in or enter the meeting password",
        "banner_sub": "This script will continue automatically once you are in.",
    },
    "zh": {
        "opening": "打开录制页面",
        "checking": "检查登录状态",
        "auth_need_login": "需要登录或输入密码",
        "auth_opening_window": "正在打开浏览器窗口 ...",
        "auth_please_login": "请在浏览器窗口中登录,或输入会议密码",
        "auth_polling": f"每 {int(POLL_INTERVAL_SEC)} 秒检查一次(最多等 {int(AUTH_TIMEOUT_SEC / 60)} 分钟)",
        "auth_success": "登录成功",
        "auth_timeout": f"等待登录超时({int(AUTH_TIMEOUT_SEC / 60)} 分钟)",
        "auth_check_failed": "登录状态检查失败",
        "expanding": "展开转写面板",
        "expand_warn": "未找到转写按钮,尝试继续执行",
        "collecting": "滚动收集逐字稿",
        "collected": "已收集 {count} 条记录",
        "collect_incomplete": "逐字稿采集未能稳定到达末尾，为避免导出不完整内容已中止",
        "saving": "保存文件",
        "done": "完成",
        "no_browser": "未检测到系统 Chrome / Edge —— 正在下载 Playwright Chromium(约 170 MB,一次性)",
        "chromium_install_failed": "自动安装 Playwright Chromium 失败",
        "cancelled_user": "用户取消操作(Ctrl+C)",
        "browser_closed": "浏览器窗口被提前关闭",
        "timeout_op": "操作超时",
        "unreachable": "无法访问录制页面 —— 请检查网络连接和链接",
        "empty_transcript": "这场录制没有逐字稿(会议当时没有开启转写功能)",
        "unexpected": "发生意外错误",
        "banner_title": "请登录或输入会议密码",
        "banner_sub": "完成后脚本会自动继续运行。",
    },
}


# ---------- browser launching ----------

def install_chromium() -> None:
    """Download Playwright's bundled Chromium (fallback path)."""
    result = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = _first_non_empty_line(result.stderr, result.stdout)
        if detail:
            detail = f"{detail} (exit code {result.returncode})"
        else:
            detail = f"playwright install chromium exited with code {result.returncode}"
        raise ScriptCancelled("chromium_install_failed", detail=detail)


def launch_context(p, headless: bool, msgs: dict) -> BrowserContext:
    """Launch persistent context: system Chrome → Edge → bundled Chromium."""
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    common: dict = {
        "user_data_dir": str(PROFILE_DIR),
        "headless": headless,
        "ignore_default_args": [
            "--enable-automation",
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
        ],
        "args": [
            f"--window-size={WINDOW_W},{WINDOW_H}",
            # Auto-deny every permission prompt (mic, cam, notifications,
            # protocol handlers, "access other apps", window management …).
            "--deny-permission-prompts",
            "--disable-extensions",
            "--disable-default-apps",
            "--disable-notifications",
            "--disable-translate",
            "--disable-features=Translate,TranslateUI,AutofillServerCommunication,RegisterProtocolHandler,WebAppProtocolHandlers,GetInstalledRelatedApps,InstalledApp",
            "--disable-sync",
            "--disable-background-networking",
            "--no-first-run",
            "--no-default-browser-check",
        ],
    }
    # Headless has no real window — emulate viewport. Headed mode lets the
    # actual window size drive viewport (avoids double-counting chrome height
    # and stops Playwright from reserving phantom space for the old infobar).
    if headless:
        common["viewport"] = {"width": WINDOW_W, "height": WINDOW_H}
    else:
        common["no_viewport"] = True

    context: BrowserContext | None = None
    for channel in ("chrome", "msedge"):
        try:
            context = p.chromium.launch_persistent_context(channel=channel, **common)
            break
        except Exception:
            continue
    if context is None:
        try:
            context = p.chromium.launch_persistent_context(**common)
        except Exception:
            warn(msgs["no_browser"])
            install_chromium()
            context = p.chromium.launch_persistent_context(**common)

    harden_context(context)
    return context


def first_page(context: BrowserContext) -> Page:
    """Return the existing about:blank page (if any) instead of opening a new tab."""
    return context.pages[0] if context.pages else context.new_page()


def minimize_window(page: Page) -> None:
    """Minimize the browser window via CDP — sends it to the dock/taskbar
    without closing the context. Used after a successful login so the
    password session (which is tied to the window, not cookies) survives."""
    try:
        cdp = page.context.new_cdp_session(page)
        win = cdp.send("Browser.getWindowForTarget")
        cdp.send("Browser.setWindowBounds", {
            "windowId": win["windowId"],
            "bounds": {"windowState": "minimized"},
        })
    except Exception:
        pass  # not critical — fall back to visible window


# Neutralise the Tencent Meeting page's attempts to hand off to the desktop
# app — blocks the "Access other apps and services on this device" prompt
# that is triggered by getInstalledRelatedApps / registerProtocolHandler,
# plus any custom-scheme click-to-launch links.
HARDEN_JS = """
(() => {
  const noopFn = function() {};
  const emptyListPromise = function() { return Promise.resolve([]); };

  function forceReplace(obj, prop, value) {
    try { obj[prop] = value; } catch (e) {}
    try {
      Object.defineProperty(obj, prop, {
        value: value, writable: true, configurable: true,
      });
    } catch (e) {}
  }

  // Kill getInstalledRelatedApps on both the instance and the prototype —
  // this is the main trigger for the "access other apps" prompt.
  forceReplace(navigator, 'getInstalledRelatedApps', emptyListPromise);
  if (typeof Navigator !== 'undefined' && Navigator.prototype) {
    forceReplace(Navigator.prototype, 'getInstalledRelatedApps', emptyListPromise);
  }

  // Kill registerProtocolHandler (another source of app-handoff prompts).
  forceReplace(navigator, 'registerProtocolHandler', noopFn);
  if (typeof Navigator !== 'undefined' && Navigator.prototype) {
    forceReplace(Navigator.prototype, 'registerProtocolHandler', noopFn);
  }

  // Force permissions.query() to say "denied" for any related-app query.
  try {
    if (navigator.permissions && navigator.permissions.query) {
      const origQuery = navigator.permissions.query.bind(navigator.permissions);
      navigator.permissions.query = function(desc) {
        const name = (desc && desc.name) || '';
        if (/installed-app|related-app|protocol-handler|launch|window-management|local-network/i.test(name)) {
          return Promise.resolve({ state: 'denied', onchange: null });
        }
        return origQuery(desc);
      };
    }
  } catch (e) {}

  // Disable the PWA Launch Handler API.
  try { delete window.launchQueue; } catch (e) {}

  // Block clicks on custom-scheme links (wemeet://, tencent://, etc.).
  document.addEventListener('click', function(e) {
    const a = e.target && e.target.closest && e.target.closest('a');
    if (a && a.href && /^(wemeet|tencent|wechat|ms-|mailto):/i.test(a.href)) {
      e.preventDefault();
      e.stopPropagation();
    }
  }, true);

  // Strip custom-scheme URLs from window.open.
  const _open = window.open;
  window.open = function(url) {
    if (typeof url === 'string' && /^(wemeet|tencent|wechat|ms-):/i.test(url)) {
      return null;
    }
    return _open.apply(window, arguments);
  };
})();
"""


def harden_context(context: BrowserContext) -> None:
    """Install the init script on every page + grant zero permissions."""
    try:
        # Explicitly grant nothing — Playwright auto-denies any known
        # permission request that reaches this context.
        context.grant_permissions([])
    except Exception:
        pass
    try:
        context.add_init_script(HARDEN_JS)
    except Exception:
        pass


# ---------- auth detection + banner ----------

# Yellow bottom banner. Attached to <html> (not <body>) so any body-level
# transform / filter / perspective can't trap our fixed positioning. Uses a
# full-viewport flex wrapper to anchor the banner to the bottom, which is
# more reliable than `bottom:0` alone when the host page has a weird
# containing block. Built via createElement/textContent (no innerHTML).
BANNER_JS = """
(args) => {
  const [title, sub] = args;

  function applyStyles(el, rules) {
    for (const [k, v] of Object.entries(rules)) {
      el.style.setProperty(k, v, 'important');
    }
  }

  // Reset html/body bottom spacing — some Tencent Meeting builds leave
  // bottom padding that pushes fixed elements away from the viewport edge.
  for (const el of [document.documentElement, document.body]) {
    el.style.setProperty('margin-bottom', '0', 'important');
    el.style.setProperty('padding-bottom', '0', 'important');
  }

  let wrapper = document.getElementById('tm-auth-wrapper');
  if (!wrapper) {
    // Full-viewport flex column, bottom-aligned. Invisible itself; only the
    // banner inside it is visible.
    wrapper = document.createElement('div');
    wrapper.id = 'tm-auth-wrapper';
    applyStyles(wrapper, {
      'position': 'fixed',
      'top': '0',
      'left': '0',
      'width': '100vw',
      'height': '100vh',
      'display': 'flex',
      'flex-direction': 'column',
      'justify-content': 'flex-end',
      'align-items': 'stretch',
      'margin': '0',
      'padding': '0',
      'border': '0',
      'background': 'transparent',
      'pointer-events': 'none',
      'z-index': '2147483647',
    });

    const banner = document.createElement('div');
    banner.id = 'tm-auth-banner';
    applyStyles(banner, {
      'min-height': '96px',
      'width': '100%',
      'display': 'flex',
      'flex-direction': 'column',
      'justify-content': 'center',
      'align-items': 'center',
      'row-gap': '6px',
      'background': 'linear-gradient(180deg,#FFE066,#FFC107)',
      'color': '#000',
      'text-align': 'center',
      'padding': '16px 24px',
      'margin': '0',
      'box-sizing': 'border-box',
      'box-shadow': '0 -4px 16px rgba(0,0,0,.25)',
      'font-family': '-apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif',
      'border': '0',
    });

    const titleEl = document.createElement('div');
    titleEl.className = 'tm-title';
    applyStyles(titleEl, {
      'font-size': '20px',
      'font-weight': '700',
      'line-height': '1.3',
      'margin': '0',
      'padding': '0',
    });
    banner.appendChild(titleEl);

    const subEl = document.createElement('div');
    subEl.className = 'tm-sub';
    applyStyles(subEl, {
      'font-size': '14px',
      'opacity': '0.85',
      'line-height': '1.3',
      'margin': '0',
      'padding': '0',
    });
    banner.appendChild(subEl);

    wrapper.appendChild(banner);
    // Attach to <html>, not <body> — skips any transform-based containing
    // block on body-level elements that would hijack fixed positioning.
    document.documentElement.appendChild(wrapper);
  }
  wrapper.querySelector('.tm-title').textContent = title;
  wrapper.querySelector('.tm-sub').textContent = sub;
}
"""


PAGE_LANG_JS = """
() => {
    // 1. <html lang="..."> — most authoritative when present
    const htmlLang = (document.documentElement.lang || '').toLowerCase();
    if (htmlLang.startsWith('zh')) return 'zh';
    if (htmlLang.startsWith('en')) return 'en';

    // 2. Password-page input placeholder (primary login/password view)
    for (const inp of document.querySelectorAll('input')) {
        const ph = (inp.placeholder || '').trim();
        if (!ph) continue;
        if (/password/i.test(ph)) return 'en';
        if (/密码/.test(ph)) return 'zh';
    }

    // 3. Primary button label (Go to View / 查看 / Login / 登录)
    for (const btn of document.querySelectorAll('button, .met-btn')) {
        const t = (btn.textContent || '').trim();
        if (!t) continue;
        if (/^(Go to View|View|Sign In|Log In|Login)$/i.test(t)) return 'en';
        if (/^(查看|去查看|登录|登入)$/.test(t)) return 'zh';
    }

    // 4. Native toolbar button text (only present once logged in)
    const saveAs = document.querySelector('.saveas-btn .met-dropdown-icon-text');
    if (saveAs) {
        const t = saveAs.textContent.trim();
        if (t === '另存为') return 'zh';
        if (t === 'Save as') return 'en';
    }

    // 5. Body text keyword count (last-resort fallback)
    const body = document.body.innerText || '';
    const zhHits = (body.match(/请输入.*密码|访问密码|下次访问|另存为|分享|翻译/g) || []).length;
    const enHits = (body.match(/access password|Password not required|\\bSave as\\b|\\bShare\\b|\\bTranslators\\b/g) || []).length;
    if (zhHits > enHits && zhHits > 0) return 'zh';
    if (enHits > 0) return 'en';

    return null;
}
"""


def detect_page_lang(page: Page) -> str | None:
    """Detect UI language from the currently loaded page. Returns 'zh' / 'en' / None."""
    try:
        return page.evaluate(PAGE_LANG_JS)
    except Exception:
        return None


def is_auth_required(page: Page) -> bool:
    """True if the recording toolbar is absent."""
    return page.locator(".buttons-container").count() == 0


# Combined DOM read: returns (authRequired, hasPasswordInput) in one IPC call.
# hasPasswordInput distinguishes "shared file with per-window password session"
# from "own file with pure login" — the former must keep the headed window
# alive, the latter can drop back to headless once cookies are cached.
AUTH_STATE_JS = """
() => {
    const toolbar = document.querySelector('.buttons-container');
    if (toolbar) return { authRequired: false, hasPwd: false };
    let hasPwd = false;
    for (const i of document.querySelectorAll('input')) {
        const ph = ((i.placeholder || '') + '').toLowerCase();
        if (ph.includes('password') || ph.indexOf('密码') >= 0) {
            hasPwd = true;
            break;
        }
    }
    return { authRequired: true, hasPwd: hasPwd };
}
"""


def read_auth_state(page: Page) -> tuple[bool, bool]:
    """Returns (authRequired, hasPasswordInput) in a single IPC call."""
    result = page.evaluate(AUTH_STATE_JS)
    return bool(result["authRequired"]), bool(result["hasPwd"])


# Fast path for Case B with cached password: when the user is already logged
# in AND the meeting password is saved to their Tencent account, the page
# only needs a single click on the "Go to View" / "查看" button to proceed.
# Trying this click from headless avoids showing the browser window at all.
AUTO_PROCEED_JS = """
() => {
    const labels = /^(go to view|view|查看|去查看)$/i;
    for (const b of document.querySelectorAll('button, .met-btn, [role="button"]')) {
        const text = (b.textContent || '').trim();
        if (!labels.test(text)) continue;
        if (b.disabled) continue;
        if (b.getAttribute('aria-disabled') === 'true') continue;
        const cls = (b.className || '') + '';
        if (/is-disabled|disabled/i.test(cls)) continue;
        b.click();
        return true;
    }
    return false;
}
"""


def try_auto_proceed(page: Page) -> bool:
    """Headless fast path: click the 'Go to View' button if present. Returns
    True when the click actually bypassed the auth gate. Safe to call on any
    page — returns False if no matching button, or if the click failed to
    reveal the recording toolbar."""
    try:
        if not page.evaluate(AUTO_PROCEED_JS):
            return False
        page.wait_for_timeout(1500)
        return not is_auth_required(page)
    except Exception:
        return False


def show_auth_banner(page: Page, msgs: dict) -> None:
    try:
        page.evaluate(BANNER_JS, [msgs["banner_title"], msgs["banner_sub"]])
    except Exception:
        pass  # page may be mid-navigation


def wait_for_auth(page: Page, msgs: dict) -> tuple[bool, bool]:
    """Poll the DOM every 300 ms. Returns (success, saw_password_gate).
    saw_password is True if a password input was ever seen during the flow —
    callers use that flag to decide whether the browser window must stay
    alive (password sessions are per-window) or can be closed + reopened."""
    deadline = time.monotonic() + AUTH_TIMEOUT_SEC
    next_banner = 0.0
    saw_password = False
    while time.monotonic() < deadline:
        try:
            auth_required, has_pwd = read_auth_state(page)
            if not auth_required:
                return True, saw_password
            if has_pwd:
                saw_password = True
            if time.monotonic() >= next_banner:
                show_auth_banner(page, msgs)
                next_banner = time.monotonic() + POLL_INTERVAL_SEC
        except Exception as e:
            if _is_browser_closed(e):
                raise ScriptCancelled("browser_closed") from e
            if not _is_transient_page_error(e):
                raise ScriptCancelled("auth_check_failed", detail=_format_exception_detail(e)) from e
        time.sleep(0.3)
    return False, saw_password


# ---------- core scraper JS ----------

COLLECT_SCRIPT = """
async (safe) => {
    const container = document.querySelector('.minutes-module-list');
    if (!container) return { error: 'Transcription container not found', code: 'empty_transcript' };

    const transcript = new Map();

    function collectVisible() {
        let added = 0;
        for (const p of container.querySelectorAll('[class*="paragraph-module_paragraph"]')) {
            const pid = p.getAttribute('data-pid');
            if (!pid || transcript.has(pid)) continue;
            const speaker = p.querySelector('[class*="speaker-name"]')?.textContent?.trim() || '';
            const time = p.querySelector('[class*="p-start-time"]')?.textContent?.trim() || '';
            const text = p.querySelector('[class*="paragraph-module_sentences"]')?.textContent?.trim() || '';
            if (speaker || text) {
                transcript.set(pid, { pid: parseInt(pid), speaker, time, text });
                added += 1;
            }
        }
        return added;
    }

    function maxPid() {
        let max = -1;
        for (const n of container.querySelectorAll('[class*="paragraph-module_paragraph"]')) {
            const v = parseInt(n.getAttribute('data-pid') || '-1');
            if (v > max) max = v;
        }
        return max;
    }

    // Adaptive wait — resolves as soon as a paragraph with pid > prevMaxPid
    // appears in the DOM (new content rendered), or after maxMs timeout.
    function waitForNewContent(prevMaxPid, maxMs) {
        return new Promise(resolve => {
            let done = false;
            let timer = 0;
            let obs = null;
            const finish = (didGrow) => {
                if (done) return;
                done = true;
                clearTimeout(timer);
                if (obs) obs.disconnect();
                resolve(didGrow);
            };
            obs = new MutationObserver(() => {
                if (maxPid() > prevMaxPid) finish(true);
            });
            obs.observe(container, { childList: true, subtree: true });
            timer = setTimeout(() => finish(maxPid() > prevMaxPid), maxMs);
            setTimeout(() => {
                if (maxPid() > prevMaxPid) finish(true);
            }, 15);
        });
    }

    const scrollFactor = safe ? 0.6 : 1.0;
    const initialWait = safe ? 500 : 300;
    const safeWait = 200;
    const adaptiveMaxWait = 250;
    const maxRounds = 5000;
    const maxStagnantRounds = 4;

    container.scrollTop = 0;
    await new Promise(r => setTimeout(r, initialWait));

    let rounds = 0;
    let stagnantRounds = 0;
    while (true) {
        collectVisible();
        const prevMax = maxPid();
        const prevCount = transcript.size;
        const prev = container.scrollTop;
        container.scrollTop += container.clientHeight * scrollFactor;
        if (safe) {
            await new Promise(r => setTimeout(r, safeWait));
        } else {
            await waitForNewContent(prevMax, adaptiveMaxWait);
        }
        const added = collectVisible();
        const currentMax = maxPid();
        const moved = Math.abs(container.scrollTop - prev) >= 2;
        const advanced = currentMax > prevMax || transcript.size > prevCount || added > 0;

        rounds++;
        if (!moved && !advanced) {
            stagnantRounds++;
        } else {
            stagnantRounds = 0;
        }

        if (stagnantRounds >= maxStagnantRounds) break;
        if (rounds >= maxRounds) {
            return {
                error: 'Transcript collection exceeded the safety iteration limit before reaching a stable end',
                code: 'collect_incomplete',
                count: transcript.size,
                rounds,
            };
        }
    }

    const sorted = Array.from(transcript.values()).sort((a, b) => a.pid - b.pid);
    return { count: sorted.length, rounds, entries: sorted };
}
"""

META_SCRIPT = """
() => {
    // The recording title lives in a CSS Module hashed div — use prefix match.
    const titleEl = document.querySelector('[class*="title-with-edit"]');
    const title = titleEl ? (titleEl.textContent || '').trim() : '';
    return { title, date: '' };
}
"""


# ---------- main pipeline ----------

def ensure_authenticated(
    p, context: BrowserContext, page: Page, url: str, headed: bool, msgs: dict
) -> tuple[BrowserContext, Page, dict]:
    """Handle login / password pages. Tries a headless auto-click fast path
    first; falls back to opening a visible window when real user interaction
    is required."""
    if not is_auth_required(page):
        return context, page, msgs

    # Fast path: cached cookies + account-saved password → Tencent only
    # shows a single "Go to View" button. Click it from headless and skip
    # escalation entirely.
    if try_auto_proceed(page):
        ok(msgs["auth_success"])
        return context, page, msgs

    warn(msgs["auth_need_login"])
    escalated = not headed

    if escalated:
        info(msgs["auth_opening_window"])
        context.close()
        context = launch_context(p, headless=False, msgs=msgs)
        page = first_page(context)
        page.goto(url, wait_until="networkidle", timeout=NAV_TIMEOUT_MS)
        page.wait_for_timeout(500)

        # Refresh language from the now-visible page
        msgs = _maybe_switch_lang(page, msgs)

        if not is_auth_required(page):
            # Cached cookies already logged us in; minimise and move on.
            ok(msgs["auth_success"])
            minimize_window(page)
            return context, page, msgs

    info(msgs["auth_please_login"])
    show_auth_banner(page, msgs)
    info(msgs["auth_polling"])

    success, saw_password = wait_for_auth(page, msgs)
    if not success:
        raise ScriptCancelled("auth_timeout")

    ok(msgs["auth_success"])

    # Banner cleanup regardless of mode
    try:
        page.evaluate("() => document.getElementById('tm-auth-wrapper')?.remove()")
    except Exception:
        pass

    if escalated:
        if saw_password:
            # Shared file with a password gate — session is bound to THIS
            # window. Closing would force another password entry. Just hide
            # the window by minimising it to the dock.
            minimize_window(page)
        else:
            # Pure login flow (own file / public file) — cookies now cache
            # the session, so it's safe to close the visible window and
            # continue fully headless.
            context.close()
            context = launch_context(p, headless=True, msgs=msgs)
            page = first_page(context)
            page.goto(url, wait_until="networkidle", timeout=NAV_TIMEOUT_MS)
            page.wait_for_timeout(500)

    return context, page, msgs


def _maybe_switch_lang(page: Page, msgs: dict) -> dict:
    """Re-detect UI language from the page; swap msgs if it differs."""
    detected = detect_page_lang(page)
    if detected and MSGS[detected] is not msgs:
        return MSGS[detected]
    return msgs


def click_transcription_toggle(page: Page, msgs: dict) -> None:
    """Expand the Transcription panel if it is not already open. Matches both
    English and Chinese toggle text. Silent on success; warns only when
    neither a visible toggle nor an already-open panel can be found."""
    # Skip clicking entirely when the panel is already rendered.
    if page.locator(".minutes-module-list").count() > 0:
        return
    for label in ("Transcription", "转写"):
        try:
            btn = page.locator(f"text={label}").first
            btn.wait_for(state="visible", timeout=5_000)
            parent = btn.locator("..").locator("button").first
            if parent.count() > 0:
                parent.click()
            else:
                btn.click()
            page.wait_for_timeout(1500)
            return
        except PwTimeout:
            continue
    warn(msgs["expand_warn"])


def extract_transcript(
    url: str, headed: bool, safe: bool, msgs: dict
) -> tuple[dict, list[dict], dict]:
    """Drive the full extraction pipeline. Raises ScriptCancelled on known errors.
    Returns (metadata, entries, msgs) — msgs may have been swapped to match
    the page's detected UI language."""
    with sync_playwright() as p:
        context = None
        try:
            context = launch_context(p, headless=not headed, msgs=msgs)
            page = first_page(context)

            step(1, 5, msgs["opening"])
            detail(url)
            try:
                page.goto(url, wait_until="networkidle", timeout=NAV_TIMEOUT_MS)
            except PwTimeout as e:
                raise ScriptCancelled("unreachable") from e

            # Re-detect language from the live page — match subsequent output
            # to whatever Tencent Meeting is actually rendering.
            msgs = _maybe_switch_lang(page, msgs)

            step(2, 5, msgs["checking"])
            page.wait_for_timeout(500)
            context, page, msgs = ensure_authenticated(p, context, page, url, headed, msgs)

            # Metadata — prefer the dedicated title-with-edit DOM node; fall
            # back to a regex over the visible body text if the selector
            # fails (e.g. Tencent Meeting rotates its CSS class hash).
            meta = page.evaluate(META_SCRIPT)
            header_text = page.inner_text("body")
            title = (meta.get("title") or "").strip()
            if not title:
                title_match = re.search(r"(\d{4}/\d{2}/\d{2}\s+.+?)(?:\n|$)", header_text)
                title = title_match.group(1).strip() if title_match else "meeting"
            date_match = re.search(r"(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2})", header_text)
            date = date_match.group(1).strip() if date_match else ""

            step(3, 5, msgs["expanding"])
            click_transcription_toggle(page, msgs)

            try:
                page.wait_for_selector(".minutes-module-list", timeout=10_000)
            except PwTimeout as e:
                raise ScriptCancelled("empty_transcript") from e

            step(4, 5, msgs["collecting"])
            result = page.evaluate(COLLECT_SCRIPT, safe)

            if isinstance(result, dict) and "error" in result:
                raise ScriptCancelled(result.get("code", "empty_transcript"), detail=result["error"])

            entries = result["entries"]
            info(msgs["collected"].format(count=result["count"]))

            speakers = list(dict.fromkeys(e["speaker"] for e in entries if e["speaker"]))
            metadata = {
                "title": title,
                "date": date,
                "speakers": speakers,
                "count": len(entries),
            }
            return metadata, entries, msgs
        finally:
            if context is not None:
                try:
                    context.close()
                except Exception:
                    pass


# ---------- file writers (file contents in Chinese for parity across scripts) ----------

def save_txt(metadata: dict, entries: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(f'{metadata["title"]} - 逐字稿\n')
        handle.write(f'录制日期：{metadata["date"]}\n')
        handle.write(f'参与者：{"、".join(metadata["speakers"])}\n')
        handle.write(f'共 {metadata["count"]} 条记录\n')
        handle.write("=" * 60)
        handle.write("\n\n")
        for e in entries:
            handle.write(f'[{e["time"]}] {e["speaker"]}\n')
            handle.write(f'{e["text"]}\n\n')


def save_md(metadata: dict, entries: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(f'# {metadata["title"]} - 逐字稿\n\n')
        handle.write(f'- **录制日期**：{metadata["date"]}\n')
        handle.write(f'- **参与者**：{"、".join(metadata["speakers"])}\n')
        handle.write(f'- **记录条数**：{metadata["count"]}\n\n')
        handle.write("---\n\n")

        current = None
        for e in entries:
            if e["speaker"] != current:
                current = e["speaker"]
                handle.write(f'### {e["speaker"]}  `{e["time"]}`\n\n')
            else:
                handle.write(f'**`{e["time"]}`**\n\n')
            handle.write(f'{e["text"]}\n\n')


def save_json(metadata: dict, entries: list[dict], path: Path) -> None:
    data = {"metadata": metadata, "entries": entries}
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def expand_cli_path(raw: str) -> Path:
    """Expand ~ and environment variables in CLI path arguments."""
    expanded = os.path.expandvars(os.path.expanduser(raw))
    expanded = re.sub(
        r"%([^%]+)%",
        lambda match: os.environ.get(match.group(1), match.group(0)),
        expanded,
    )
    return Path(expanded)


def make_filename(title: str) -> str:
    """Convert the recording title to a filesystem-safe filename, appending
    ` - 逐字稿`. Preserves the original formatting (e.g. the space between
    date and topic) while staying valid on Windows too."""
    safe = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "-", title).strip()
    safe = re.sub(r"\s+", " ", safe)
    safe = safe.rstrip(" .")
    if not safe:
        safe = "meeting"
    return f"{safe} - 逐字稿"


# ---------- runner + error boundary ----------

# Output format → (column label, saver function)
SAVERS = {
    "txt": ("TXT ", save_txt),
    "md": ("MD  ", save_md),
    "json": ("JSON", save_json),
}


def run(args: argparse.Namespace, msgs: dict) -> dict:
    """Run the full extraction + save pipeline. Returns the (possibly updated) msgs."""
    metadata, entries, msgs = extract_transcript(
        args.url, headed=args.headed, safe=args.safe, msgs=msgs
    )

    out_dir = expand_cli_path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    basename = make_filename(metadata["title"])

    step(5, 5, msgs["saving"])
    # Stable save order regardless of how the user passed -f.
    for fmt in ("txt", "md", "json"):
        if fmt not in args.formats:
            continue
        label, saver = SAVERS[fmt]
        path = out_dir / f"{basename}.{fmt}"
        saver(metadata, entries, path)
        ok(f"{label}  → {path}")

    return msgs


def _print_error(msgs: dict, msg_key: str, detail_text: str = "") -> None:
    print()
    err(msgs[msg_key])
    if detail_text:
        print(f"  {dim(detail_text)}", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    """Define the CLI surface."""
    parser = argparse.ArgumentParser(
        prog="tencent_meeting_transcript",
        description=(
            "Tencent Meeting Transcript Exporter — scrape a recording's "
            "transcript and save as TXT / Markdown / JSON."
        ),
        epilog=(
            "examples:\n"
            "  %(prog)s <url>                      # export TXT to the current directory\n"
            "  %(prog)s <url> -f md                # export Markdown only\n"
            "  %(prog)s <url> -f txt md json       # export all three formats\n"
            "  %(prog)s <url> -f all -o ~/Desktop  # shorthand + custom output dir\n"
            "  %(prog)s <url> -o %%USERPROFILE%%\\\\Desktop  # Windows env-var path\n"
            "  %(prog)s <url> --safe               # slower but more thorough scrape\n"
            "  %(prog)s <url> --headed             # show the browser window\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "url",
        help="Tencent Meeting recording URL (https://meeting.tencent.com/cw/... or /crm/...)",
    )
    parser.add_argument(
        "-f",
        "--format",
        nargs="+",
        default=["txt"],
        choices=["txt", "md", "json", "all"],
        metavar="FMT",
        help="Output format(s): txt / md / json / all (default: txt)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=".",
        metavar="DIR",
        help="Output directory (supports ~ and environment variables; default: current directory)",
    )
    parser.add_argument(
        "-s",
        "--safe",
        action="store_true",
        help="Use the slower-but-thorough scrape mode (60%% scroll step, "
        "fixed 200 ms wait). Try this if the default fast mode produces "
        "fewer entries than expected.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Force the browser window to stay visible (useful for debugging).",
    )
    parser.add_argument(
        "-l",
        "--lang",
        choices=["auto", "zh", "en"],
        default="auto",
        help="CLI output language (default: auto-detect from system locale)",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {VERSION} · by {AUTHOR}",
    )
    return parser


def main() -> None:
    parser = build_parser()

    # Empty run → print help and exit cleanly.
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    # Expand format list: "all" is a shortcut for every known format.
    formats = set(args.format)
    if "all" in formats:
        formats = {"txt", "md", "json"}
    args.formats = formats

    lang = detect_lang() if args.lang == "auto" else args.lang
    msgs = MSGS[lang]

    print_header()

    start = time.monotonic()
    try:
        msgs = run(args, msgs)
    except KeyboardInterrupt:
        _print_error(msgs, "cancelled_user")
        sys.exit(130)
    except ScriptCancelled as e:
        _print_error(msgs, e.msg_key, e.detail)
        sys.exit(e.code)
    except PwTimeout:
        _print_error(msgs, "timeout_op")
        sys.exit(1)
    except Exception as e:
        if _is_browser_closed(e):
            _print_error(msgs, "browser_closed")
        else:
            _print_error(msgs, "unexpected", _format_exception_detail(e))
        sys.exit(1)

    elapsed = time.monotonic() - start
    print()
    print(f"{OK_SYM} {green(bold(msgs['done']))} {dim(f'({elapsed:.1f}s)')}")


if __name__ == "__main__":
    main()
