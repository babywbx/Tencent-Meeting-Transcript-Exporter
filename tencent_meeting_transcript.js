/**
 * Tencent Meeting Transcript Exporter — one-shot DevTools console script.
 * Paste this into the Console of an open recording page; it auto-downloads
 * TXT and Markdown. For unattended CLI use the Python version; for a
 * one-click toolbar button use the userscript version.
 *
 * Version: 1.0.0
 * Author:  Babywbx
 * Repo:    https://github.com/babywbx/Tencent-Meeting-Transcript-Exporter
 *
 * Usage:
 *   1. Open the recording page (https://meeting.tencent.com/crm/xxx)
 *   2. Open DevTools Console (Cmd+Option+J / F12)
 *   3. Paste this entire script and press Enter
 *   4. Wait for scrolling to finish — files auto-download
 */

(async () => {
  // -- helpers --
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const TRANSCRIPTION_LABELS = new Set(["转写", "Transcription"]);

  function getVisibleText(el) {
    return (el?.innerText || el?.textContent || "").replace(/\s+/g, " ").trim();
  }

  function download(filename, content) {
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  // -- 1. ensure Transcription panel is open --
  let container = document.querySelector(".minutes-module-list");
  if (!container) {
    console.log("[1/4] Opening transcription panel ...");
    const btn = [...document.querySelectorAll("button, div, span")].find(
      (el) =>
        el.offsetParent !== null && TRANSCRIPTION_LABELS.has(getVisibleText(el))
    );
    if (btn) {
      btn.click();
      await sleep(1500);
      container = document.querySelector(".minutes-module-list");
    }
  }

  if (!container) {
    console.error("❌ Cannot find transcription panel. Make sure it is visible on the page.");
    return;
  }
  console.log("[1/4] Transcription panel found.");

  // -- 2. extract metadata --
  console.log("[2/4] Extracting metadata ...");
  const bodyText = document.body.innerText;
  // Prefer the dedicated title-with-edit div; fall back to body regex.
  const titleEl = document.querySelector('[class*="title-with-edit"]');
  let title = titleEl ? (titleEl.textContent || "").trim() : "";
  if (!title) {
    const titleMatch = bodyText.match(/(\d{4}\/\d{2}\/\d{2}\s+[^\n]+)/);
    title = titleMatch ? titleMatch[1].trim() : "meeting";
  }
  const dateMatch = bodyText.match(/(\d{4}\/\d{2}\/\d{2}\s+\d{2}:\d{2})/);
  const date = dateMatch ? dateMatch[1].trim() : "";

  // -- 3. scroll & collect --
  // Set `window.TM_SAFE = true` before running to force slow/thorough mode.
  const safe = !!window.TM_SAFE;
  console.log(`[3/4] Scrolling & collecting (${safe ? "safe" : "fast"} mode) ...`);
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

  // Adaptive wait: resolve as soon as a new paragraph appears.
  function waitForNewContent(prevMaxPid, maxMs) {
    return new Promise((resolve) => {
      let done = false;
      let timer = 0;
      let probeTimer = 0;
      let obs = null;
      const finish = () => {
        if (done) return;
        done = true;
        clearTimeout(timer);
        clearTimeout(probeTimer);
        obs?.disconnect();
        resolve(maxPid() > prevMaxPid);
      };
      timer = setTimeout(finish, maxMs);
      obs = new MutationObserver(() => {
        if (maxPid() > prevMaxPid) finish();
      });
      obs.observe(container, { childList: true, subtree: true });
      probeTimer = setTimeout(() => {
        if (maxPid() > prevMaxPid) finish();
      }, 15);
    });
  }

  const scrollFactor = safe ? 0.6 : 1.0;
  container.scrollTop = 0;
  await sleep(safe ? 500 : 300);

  let rounds = 0;
  let stagnantRounds = 0;
  while (rounds < 300) {
    collectVisible();
    const prevMax = maxPid();
    const prev = container.scrollTop;
    container.scrollTop += container.clientHeight * scrollFactor;
    let sawNewContent = false;
    if (safe) {
      await sleep(200);
      sawNewContent = maxPid() > prevMax;
    } else {
      sawNewContent = await waitForNewContent(prevMax, 250);
    }
    collectVisible();
    if (Math.abs(container.scrollTop - prev) < 2) {
      if (sawNewContent) {
        stagnantRounds = 0;
        continue;
      }
      if (!safe && !sawNewContent && stagnantRounds < 1) {
        stagnantRounds++;
        await sleep(250);
        continue;
      }
      break;
    }
    stagnantRounds = 0;
    rounds++;
  }

  const entries = [...transcript.values()].sort((a, b) => a.pid - b.pid);
  const speakers = [...new Set(entries.map((e) => e.speaker).filter(Boolean))];
  console.log(`  Collected ${entries.length} entries`);

  // -- 4. build & download files --
  console.log("[4/4] Generating files ...");

  // Preserve the recording's original title, only sanitising FS-illegal chars.
  const base = (title.replace(/[\\/:*?"<>|]/g, "-").replace(/\s+/g, " ").trim() || "meeting") + " - 逐字稿";

  // TXT
  const txtLines = [
    `${title} - 逐字稿`,
    `录制日期：${date}`,
    `参与者：${speakers.join("、")}`,
    `共 ${entries.length} 条记录`,
    "=".repeat(60),
    "",
  ];
  for (const e of entries) {
    txtLines.push(`[${e.time}] ${e.speaker}`);
    txtLines.push(e.text);
    txtLines.push("");
  }
  download(`${base}.txt`, txtLines.join("\n"));

  // MD
  const mdLines = [
    `# ${title} - 逐字稿`,
    "",
    `- **录制日期**：${date}`,
    `- **参与者**：${speakers.join("、")}`,
    `- **记录条数**：${entries.length}`,
    "",
    "---",
    "",
  ];
  let curSpeaker = null;
  for (const e of entries) {
    if (e.speaker !== curSpeaker) {
      curSpeaker = e.speaker;
      mdLines.push(`### ${e.speaker}  \`${e.time}\``);
    } else {
      mdLines.push(`**\`${e.time}\`**`);
    }
    mdLines.push("");
    mdLines.push(e.text);
    mdLines.push("");
  }
  download(`${base}.md`, mdLines.join("\n"));

  console.log(`✅ Done! Downloaded ${base}.txt and ${base}.md`);
})();
