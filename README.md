<div align="center"><a name="readme-top"></a>

# Tencent Meeting Transcript Exporter

一键从腾讯会议录制页导出逐字稿为 TXT / Markdown / JSON 的工具集，<br/>
包含 Tampermonkey 油猴脚本、浏览器控制台脚本和 Python CLI 三种使用方式。

[English](./README.en.md) · [报告问题][github-issues-link] · [更新日志][github-release-link]

<!-- SHIELD GROUP -->

[![][github-stars-shield]][github-stars-link]
[![][github-forks-shield]][github-forks-link]
[![][github-issues-shield]][github-issues-link]
[![][github-license-shield]][github-license-link]<br/>
[![][github-contributors-shield]][github-contributors-link]
[![][github-lastcommit-shield]][github-lastcommit-link]

</div>

<details>
<summary><kbd>目录</kbd></summary>

#### TOC

- [✨ 特性](#-特性)
- [📦 三种使用方式](#-三种使用方式)
- [🚀 快速开始](#-快速开始)
  - [方式一：Tampermonkey 油猴脚本（一键按钮，推荐）](#方式一tampermonkey-油猴脚本一键按钮推荐)
  - [方式二：浏览器控制台（一次性）](#方式二浏览器控制台一次性)
  - [方式三：Python CLI（无人值守 / 自动化）](#方式三python-cli无人值守--自动化)
- [📂 输出格式](#-输出格式)
- [🌐 多语言支持](#-多语言支持)
- [🔍 工作原理](#-工作原理)
- [❓ FAQ](#-faq)
- [📝 许可证](#-许可证)

####

<br/>

</details>

## ✨ 特性

> \[!WARNING\]
>
> **最后测试时间：2026-04-15** · 脚本依赖腾讯会议当前的 DOM 结构（CSS Module 哈希类名、滚动容器选择器等）。如果腾讯会议更新了网页版，选择器可能失效 —— 届时按钮可能样式错乱或抓取不到数据。欢迎提 issue 或参考 [🔍 工作原理](#-工作原理) 小节自行更新选择器。

> \[!IMPORTANT\]
>
> **Star Us** — 你将第一时间收到 GitHub 的版本更新通知 \~ ⭐️

这个项目解决一个问题：**把腾讯会议录制页的逐字稿完整、可靠地导出为本地文件**。核心目标：

- **🎯 完整抓取** — 基于 `MutationObserver` 的自适应滚动，一句不漏
- **⚡️ 快** — 典型 1 小时会议（~327 条记录）**3 秒内**完成采集（比旧版快 5x）
- **📄 多格式** — TXT / Markdown / JSON 按需输出，可任意组合
- **🌐 多语言** — 自动识别腾讯会议 UI 语言（中文 / 英文）并同步切换输出
- **🖼️ 原生样式** — 油猴版按钮完美融入工具栏，和「另存为 / 翻译」视觉一致
- **🔒 纯本地** — 全程在浏览器或本地机器内完成，不上传任何数据到第三方
- **🔐 密码会议** — Python CLI 自动检测登录 / 密码页，弹出可见窗口让你登录，完成后自动最小化继续后台抓取
- **🎛️ 三种形态** — CLI / 控制台 / 油猴按钮，按使用场景自由选择

<div align="right">

[![][back-to-top]](#readme-top)

</div>

## 📦 三种使用方式

项目提供三种完成同一任务的工具，核心抓取逻辑一致，运行方式不同，按推荐程度排序：

| 工具 | 文件 | 适合场景 | 输出格式 |
| --- | --- | --- | --- |
| 🖱️ **油猴脚本**（⭐ 推荐） | `tencent_meeting_transcript.user.js` | 长期使用、想要一键按钮、原生视觉融入工具栏 | TXT / MD / 两者 |
| 📋 **控制台脚本** | `tencent_meeting_transcript.js` | 偶尔用一次、不想安装任何扩展 | TXT + MD |
| 🐍 **Python CLI** | `tencent_meeting_transcript.py` | 无人值守、批量处理、密码会议自动化 | TXT / MD / JSON 任意组合 |

> \[!TIP\]
>
> 大多数人装**油猴脚本**就够了 —— 装一次之后每个录制页面都会自动出现一个「导出逐字稿」按钮，一键导出。<br/>
> 偶尔用一次、不想装扩展：**控制台脚本**，粘贴即跑。<br/>
> 需要批量导出、无人值守、或接入其他流程：**Python CLI**。

<div align="right">

[![][back-to-top]](#readme-top)

</div>

## 🚀 快速开始

### 方式一：Tampermonkey 油猴脚本（一键按钮，推荐）

**第一步 · 安装 Tampermonkey 扩展：**

- Chrome / Edge / Arc / Brave：[Chrome 应用商店][tampermonkey-chrome-link]
- Safari：改用免费的 [Userscripts][userscripts-safari-link]

> \[!IMPORTANT\]
>
> Chrome 138+ 要求打开 `chrome://extensions/` → 右上角「**开发者模式**」开关，否则所有油猴脚本都无法运行。

**第二步 · 一键安装本脚本：**

装好 Tampermonkey 后，点下面的链接，浏览器会直接弹出 Tampermonkey 的安装确认页，点「**安装**」即可：

👉 **[点此一键安装最新版][userscript-install-link]** 👈

或者手动复制链接：

```
https://github.com/babywbx/Tencent-Meeting-Transcript-Exporter/raw/main/tencent_meeting_transcript.user.js
```

> \[!TIP\]
>
> 油猴会**自动检查这个链接的更新**，之后每次有新版本时你都会收到升级提示 —— 不用手动替换文件。

**第三步 · 使用：**

1. 打开任意腾讯会议录制页面 `https://meeting.tencent.com/crm/xxx`
2. 工具栏「另存为 / Save as」按钮右侧会出现一个「**导出逐字稿 / Export Transcript**」下拉按钮
3. 点击选择格式：
   - 纯文本 (.txt)
   - Markdown (.md)
   - TXT + Markdown
4. 等待滚动完成，文件自动下载

按钮会自动跟随腾讯会议的界面语言显示中文或英文文案；密码输入页和未登录页不会显示按钮。

> \[!TIP\]
>
> 如果默认的快速模式抓不全，可以在浏览器右上角点击 Tampermonkey 扩展图标，从脚本菜单中切换到「**安全模式**」。开启后，每个导出选项会带上「（安全模式）」后缀，再次点击即可恢复默认。

### 方式二：浏览器控制台（一次性）

1. 在浏览器里打开录制页面（已登录），确保右侧 Transcription 面板展开
2. 打开 DevTools 控制台（<kbd>Cmd</kbd>+<kbd>Option</kbd>+<kbd>J</kbd> 或 <kbd>F12</kbd>）
3. 首次粘贴代码时 Chrome 可能提示安全警告，按要求输入 `allow pasting` 后回车
4. 把 [`tencent_meeting_transcript.js`][console-script-link] 的完整内容粘贴进去并回车
5. 等待滚动完成，TXT 和 Markdown 会自动下载

> \[!NOTE\]
>
> 这个模式不需要安装任何扩展，但每次使用都要重新粘贴代码。适合偶尔用一次的场景。

> \[!TIP\]
>
> 如果抓到的条数比预期少，在粘贴脚本**之前**先在控制台运行一行 `window.TM_SAFE = true;`，然后再粘脚本 —— 这会切到更慢但更稳妥的采集模式。

### 方式三：Python CLI（无人值守 / 自动化）

- Python >= 3.10
- 使用 [`uv`](https://docs.astral.sh/uv/) 运行，自动管理依赖
- **自动复用系统已安装的 Google Chrome 或 Microsoft Edge**，不会强制下载 Playwright 自带的 Chromium
- **持久化登录 profile**（`~/.tencent-meeting-transcript/chrome-profile`）—— 第一次登录后，后续运行直接复用 cookies
- **支持 macOS / Linux / Windows** —— `--output` 会自动展开 `~` 和环境变量（如 `$HOME` / `%USERPROFILE%`）

**最简用法：**

```bash
uv run tencent_meeting_transcript.py https://meeting.tencent.com/crm/xxxxxx
```

默认导出 **TXT**（一个文件）到当前目录。文件名会沿用录制原标题，例如 `今日会议 - 逐字稿.txt`。

**常用参数：**

```bash
# 查看所有参数
uv run tencent_meeting_transcript.py --help

# 只导 Markdown
uv run tencent_meeting_transcript.py <url> -f md

# 同时导 TXT + Markdown + JSON（任意组合）
uv run tencent_meeting_transcript.py <url> -f txt md json

# 三种都要（等价于上一行）
uv run tencent_meeting_transcript.py <url> -f all

# 指定输出目录
uv run tencent_meeting_transcript.py <url> -o ~/Desktop

# 组合使用
uv run tencent_meeting_transcript.py <url> -f all -o ~/Desktop

# 慢速安全模式（如果快速模式抓到的条数比预期少，用它兜底）
uv run tencent_meeting_transcript.py <url> --safe

# 强制显示浏览器窗口（调试用）
uv run tencent_meeting_transcript.py <url> --headed

# 强制中文 / 英文 CLI 输出（默认自动检测）
uv run tencent_meeting_transcript.py <url> -l zh
```

> \[!TIP\]
>
> **Windows PowerShell** 可以直接这样写桌面路径：
>
> ```powershell
> uv run tencent_meeting_transcript.py <url> -o "$env:USERPROFILE\Desktop"
> ```

**完整参数表：**

| 参数 | 简写 | 说明 | 默认 |
| --- | --- | --- | --- |
| `--format FMT [FMT …]` | `-f` | 输出格式，可组合：`txt` / `md` / `json` / `all` | `txt` |
| `--output DIR` | `-o` | 输出目录（支持 `~` 和环境变量） | 当前目录 |
| `--safe` | `-s` | 慢速安全模式（60% 滚动 + 固定 200ms 等待） | 关闭 |
| `--headed` | | 强制可见浏览器窗口 | 关闭 |
| `--lang {auto,zh,en}` | `-l` | CLI 输出语言 | `auto` |
| `--version` | `-V` | 打印版本号并退出 | |
| `--help` | `-h` | 打印帮助信息并退出 | |

**密码会议的处理流程：**

1. 脚本先在后台（headless）访问 URL
2. 如果检测到登录 / 密码页，自动弹出一个可见的 Chrome 窗口
3. 页面底部出现黄色横幅 **「请登录或输入会议密码」**
4. 你在窗口里输入密码或登录
5. 脚本每 300 ms 检测一次，一旦通过就自动**把窗口最小化到 Dock / 任务栏**，继续后台抓取

首次登录后 cookies 会保存到持久化 profile，后续运行**完全不需要再登录**。

**浏览器启动顺序：** `chrome → msedge → Playwright 自带 Chromium`。只要系统里装了 Chrome 或 Edge（绝大多数人都有），就会直接复用，省掉 170 MB 下载。

> \[!TIP\]
>
> **中国大陆用户**：万一真的触发了 Chromium 下载，可以用 npmmirror 镜像加速：
>
> ```bash
> PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright \
>   uv run tencent_meeting_transcript.py <url>
> ```
>
> 或者直接装一个 [Google Chrome](https://www.google.com/chrome/)，以后所有 Playwright 脚本都能复用。

<div align="right">

[![][back-to-top]](#readme-top)

</div>

## 📂 输出格式

**文件名：** 沿用腾讯会议录制的原始标题，仅把 `/` 等文件系统非法字符和控制字符换成 `-`，并额外兼容 Windows 文件名规则，末尾加 ` - 逐字稿`。例子：

```
原始标题：  "今日会议"
→ 输出：    "今日会议 - 逐字稿.txt"
           "今日会议 - 逐字稿.md"
           "今日会议 - 逐字稿.json"
```

**三种格式的内容：**

- **TXT** — 纯文本，表头包含会议主题 / 日期 / 参与者 / 记录条数，正文按时间顺序的「[时间] 发言人 + 内容」
- **Markdown** — 结构化文档，发言人分段标题 + 时间戳，适合粘贴到笔记软件或二次编辑
- **JSON**（仅 Python CLI）— 结构化数据，包含 `metadata` 对象和 `entries` 数组，适合喂给其他工具做总结 / 翻译 / 检索等后处理

<div align="right">

[![][back-to-top]](#readme-top)

</div>

## 🌐 多语言支持

所有三个脚本都会自动识别腾讯会议的 UI 语言：

- **中文界面** — 按钮显示「导出逐字稿」，菜单项显示「纯文本 (.txt) / Markdown (.md) / TXT + Markdown」
- **英文界面** — 按钮显示「Export Transcript」，菜单项显示「Text (.txt) / Markdown (.md) / TXT + Markdown」

检测方式是直接读取原生「另存为 / Save as」按钮的文字内容，避免了从页面文本中搜索关键词时可能出现的误判。

<div align="right">

[![][back-to-top]](#readme-top)

</div>

## 🔍 工作原理

腾讯会议逐字稿使用虚拟列表渲染（只渲染视口内的段落），所以不能一次性读取全部内容。三个脚本核心逻辑一致：

1. **定位容器** — 查找 `.minutes-module-list`（Transcription 面板滚动容器）
2. **滚动收集** — 每轮向下滚动一段距离，抓取当前可见的 `[data-pid]` 段落
3. **去重排序** — 用 `Map` 按 `data-pid` 去重，最后按 pid 升序排列
4. **提取字段** — 从每个段落里拿 `speaker-name` / `p-start-time` / `paragraph-module_sentences`
5. **格式化输出** — 按 TXT / Markdown / JSON 模板生成文件

默认使用快速模式；若抓取结果不符合预期，可切换到安全模式兜底（详见 FAQ）。

**油猴版额外做的事：**

- **注入原生按钮** — 复用 `met-dropdown saveas-btn saveas-btn_save-btn__Q5xVC header-btn-style_header-btn__msdow` 类，DOM 结构镜像「另存为」按钮，视觉完全一致
- **SPA 路由监听** — 通过 `MutationObserver` 持续监听工具栏重挂载，保证 SPA 路由切换后按钮不会丢失

**Python CLI 额外做的事：**

- **持久化 profile** — `launch_persistent_context` 把 cookies 存到 `~/.tencent-meeting-transcript/chrome-profile`，首次登录后永久生效
- **Headless ↔ Headed 智能切换** — 默认后台跑，遇到登录 / 密码页自动关掉 headless 重开 headed，完成后通过 CDP 把窗口最小化到 Dock，继续在同一个 context 里后台抓取（因为密码会话是**绑定到窗口**的，关了就失效）
- **Auto-proceed fast path** — 如果 cookies 里已经有密码信息，headless 阶段直接尝试点击「Go to View」跳过可见窗口
- **多 API 权限屏蔽** — 通过 Chrome flag + 页面注入脚本屏蔽 `navigator.registerProtocolHandler` / `getInstalledRelatedApps` 等 API，避免 Chrome 弹出「是否允许访问其他应用」权限请求

<div align="right">

[![][back-to-top]](#readme-top)

</div>

## ❓ FAQ

<details>
<summary><kbd>Q：点开录制链接跳到腾讯会议客户端了，看不到按钮？</kbd></summary>

脚本只在**浏览器网页版**里运行。如果系统装了腾讯会议客户端，点链接默认会跳转到客户端打开，而客户端里不会有油猴按钮。两种解决办法：

1. **右键链接 → 复制链接，手动粘贴到浏览器地址栏打开**
2. 或者在客户端录制详情页里，点右上角「更多」菜单（⋯）→ 选「**通过浏览器打开文件**」

之后正常使用，按钮就会出现在网页工具栏上。

</details>

<details>
<summary><kbd>Q：手机 / 平板上能用吗？</kbd></summary>

不能。移动端浏览器没有 Tampermonkey 扩展，也打不开 DevTools 控制台，Python CLI 也依赖桌面浏览器 —— 所以这套工具**只能在电脑浏览器里用**。手机上收到录制链接，请转发到电脑上再导出。

</details>

<details>
<summary><kbd>Q：我装好了油猴脚本，但录制页面上没看到按钮？</kbd></summary>

按以下顺序排查：

1. **刷新一下页面** —— 新装的脚本不会对已经打开的标签页生效，关闭重开或 <kbd>Cmd</kbd>/<kbd>Ctrl</kbd>+<kbd>R</kbd> 刷新
2. **检查 Tampermonkey 图标** —— 右上角油猴图标点开，看「腾讯会议逐字稿导出」是否显示为**已启用**（绿色开关）
3. **检查开发者模式** —— Chrome 138+ 需要在 `chrome://extensions/` 右上角打开「**开发者模式**」开关，否则所有油猴脚本都不会运行
4. **检查网址** —— 只有 `meeting.tencent.com/cw/*` 和 `/crm/*` 下才会注入。如果你的链接是其他路径（比如直接进入会议），不会触发
5. **确认已登录且能看到录制内容** —— 密码页、未登录页、加载中的页面都不会显示按钮

</details>

<details>
<summary><kbd>Q：页面上根本找不到「转写 / Transcription」面板，也就没有逐字稿可以导？</kbd></summary>

这说明这场会议**当时没有开启转写功能**，腾讯会议只录制了视频和音频，没有生成文字。这种情况下任何工具都无法导出逐字稿（因为压根就不存在）。

下次开会时，发起人可以在会议控制栏里开启「实时转写」，或者在录制设置里勾选「同时生成会议纪要」，这样录制结束后 Transcription 面板里才会有内容。

</details>

<details>
<summary><kbd>Q：导出的文件保存在哪里？</kbd></summary>

和你平时下载其他文件的位置一样 —— 浏览器默认的下载目录（通常是 `~/Downloads` 或「下载」文件夹）。Python CLI 版默认存在运行脚本的当前目录，可以用 `-o` 参数指定其他位置：

```bash
uv run tencent_meeting_transcript.py <url> -o ~/Desktop
```

</details>

<details>
<summary><kbd>Q：这个脚本安全吗？会不会上传我的会议内容到外部服务器？</kbd></summary>

**不会。** 三个脚本都是纯本地运行：

- **油猴脚本**：只在你自己的浏览器里读取当前页面的 DOM，然后生成文件让浏览器下载，全程不发任何网络请求到第三方
- **控制台脚本**：同上，只在你当前打开的浏览器标签里运行
- **Python CLI**：用本地 Playwright 打开你的 Chrome，抓完内容写入本地文件，也不联外网

代码全部开源在 GitHub，任何人都可以自己审计。如果不放心，可以在安装前通读一遍 `.user.js` 文件 —— 只有三百多行，关键词搜一下 `fetch` / `XMLHttpRequest` / `sendBeacon` 就能确认没有偷偷上传。

</details>

<details>
<summary><kbd>Q：要付费吗？</kbd></summary>

**完全免费。** 本项目基于 MIT 许可证开源，你可以自由使用、修改、分发，甚至商用。

不过要注意：腾讯会议本身的「转写」功能是否可用取决于你的账号权限（部分功能可能需要会员或企业版），这是腾讯的事，和本脚本无关 —— 这个脚本只负责把**已经存在的逐字稿**导出，不会凭空生成。

</details>

<details>
<summary><kbd>Q：会议特别长（比如 3 小时以上）能导完吗？会不会很慢？</kbd></summary>

可以导完，没有长度上限。参考耗时：

- **1 小时会议**（约 300 条）≈ **3 秒**
- **3 小时会议**（约 900 条）≈ 8–10 秒
- **超长会议** 通常 20 秒内完成

如果使用 `--safe` / 安全模式，耗时大约为上述值的 4–5 倍。

导出过程中不要切走标签页（否则浏览器会降低后台页面的 JS 执行频率，影响滚动速度），耐心等进度条走完就行。

</details>

<details>
<summary><kbd>Q：为什么导出的条数好像少了几条？</kbd></summary>

请**切换到安全模式**后重新导出：

| 脚本 | 切换方式 |
| --- | --- |
| 🐍 Python CLI | 添加 `--safe` 或 `-s` 参数 |
| 📋 控制台脚本 | 粘贴脚本前，先在控制台执行 `window.TM_SAFE = true;` |
| 🖱️ 油猴脚本 | 点击浏览器工具栏中的 Tampermonkey 图标，在脚本菜单里切换「**安全模式**」 |

安全模式采用更保守的滚动策略，速度会相应降低。

**附注：** 腾讯会议的段落 `pid` 本身并非严格连续（内部会跳过部分编号），因此"条数似乎变少"有时只是错觉。

</details>

<details>
<summary><kbd>Q：在中国大陆运行 Python 版，首次启动卡在下载 Chromium 动不了？</kbd></summary>

正常情况下**不应该**发生 —— 脚本会优先用系统已经装好的 Chrome 或 Edge，完全跳过下载。

如果你确实没装 Chrome 也没装 Edge 需要回落下载 Chromium，加一个环境变量走 npmmirror 镜像：

```bash
PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright \
  uv run tencent_meeting_transcript.py <url>
```

这个镜像是淘宝开源镜像站维护的，速度一般在几 MB/s，几秒到几十秒就能下完。

**更省事的做法**：直接装一个 [Google Chrome](https://www.google.com/chrome/)，装完以后脚本秒启动，不用下载任何东西，以后所有 Playwright 脚本也能复用。

</details>

<details>
<summary><kbd>Q：导出之后想让 AI 帮我做会议总结，怎么用？</kbd></summary>

推荐导出 **Markdown 格式** —— 因为 Markdown 保留了发言人分段和时间戳，AI 做总结时可以精确引用某个片段（「在 15:23 你提到了 X」）。

然后把整个 `.md` 文件内容复制，贴给任意 AI 聊天工具（ChatGPT、Claude、Gemini、DeepSeek、通义千问等），配合提示词，例如：

```
以下是一份会议逐字稿，请帮我做以下事情：

1. 提炼 3-5 个核心议题
2. 列出所有达成的决定和行动项（谁负责、什么时候前）
3. 标记出所有需要后续跟进的遗留问题
4. 用 300 字以内生成一个执行摘要

[粘贴 .md 内容]
```

如果会议很长超出了 AI 的上下文窗口，可以分段贴，或者用 Claude / Gemini 这种长上下文模型（200K+ token）。

</details>

<div align="right">

[![][back-to-top]](#readme-top)

</div>

## 📝 许可证

Copyright © 2026-present [Babywbx][profile-link].<br/>
本项目基于 [MIT](./LICENSE) 许可证发布。

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
