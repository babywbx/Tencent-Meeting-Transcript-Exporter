<div align="center"><a name="readme-top"></a>

# Tencent Meeting Transcript Exporter

A toolkit for exporting Tencent Meeting recording transcripts as TXT / Markdown / JSON,<br/>
shipped as a Tampermonkey userscript, a browser console snippet, and a Python CLI.

[简体中文](./README.md) · [Report Issue][github-issues-link] · [Changelog][github-release-link]

<!-- SHIELD GROUP -->

[![][github-stars-shield]][github-stars-link]
[![][github-forks-shield]][github-forks-link]
[![][github-issues-shield]][github-issues-link]
[![][github-license-shield]][github-license-link]<br/>
[![][github-contributors-shield]][github-contributors-link]
[![][github-lastcommit-shield]][github-lastcommit-link]

</div>

<details>
<summary><kbd>Table of Contents</kbd></summary>

#### TOC

- [✨ Features](#-features)
- [📦 Three Ways to Use](#-three-ways-to-use)
- [🚀 Quick Start](#-quick-start)
  - [Option 1: Tampermonkey Userscript (recommended)](#option-1-tampermonkey-userscript-recommended)
  - [Option 2: Browser Console (one-shot)](#option-2-browser-console-one-shot)
  - [Option 3: Python CLI (unattended / automation)](#option-3-python-cli-unattended--automation)
- [📂 Output Formats](#-output-formats)
- [🌐 Multilingual Support](#-multilingual-support)
- [🔍 How It Works](#-how-it-works)
- [❓ FAQ](#-faq)
- [📝 License](#-license)

####

<br/>

</details>

## ✨ Features

> \[!WARNING\]
>
> **Last tested: 2026-04-15** · The scripts depend on Tencent Meeting's current DOM structure (CSS Module hashed class names, virtual list selectors, etc.). If Tencent Meeting ships a UI update, the selectors may break — the injected button may lose styling, or the scraping may return zero entries. Please open an issue, or check the [🔍 How It Works](#-how-it-works) section to patch the selectors yourself.

> \[!IMPORTANT\]
>
> **Star Us** — you will receive all release notifications from GitHub without any delay \~ ⭐️

This project solves one problem well: **reliably export the full transcript from a Tencent Meeting recording page to local files**. Core goals:

- **🎯 Full capture** — `MutationObserver`-driven adaptive scrolling, no sentence missed
- **⚡️ Fast** — a typical 1-hour meeting (~327 entries) finishes in **under 3 seconds** (5× faster than the legacy path)
- **📄 Multi-format** — TXT / Markdown / JSON on demand, pick any combination
- **🌐 Multilingual** — auto-detects Tencent Meeting's UI language (Chinese / English) and matches the output
- **🖼️ Native look** — the userscript button blends perfectly into the toolbar, matching "Save as" / "Translate"
- **🔒 Local-only** — everything happens in your browser or local machine, no third-party upload
- **🔐 Password meetings** — Python CLI auto-detects login / password pages, pops a visible window for you, then silently minimises it and keeps scraping in the background
- **🎛️ Three flavors** — CLI / console snippet / userscript button, pick whatever fits your workflow

<div align="right">

[![][back-to-top]](#readme-top)

</div>

## 📦 Three Ways to Use

Three tools accomplish the same task. Core scraping logic is identical — only the runtime differs. Listed in order of recommendation:

| Tool | File | Best For | Formats |
| --- | --- | --- | --- |
| 🖱️ **Userscript** (⭐ Recommended) | `tencent_meeting_transcript.user.js` | Long-term use, one-click button, native toolbar look | TXT / MD / both |
| 📋 **Console Snippet** | `tencent_meeting_transcript.js` | Occasional one-off use, no extension install | TXT + MD |
| 🐍 **Python CLI** | `tencent_meeting_transcript.py` | Unattended runs, batch jobs, password-protected recordings | TXT / MD / JSON in any combination |

> \[!TIP\]
>
> For most users, just install the **userscript** — it auto-adds an "Export Transcript" button to every recording page.<br/>
> For a one-off run without installing anything: use the **console snippet**.<br/>
> For batch export, unattended runs, or integration with other tools: use the **Python CLI**.

<div align="right">

[![][back-to-top]](#readme-top)

</div>

## 🚀 Quick Start

### Option 1: Tampermonkey Userscript (recommended)

**Step 1 · Install Tampermonkey:**

- Chrome / Edge / Arc / Brave: [Chrome Web Store][tampermonkey-chrome-link]
- Safari: use the free [Userscripts][userscripts-safari-link] extension

> \[!IMPORTANT\]
>
> Chrome 138+ requires enabling **Developer mode** at `chrome://extensions/` — otherwise userscripts will not run at all.

**Step 2 · One-click install this script:**

With Tampermonkey installed, click the link below — your browser opens the Tampermonkey install prompt directly. Click **Install**:

👉 **[Click to install the latest version][userscript-install-link]** 👈

Or copy the raw URL manually:

```
https://github.com/babywbx/Tencent-Meeting-Transcript-Exporter/raw/main/tencent_meeting_transcript.user.js
```

> \[!TIP\]
>
> Tampermonkey will **auto-check this URL for updates**, so you will get an upgrade prompt whenever a new version is released — no manual file swapping needed.

**Step 3 · Usage:**

1. Open any Tencent Meeting recording page `https://meeting.tencent.com/crm/xxx`
2. A **Export Transcript / 导出逐字稿** dropdown appears right after the native "Save as" button in the toolbar
3. Click it to choose format:
   - Text (.txt)
   - Markdown (.md)
   - TXT + Markdown
4. Wait for scrolling to finish — files auto-download

The button label auto-follows the Tencent Meeting UI language. Password-protected pages and unauthenticated views do not show the button.

> \[!TIP\]
>
> If the default fast mode misses entries, click the Tampermonkey extension icon in your browser toolbar and toggle **Safe mode** from the script menu. Each export option will then show a `(Safe mode)` suffix; toggle again to return to the default.

### Option 2: Browser Console (one-shot)

1. Open the recording page in a logged-in browser; make sure the Transcription panel is expanded
2. Open DevTools Console (<kbd>Cmd</kbd>+<kbd>Option</kbd>+<kbd>J</kbd> or <kbd>F12</kbd>)
3. On first paste, Chrome may show a security warning — type `allow pasting` and press Enter
4. Paste the full contents of [`tencent_meeting_transcript.js`][console-script-link] and press Enter
5. Wait for scrolling to finish — TXT and Markdown files auto-download

> \[!NOTE\]
>
> No extension required, but you need to paste the code each time. Best for occasional use.

> \[!TIP\]
>
> If the result seems incomplete, run `window.TM_SAFE = true;` in the console **before** pasting the script — this switches to the slower-but-thorough capture mode.

### Option 3: Python CLI (unattended / automation)

- Python >= 3.10
- Run with [`uv`](https://docs.astral.sh/uv/) — it handles dependencies automatically
- **Reuses your system-installed Google Chrome or Microsoft Edge** instead of downloading Playwright's bundled Chromium
- **Persistent login profile** at `~/.tencent-meeting-transcript/chrome-profile` — log in once, subsequent runs reuse cookies
- **Works on macOS / Linux / Windows** — `--output` expands `~` and environment variables such as `$HOME` / `%USERPROFILE%`

**Simplest usage:**

```bash
uv run tencent_meeting_transcript.py https://meeting.tencent.com/crm/xxxxxx
```

Default is a single **TXT** file in the current directory. The filename preserves the recording's original title, e.g. `Today's Meeting - 逐字稿.txt`.

**Common flags:**

```bash
# Show all flags
uv run tencent_meeting_transcript.py --help

# Markdown only
uv run tencent_meeting_transcript.py <url> -f md

# TXT + Markdown + JSON (any combination)
uv run tencent_meeting_transcript.py <url> -f txt md json

# Same thing, shorthand
uv run tencent_meeting_transcript.py <url> -f all

# Custom output directory
uv run tencent_meeting_transcript.py <url> -o ~/Desktop

# Combined
uv run tencent_meeting_transcript.py <url> -f all -o ~/Desktop

# Slow but thorough safe mode — use if fast mode captures fewer entries than expected
uv run tencent_meeting_transcript.py <url> --safe

# Force the browser window to stay visible (debugging)
uv run tencent_meeting_transcript.py <url> --headed

# Force Chinese / English CLI output (default: auto-detect)
uv run tencent_meeting_transcript.py <url> -l en
```

> \[!TIP\]
>
> On **Windows PowerShell**, a desktop path can be written like this:
>
> ```powershell
> uv run tencent_meeting_transcript.py <url> -o "$env:USERPROFILE\Desktop"
> ```

**Full flag reference:**

| Flag | Short | Description | Default |
| --- | --- | --- | --- |
| `--format FMT [FMT …]` | `-f` | Output format(s), combinable: `txt` / `md` / `json` / `all` | `txt` |
| `--output DIR` | `-o` | Output directory (supports `~` and env vars) | current dir |
| `--safe` | `-s` | Slow & thorough mode (60% scroll + fixed 200 ms wait) | off |
| `--headed` | | Force the visible browser window | off |
| `--lang {auto,zh,en}` | `-l` | CLI output language | `auto` |
| `--version` | `-V` | Print version and exit | |
| `--help` | `-h` | Print help and exit | |

**Password-protected meeting flow:**

1. The script first hits the URL in headless mode
2. If a login / password page is detected, a visible Chrome window pops up
3. A yellow banner appears at the bottom: **"Please log in or enter the meeting password"**
4. You log in / enter the password in the window
5. The script polls every 300 ms, and as soon as it detects success it **minimises the window to the dock / taskbar** and keeps scraping in the background

After the first login, cookies are persisted to the profile so **subsequent runs need no interaction at all**.

**Browser launch order:** `chrome → msedge → Playwright-bundled Chromium`. As long as you have Chrome or Edge installed (most people do), it launches instantly and skips the 170 MB Chromium download.

> \[!TIP\]
>
> **Users in Mainland China**: if the fallback Chromium download ever triggers, use the npmmirror CDN to speed it up:
>
> ```bash
> PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright \
>   uv run tencent_meeting_transcript.py <url>
> ```
>
> Or just install [Google Chrome](https://www.google.com/chrome/) — all future Playwright scripts will reuse it.

<div align="right">

[![][back-to-top]](#readme-top)

</div>

## 📂 Output Formats

**Filename:** preserves the recording's original title verbatim, replacing filesystem-illegal characters and control characters with a dash so the result stays Windows-safe too, then appending ` - 逐字稿`. Example:

```
Original title: "Today's Meeting"
→ Output:      "Today's Meeting - 逐字稿.txt"
               "Today's Meeting - 逐字稿.md"
               "Today's Meeting - 逐字稿.json"
```

**Content in each format:**

- **TXT** — plain text, header with title / date / participants / entry count, followed by chronological `[time] speaker` blocks
- **Markdown** — structured doc with speaker-grouped headings and timestamps, ideal for pasting into note apps or further editing
- **JSON** (Python CLI only) — structured data with a `metadata` object and `entries` array, ready to feed into other tools (summarization, translation, search, etc.)

<div align="right">

[![][back-to-top]](#readme-top)

</div>

## 🌐 Multilingual Support

All three scripts auto-detect the Tencent Meeting UI language:

- **Chinese UI** — button reads `导出逐字稿`, menu reads `纯文本 (.txt) / Markdown (.md) / TXT + Markdown`
- **English UI** — button reads `Export Transcript`, menu reads `Text (.txt) / Markdown (.md) / TXT + Markdown`

Detection reads the native "Save as / 另存为" button's text directly, avoiding false positives from mixed-language strings in page text.

<div align="right">

[![][back-to-top]](#readme-top)

</div>

## 🔍 How It Works

Tencent Meeting transcripts use a virtualized list (only viewport-visible paragraphs are rendered), so a naive DOM read misses most of the content. All three scripts share the same core logic:

1. **Locate container** — find `.minutes-module-list` (the scrollable Transcription panel)
2. **Scroll-collect** — scroll down, then harvest each visible `[data-pid]` paragraph
3. **Dedupe & sort** — a `Map` keyed by `data-pid` eliminates duplicates, final list sorted by pid ascending
4. **Extract fields** — pull `speaker-name` / `p-start-time` / `paragraph-module_sentences` from each paragraph
5. **Format output** — render TXT / Markdown / JSON from templates

Fast mode is used by default. If the result does not match expectations, fall back to safe mode (see FAQ).

**The userscript additionally:**

- **Injects a native-looking button** — mirrors the DOM of the "Save as" dropdown using the same CSS Module classes (`met-dropdown saveas-btn saveas-btn_save-btn__Q5xVC header-btn-style_header-btn__msdow`), visually indistinguishable from the native buttons
- **Watches SPA navigation** — a `MutationObserver` keeps watching for toolbar remount so the button reappears after route changes

**The Python CLI additionally:**

- **Persistent profile** — `launch_persistent_context` caches cookies under `~/.tencent-meeting-transcript/chrome-profile`, so you only log in once
- **Headless ↔ Headed swap** — runs headless by default; when a login / password page is detected, it closes the headless context, reopens in headed mode so you can interact, and after success minimises the window via CDP (`Browser.setWindowBounds` with `windowState: minimized`). The context stays alive because Tencent's password session is bound to the window, not to cookies
- **Auto-proceed fast path** — if the saved password already exists, the headless run clicks the "Go to View" button directly, bypassing the visible window entirely
- **Permission-prompt suppression** — Chrome flags + init scripts neutralise `navigator.registerProtocolHandler` / `getInstalledRelatedApps` so Chrome never shows the "Access other apps and services" permission popup

<div align="right">

[![][back-to-top]](#readme-top)

</div>

## ❓ FAQ

<details>
<summary><kbd>Q: My recording link opens the Tencent Meeting desktop client — the button never shows up.</kbd></summary>

The scripts only run inside a **browser**. If you have the Tencent Meeting desktop client installed, clicking a recording link will open it in the client by default, and no userscript button is injected. Two workarounds:

1. **Right-click the link → Copy link, then paste it into a browser address bar manually**
2. Or inside the client's recording detail view, click the top-right **More** menu (⋯) → **Open file in browser**

From there, use the web version as usual and the button will appear in the toolbar.

</details>

<details>
<summary><kbd>Q: Does this work on phones / tablets?</kbd></summary>

No. Mobile browsers don't have Tampermonkey, don't expose a DevTools console, and the Python CLI needs a desktop browser — so the toolkit **only works on a desktop browser**. If you receive a recording link on your phone, forward it to your computer and export from there.

</details>

<details>
<summary><kbd>Q: I installed the userscript but the button still doesn't show up on the recording page.</kbd></summary>

Try these in order:

1. **Refresh the page** — a newly installed userscript does not apply to already-open tabs. Close and reopen, or press <kbd>Cmd</kbd>/<kbd>Ctrl</kbd>+<kbd>R</kbd>
2. **Check the Tampermonkey icon** — click it in the browser toolbar; verify `腾讯会议逐字稿导出` is listed as **enabled** (green toggle)
3. **Enable Developer mode** — Chrome 138+ requires toggling **Developer mode** ON at `chrome://extensions/`, otherwise no userscripts run at all
4. **Check the URL** — the script only injects on `meeting.tencent.com/cw/*` and `/crm/*`. Other Tencent Meeting routes will not trigger it
5. **Make sure you're logged in and can actually see the recording content** — password prompts, unauthenticated pages, and loading states do not show the button

</details>

<details>
<summary><kbd>Q: I can't find a "Transcription / 转写" panel on the page — there's nothing to export.</kbd></summary>

This means the meeting **did not have transcription enabled** when it was held, so Tencent Meeting only recorded video and audio, no text transcript. No tool can export a transcript that doesn't exist.

Next time, the host can enable **Live Transcription** from the meeting toolbar, or tick **Generate meeting minutes** in the recording settings — then the Transcription panel will be populated after the recording ends.

</details>

<details>
<summary><kbd>Q: Where are the exported files saved?</kbd></summary>

Same place your browser saves any other download — the default downloads folder (usually `~/Downloads` or "Downloads"). The Python CLI saves to the current working directory by default; use `-o` to override:

```bash
uv run tencent_meeting_transcript.py <url> -o ~/Desktop
```

</details>

<details>
<summary><kbd>Q: Is this safe? Does it upload my meeting content to any server?</kbd></summary>

**No.** All three scripts run 100% locally:

- **Userscript**: reads the current page's DOM in your own browser, generates files, and triggers browser downloads — no network requests to any third party
- **Console snippet**: same thing, runs only in your current browser tab
- **Python CLI**: launches a local Playwright-controlled browser, scrapes DOM, writes local files — no outbound calls either

The source code is fully open on GitHub — you can audit it yourself. If in doubt, read through `.user.js` (only a few hundred lines) and grep for `fetch` / `XMLHttpRequest` / `sendBeacon` to confirm there are no sneaky uploads.

</details>

<details>
<summary><kbd>Q: Does it cost anything?</kbd></summary>

**Completely free.** Licensed under MIT — use, modify, distribute, commercialize, whatever you want.

Note: whether the Tencent Meeting transcription feature itself is available depends on your account tier (some features may require a paid plan or enterprise subscription) — that's on Tencent's side and has nothing to do with this script. This tool only exports **transcripts that already exist**, it doesn't generate them from scratch.

</details>

<details>
<summary><kbd>Q: Can it handle really long meetings (3+ hours)? Will it be slow?</kbd></summary>

Yes, no length limit. Reference timings:

- **1-hour meeting** (~300 entries) ≈ **3 seconds**
- **3-hour meeting** (~900 entries) ≈ 8–10 seconds
- **Very long meetings** usually finish in under 20 seconds

With `--safe` / safe mode, expect roughly 4–5× these times.

Don't switch away from the tab during export (background tabs get JS throttled by the browser, which slows down scrolling). Just let the progress indicator finish.

</details>

<details>
<summary><kbd>Q: Why does the output have a few fewer entries than I expected?</kbd></summary>

Please **switch to safe mode** and export again:

| Script | How to switch |
| --- | --- |
| 🐍 Python CLI | Add the `--safe` or `-s` flag |
| 📋 Console snippet | Run `window.TM_SAFE = true;` in the console **before** pasting the script |
| 🖱️ Userscript | Click the Tampermonkey icon in the browser toolbar and toggle **Safe mode** from the script menu |

Safe mode uses a more conservative scrolling strategy, so it runs proportionally slower.

**Note:** Tencent Meeting's paragraph `pid` is not strictly sequential (some internal numbers are skipped), so "the count looks lower" can sometimes be a false impression.

</details>

<details>
<summary><kbd>Q: In Mainland China, the Python version's first run hangs downloading Chromium.</kbd></summary>

Normally it **should not** — the script prefers your system Chrome / Edge and skips the download entirely.

If you truly have no Chrome or Edge installed and the fallback triggers, use the npmmirror CDN to speed things up:

```bash
PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright \
  uv run tencent_meeting_transcript.py <url>
```

This mirror is maintained by the Taobao open-source team and usually runs at several MB/s, finishing in seconds.

**Easier approach**: just install [Google Chrome](https://www.google.com/chrome/). After that, the script launches instantly, no downloads needed, and all your future Playwright scripts get to reuse it too.

</details>

<details>
<summary><kbd>Q: I want to use AI to summarize the exported transcript — how?</kbd></summary>

Export the **Markdown format** — it preserves speaker headings and timestamps, so the AI can reference specific moments ("at 15:23 you mentioned X") with precision.

Then paste the whole `.md` into any AI chat tool (ChatGPT, Claude, Gemini, DeepSeek, Qwen, etc.) with a prompt like:

```
Below is a meeting transcript. Please:

1. Extract 3–5 core topics
2. List all decisions and action items (owner, deadline)
3. Highlight any open questions that need follow-up
4. Write an executive summary under 300 words

[paste .md content]
```

For very long meetings that exceed the model's context window, split into chunks, or use a long-context model like Claude or Gemini (200K+ tokens).

</details>

<div align="right">

[![][back-to-top]](#readme-top)

</div>

## 📝 License

Copyright © 2026-present [Babywbx][profile-link].<br/>
This project is [MIT](./LICENSE) licensed.

<!-- LINK GROUP -->

[back-to-top]: https://img.shields.io/badge/-BACK_TO_TOP-151515?style=flat-square
[github-contributors-link]: https://github.com/babywbx/Tencent-Meeting-Transcript-Exporter/graphs/contributors
[github-contributors-shield]: https://img.shields.io/github/contributors/babywbx/Tencent-Meeting-Transcript-Exporter?color=c4f042&labelColor=black&style=flat-square
[github-forks-link]: https://github.com/babywbx/Tencent-Meeting-Transcript-Exporter/network/members
[github-forks-shield]: https://img.shields.io/github/forks/babywbx/Tencent-Meeting-Transcript-Exporter?color=8ae8ff&labelColor=black&style=flat-square
[github-issues-link]: https://github.com/babywbx/Tencent-Meeting-Transcript-Exporter/issues
[github-issues-shield]: https://img.shields.io/github/issues/babywbx/Tencent-Meeting-Transcript-Exporter?color=ff80eb&labelColor=black&style=flat-square
[github-lastcommit-link]: https://github.com/babywbx/Tencent-Meeting-Transcript-Exporter/commits/main
[github-lastcommit-shield]: https://img.shields.io/github/last-commit/babywbx/Tencent-Meeting-Transcript-Exporter?labelColor=black&style=flat-square
[github-license-link]: https://github.com/babywbx/Tencent-Meeting-Transcript-Exporter/blob/main/LICENSE
[github-license-shield]: https://img.shields.io/github/license/babywbx/Tencent-Meeting-Transcript-Exporter?color=white&labelColor=black&style=flat-square
[github-release-link]: https://github.com/babywbx/Tencent-Meeting-Transcript-Exporter/releases
[github-stars-link]: https://github.com/babywbx/Tencent-Meeting-Transcript-Exporter/stargazers
[github-stars-shield]: https://img.shields.io/github/stars/babywbx/Tencent-Meeting-Transcript-Exporter?color=ffcb47&labelColor=black&style=flat-square
[profile-link]: https://github.com/babywbx
[tampermonkey-chrome-link]: https://chromewebstore.google.com/detail/tampermonkey/dhdgffkkebhmkfjojejmpbldmpobfkfo
[userscripts-safari-link]: https://apps.apple.com/app/userscripts/id1463298887
[userscript-install-link]: https://github.com/babywbx/Tencent-Meeting-Transcript-Exporter/raw/main/tencent_meeting_transcript.user.js
[console-script-link]: https://github.com/babywbx/Tencent-Meeting-Transcript-Exporter/blob/main/tencent_meeting_transcript.js
