// ==UserScript==
// @name         腾讯会议逐字稿导出
// @namespace    https://github.com/babywbx/Tencent-Meeting-Transcript-Exporter
// @version      1.0.0
// @description  Export Tencent Meeting transcripts as TXT / Markdown — native-looking dropdown injected next to "Save as"
// @author       Babywbx
// @homepage     https://github.com/babywbx/Tencent-Meeting-Transcript-Exporter
// @supportURL   https://github.com/babywbx/Tencent-Meeting-Transcript-Exporter/issues
// @updateURL    https://github.com/babywbx/Tencent-Meeting-Transcript-Exporter/raw/main/tencent_meeting_transcript.user.js
// @downloadURL  https://github.com/babywbx/Tencent-Meeting-Transcript-Exporter/raw/main/tencent_meeting_transcript.user.js
// @match        https://meeting.tencent.com/cw/*
// @match        https://meeting.tencent.com/crm/*
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_registerMenuCommand
// @grant        GM_unregisterMenuCommand
// @run-at       document-idle
// ==/UserScript==

(function () {
  "use strict";

  const BTN_ID = "tm-export-transcript-dropdown";
  const SAFE_MODE_KEY = "tm-export-transcript-safe-mode";
  const SAVE_AS_LABELS = new Set(["另存为", "Save as"]);
  const TRANSCRIPT_CONTAINER_SELECTOR = ".minutes-module-list";
  const TITLE_SELECTORS = ['[class*="title-with-edit"]', '[class*="recordTitle"]'];

  const STYLE_TEXT =
    `#${BTN_ID}{position:relative}` +
    `#${BTN_ID} .tm-popover{position:absolute;top:calc(100% + 4px);right:0;z-index:9999;min-width:180px;background:#fff;border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,.12),0 0 1px rgba(0,0,0,.08);padding:4px 0;opacity:0;visibility:hidden;transform:translateY(-4px);transform-origin:top right;transition:opacity .15s ease,transform .15s ease,visibility .15s linear .15s;pointer-events:none}` +
    `#${BTN_ID}.tm-open .tm-popover{opacity:1;visibility:visible;transform:translateY(0);pointer-events:auto;transition:opacity .15s ease,transform .15s ease,visibility 0s linear 0s}` +
    `#${BTN_ID} .tm-popover ul{list-style:none;margin:0;padding:0;max-height:none}` +
    `#${BTN_ID} .tm-popover li{padding:8px 16px;cursor:pointer;font-size:14px;line-height:20px;color:#1f1f1f;white-space:nowrap;transition:background-color .12s ease}` +
    `#${BTN_ID} .tm-popover li:hover{background-color:rgba(0,0,0,.04)}` +
    `#${BTN_ID} .tm-popover li:active{background-color:rgba(0,0,0,.08)}`;

  const hasGM =
    typeof GM_getValue === "function" && typeof GM_setValue === "function";
  let safeMode = hasGM ? GM_getValue(SAFE_MODE_KEY, false) : false;
  let menuCmdId = null;
  let openDropdown = null;
  let globalUiBound = false;
  let exporting = false;

  function detectLang() {
    const label = getVisibleText(findNativeSaveAsControl());
    if (label === "另存为") return "zh";
    if (label === "Save as") return "en";
    return (document.documentElement.lang || "").startsWith("zh") ? "zh" : "en";
  }

  const I18N = {
    en: {
      btnLabel: "Export Transcript",
      menuTxt: "Text (.txt)",
      menuMd: "Markdown (.md)",
      menuBoth: "TXT + Markdown",
      safeSuffix: " (Safe mode)",
      menuCmdOn: "✓ Safe mode: ON (slower, more reliable)",
      menuCmdOff: "Safe mode: OFF (fast, default)",
      working: "Exporting…",
      noContainer: "Transcript panel not found. Open Transcription first.",
      emptyTranscript: "No transcript found on this page.",
      transcriptionLabels: ["Transcription"],
    },
    zh: {
      btnLabel: "导出逐字稿",
      menuTxt: "纯文本 (.txt)",
      menuMd: "Markdown (.md)",
      menuBoth: "TXT + Markdown",
      safeSuffix: "（安全模式）",
      menuCmdOn: "✓ 安全模式：已开启（较慢，更稳）",
      menuCmdOff: "安全模式：已关闭（默认高速）",
      working: "导出中…",
      noContainer: "未找到转写面板,请先手动点开",
      emptyTranscript: "当前页面没有可导出的逐字稿内容",
      transcriptionLabels: ["转写", "Transcription"],
    },
  };

  // ---------- helpers ----------

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  function getVisibleText(el) {
    return (el?.innerText || el?.textContent || "").replace(/\s+/g, " ").trim();
  }

  function isVisible(el) {
    return Boolean(el && el.isConnected && el.offsetParent !== null);
  }

  function findToolbarContainer() {
    return document.querySelector(".buttons-container");
  }

  function findNativeSaveAsControl() {
    const container = findToolbarContainer();
    if (!container) return null;
    const controls = container.querySelectorAll("button, .met-dropdown, .met-dropdown__header");
    for (const el of controls) {
      if (!isVisible(el)) continue;
      if (SAVE_AS_LABELS.has(getVisibleText(el))) return el;
    }
    const iconHost = container.querySelector('[aria-label*="file-save"], [class*="file-save"]');
    return iconHost?.closest("button, .met-dropdown, .met-dropdown__header") || null;
  }

  function findDirectToolbarChild(container, node) {
    let cur = node;
    while (cur && cur.parentElement !== container) cur = cur.parentElement;
    return cur;
  }

  function download(filename, content) {
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.style.display = "none";
    document.body.append(a);
    a.click();
    setTimeout(() => {
      URL.revokeObjectURL(url);
      a.remove();
    }, 1000);
  }

  function findTranscriptContainer() {
    return document.querySelector(TRANSCRIPT_CONTAINER_SELECTOR);
  }

  function findTextTarget(labels, selectors) {
    for (const selector of selectors) {
      for (const el of document.querySelectorAll(selector)) {
        if (!isVisible(el)) continue;
        if (labels.includes(getVisibleText(el))) return el;
      }
    }
    return null;
  }

  function clickElement(el) {
    el.dispatchEvent(new MouseEvent("click", {
      bubbles: true,
      cancelable: true,
      view: window,
    }));
  }

  function getRecordingTitleText() {
    for (const selector of TITLE_SELECTORS) {
      for (const el of document.querySelectorAll(selector)) {
        const text = getVisibleText(el);
        if (text) return text;
      }
    }
    return "";
  }

  function makeFilename(title) {
    const safe =
      (title || "").replace(/[\\/:*?"<>|]/g, "-").replace(/\s+/g, " ").trim() ||
      "meeting";
    return `${safe} - 逐字稿`;
  }

  // ---------- transcript collection ----------

  async function ensureTranscriptionOpen(labels) {
    let container = findTranscriptContainer();
    if (container) return container;
    const toggle = findTextTarget(labels, [
      '[role="tab"]',
      ".met-tabs__tab",
      '[class*="tab-panel-tab"]',
      "button",
      "div",
      "span",
    ]);
    if (!toggle) return null;
    clickElement(toggle);
    for (let i = 0; i < 8; i++) {
      await sleep(250);
      container = findTranscriptContainer();
      if (container) return container;
    }
    return findTranscriptContainer();
  }

  async function collectAll(container, safe) {
    const transcript = new Map();

    function collectVisible() {
      for (const p of container.querySelectorAll('[class*="paragraph-module_paragraph"]')) {
        const pid = p.getAttribute("data-pid");
        if (!pid || transcript.has(pid)) continue;
        const speaker = p.querySelector('[class*="speaker-name"]')?.textContent?.trim() || "";
        const time = p.querySelector('[class*="p-start-time"]')?.textContent?.trim() || "";
        const text = p.querySelector('[class*="paragraph-module_sentences"]')?.textContent?.trim() || "";
        if (speaker || text) {
          transcript.set(pid, { pid: parseInt(pid), speaker, time, text });
        }
      }
    }

    function maxPid() {
      let max = -1;
      for (const n of container.querySelectorAll('[class*="paragraph-module_paragraph"]')) {
        const v = parseInt(n.getAttribute("data-pid") || "-1");
        if (v > max) max = v;
      }
      return max;
    }

    function waitForNewContent(prevMaxPid, maxMs) {
      return new Promise((resolve) => {
        let done = false;
        let timer = null;
        const finish = () => {
          if (done) return;
          done = true;
          if (timer !== null) clearTimeout(timer);
          obs.disconnect();
          resolve();
        };
        const obs = new MutationObserver(() => {
          if (maxPid() > prevMaxPid) finish();
        });
        obs.observe(container, { childList: true, subtree: true });
        timer = setTimeout(finish, maxMs);
        queueMicrotask(() => {
          if (maxPid() > prevMaxPid) finish();
        });
      });
    }

    const scrollFactor = safe ? 0.6 : 1.0;
    container.scrollTop = 0;
    await sleep(safe ? 500 : 300);

    let rounds = 0;
    while (rounds < 300) {
      collectVisible();
      const prevMax = safe ? 0 : maxPid();
      const prev = container.scrollTop;
      container.scrollTop += container.clientHeight * scrollFactor;
      if (safe) {
        await sleep(200);
      } else {
        await waitForNewContent(prevMax, 250);
      }
      if (Math.abs(container.scrollTop - prev) < 2) {
        collectVisible();
        break;
      }
      rounds++;
    }

    container.scrollTop = 0;
    return [...transcript.values()].sort((a, b) => a.pid - b.pid);
  }

  function getMeta() {
    const text = document.body.innerText;
    let title = getRecordingTitleText();
    if (!title) {
      const m = text.match(/(\d{4}\/\d{2}\/\d{2}\s+[^\n]+)/);
      title = m ? m[1].trim() : "meeting";
    }
    const dateMatch = text.match(/(\d{4}\/\d{2}\/\d{2}\s+\d{2}:\d{2})/);
    return {
      title,
      date: dateMatch ? dateMatch[1].trim() : "",
    };
  }

  // ---------- formatters ----------

  function formatTxt(meta, entries) {
    const lines = [
      `${meta.title} - 逐字稿`,
      `录制日期：${meta.date}`,
      `参与者：${meta.speakers.join("、")}`,
      `共 ${entries.length} 条记录`,
      "=".repeat(60),
      "",
    ];
    for (const e of entries) {
      lines.push(`[${e.time}] ${e.speaker}`);
      lines.push(e.text);
      lines.push("");
    }
    return lines.join("\n");
  }

  function formatMd(meta, entries) {
    const lines = [
      `# ${meta.title} - 逐字稿`,
      "",
      `- **录制日期**：${meta.date}`,
      `- **参与者**：${meta.speakers.join("、")}`,
      `- **记录条数**：${entries.length}`,
      "",
      "---",
      "",
    ];
    let cur = null;
    for (const e of entries) {
      if (e.speaker !== cur) {
        cur = e.speaker;
        lines.push(`### ${e.speaker}  \`${e.time}\``);
      } else {
        lines.push(`**\`${e.time}\`**`);
      }
      lines.push("");
      lines.push(e.text);
      lines.push("");
    }
    return lines.join("\n");
  }

  async function runExport(format, labelEl, t) {
    if (exporting) return;
    exporting = true;
    const original = labelEl.textContent;
    labelEl.textContent = t.working;
    try {
      const container = await ensureTranscriptionOpen(t.transcriptionLabels);
      if (!container) {
        alert(t.noContainer);
        return;
      }
      const safe = format.startsWith("safe-");
      const realFormat = safe ? format.slice(5) : format;
      let entries = await collectAll(container, safe);
      if (!entries.length && !safe) {
        entries = await collectAll(container, true);
      }
      if (!entries.length) {
        throw new Error(t.emptyTranscript);
      }
      const speakers = [...new Set(entries.map((e) => e.speaker).filter(Boolean))];
      const meta = { ...getMeta(), speakers };
      const base = makeFilename(meta.title);
      if (realFormat === "txt" || realFormat === "both") {
        download(`${base}.txt`, formatTxt(meta, entries));
      }
      if (realFormat === "md" || realFormat === "both") {
        download(`${base}.md`, formatMd(meta, entries));
      }
    } catch (err) {
      console.error("[transcript export]", err);
      alert(String(err?.message || err));
    } finally {
      labelEl.textContent = original;
      exporting = false;
    }
  }

  // ---------- UI ----------

  function ensureStyles() {
    if (document.getElementById("tm-export-transcript-styles")) return;
    const style = document.createElement("style");
    style.id = "tm-export-transcript-styles";
    style.textContent = STYLE_TEXT;
    document.head.append(style);
  }

  function bindGlobalUiListeners() {
    if (globalUiBound) return;
    globalUiBound = true;
    document.addEventListener("click", (e) => {
      if (openDropdown && !openDropdown.contains(e.target)) {
        openDropdown.classList.remove("tm-open");
        openDropdown.setAttribute("aria-expanded", "false");
        openDropdown = null;
      }
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && openDropdown) {
        openDropdown.classList.remove("tm-open");
        openDropdown.setAttribute("aria-expanded", "false");
        openDropdown = null;
      }
    });
  }

  function buildDropdown(t, nativeSaveAs) {
    ensureStyles();
    bindGlobalUiListeners();

    const trigger = document.createElement("div");
    trigger.className =
      "tm-trigger met-dropdown saveas-btn saveas-btn_save-btn__Q5xVC header-btn-style_header-btn__msdow";
    trigger.setAttribute("role", "button");
    trigger.tabIndex = 0;

    const header = document.createElement("div");
    header.className = "met-dropdown__header met-dropdown-icon";
    const value = document.createElement("div");
    value.className = "met-dropdown__value";

    const nativeIcon =
      (nativeSaveAs && nativeSaveAs.querySelector('[class*="met-icon-file-save"]')) ||
      document.querySelector('.saveas-btn [class*="met-icon-file-save"]');
    const icon = nativeIcon
      ? nativeIcon.cloneNode(true)
      : Object.assign(document.createElement("i"), {
          className: "met-icon met-icon-file-save--app--outlined",
        });

    const labelEl = document.createElement("span");
    labelEl.className = "met-dropdown-icon-text";
    labelEl.textContent = t.btnLabel;

    value.append(icon, labelEl);
    header.append(value);
    trigger.append(header);

    const wrap = document.createElement("div");
    wrap.id = BTN_ID;
    wrap.setAttribute("aria-expanded", "false");
    wrap.append(trigger);

    const popover = document.createElement("div");
    popover.className =
      "tm-popover met-dropdown-box header-drop-down-style_header-drop-down-style__hxwjG";
    const ul = document.createElement("ul");
    ul.className = "tea-list tea-list--option";

    const suffix = safeMode ? t.safeSuffix : "";
    const items = [
      { key: "txt", label: t.menuTxt + suffix },
      { key: "md", label: t.menuMd + suffix },
      { key: "both", label: t.menuBoth + suffix },
    ];
    for (const it of items) {
      const li = document.createElement("li");
      li.className = "tea-list__item";
      li.textContent = it.label;
      li.dataset.format = it.key;
      ul.append(li);
    }
    popover.append(ul);
    wrap.append(popover);

    const setOpen = (v) => {
      if (!v && openDropdown === wrap) openDropdown = null;
      if (v && openDropdown && openDropdown !== wrap) {
        openDropdown.classList.remove("tm-open");
        openDropdown.setAttribute("aria-expanded", "false");
      }
      wrap.classList.toggle("tm-open", v);
      wrap.setAttribute("aria-expanded", v ? "true" : "false");
      openDropdown = v ? wrap : null;
    };

    trigger.addEventListener(
      "click",
      (e) => {
        if (exporting) return;
        e.preventDefault();
        e.stopPropagation();
        setOpen(!wrap.classList.contains("tm-open"));
      },
      true
    );

    trigger.addEventListener("keydown", (e) => {
      if (exporting) return;
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        setOpen(!wrap.classList.contains("tm-open"));
      }
    });

    ul.addEventListener("click", (e) => {
      if (exporting) return;
      const li = e.target.closest("li[data-format]");
      if (!li) return;
      e.stopPropagation();
      setOpen(false);
      const fmt = safeMode ? `safe-${li.dataset.format}` : li.dataset.format;
      runExport(fmt, labelEl, t);
    });

    return wrap;
  }

  function tryInject() {
    if (document.getElementById(BTN_ID)) return;
    const container = findToolbarContainer();
    if (!container) return;
    const saveAs = findNativeSaveAsControl();
    if (!saveAs) return;
    const anchor = findDirectToolbarChild(container, saveAs);
    if (!anchor) return;
    anchor.after(buildDropdown(I18N[detectLang()], saveAs));
  }

  function refreshDropdown() {
    document.getElementById(BTN_ID)?.remove();
    tryInject();
  }

  function refreshMenuCommand() {
    if (typeof GM_registerMenuCommand !== "function") return;
    const t = I18N[detectLang()];
    const label = safeMode ? t.menuCmdOn : t.menuCmdOff;
    if (menuCmdId !== null && typeof GM_unregisterMenuCommand === "function") {
      try { GM_unregisterMenuCommand(menuCmdId); } catch (_) {}
    }
    menuCmdId = GM_registerMenuCommand(label, () => {
      safeMode = !safeMode;
      if (hasGM) GM_setValue(SAFE_MODE_KEY, safeMode);
      refreshMenuCommand();
      refreshDropdown();
    });
  }

  function boot() {
    refreshMenuCommand();
    tryInject();
    new MutationObserver(() => {
      if (!document.getElementById(BTN_ID)) tryInject();
    }).observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === "complete") {
    setTimeout(boot, 500);
  } else {
    window.addEventListener("load", () => setTimeout(boot, 500));
  }
})();
