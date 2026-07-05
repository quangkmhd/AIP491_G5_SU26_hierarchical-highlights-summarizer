// app.js: streaming recap UI client.
// Connects to /api/v1/meetings/stream and renders chapter cards in place.

const API_BASE = window.__API_BASE__ || "http://localhost:8000";  // override via window.__API_BASE__ for tests

document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("transcript-input");
  const processBtn = document.getElementById("process-btn");
  const status = document.getElementById("status");
  const container = document.getElementById("chapters-container");

  // Clear placeholder if present
  function clearEmpty() {
    const empty = container.querySelector(".empty");
    if (empty) empty.remove();
  }

  function addChapterCard(segmentId) {
    clearEmpty();
    const card = document.createElement("div");
    card.className = "chapter-card";
    card.id = `chapter-${segmentId}`;
    card.dataset.segmentId = segmentId;
    card.innerHTML = `
      <div class="chapter-title">
        <span class="skeleton-bar" style="width: 60%"></span>
      </div>
      <div class="chapter-meta">
        <span class="skeleton-bar" style="width: 30%; height: 0.6rem"></span>
      </div>
      <ul class="chunk-list"></ul>
      <div class="chapter-actions">
        <button class="copy-btn">Copy</button>
        <button class="context-btn">Show Context</button>
      </div>
    `;
    container.appendChild(card);

    // Wire Copy button
    card.querySelector(".copy-btn").addEventListener("click", () => copyChapter(card));
    // Wire Show Context button (shows first 3 utt)
    card.querySelector(".context-btn").addEventListener("click", () => {
      const ctx = card.querySelector(".chunk-context");
      if (ctx) ctx.classList.toggle("visible");
    });

    return card;
  }

  function updateChapterTitle(segmentId, title) {
    const card = document.getElementById(`chapter-${segmentId}`);
    if (card) {
      const titleEl = card.querySelector(".chapter-title");
      titleEl.innerHTML = "";  // remove skeleton
      titleEl.textContent = title;
    }
  }

  function updateChapterMeta(segmentId, utterancesStart, utterancesEnd) {
    const card = document.getElementById(`chapter-${segmentId}`);
    if (card) {
      const metaEl = card.querySelector(".chapter-meta");
      metaEl.innerHTML = `Utterances ${utterancesStart}–${utterancesEnd} (${utterancesEnd - utterancesStart + 1} utt)`;
    }
  }

  function addChunkToChapter(segmentId, chunkId, startIdx, endIdx, summary) {
    const card = document.getElementById(`chapter-${segmentId}`);
    if (!card) return;
    const chunkList = card.querySelector(".chunk-list");
    const li = document.createElement("li");
    li.className = "chunk-item";
    li.dataset.chunkId = chunkId;
    li.dataset.start = startIdx;
    li.dataset.end = endIdx;
    li.textContent = summary || "(no summary yet)";
    li.title = `Chunk ${startIdx}–${endIdx} (click to expand context)`;
    li.addEventListener("click", () => toggleChunkContext(li, segmentId, chunkId, startIdx, endIdx));
    chunkList.appendChild(li);
  }

  function toggleChunkContext(li, segmentId, chunkId, startIdx, endIdx) {
    let ctx = li.querySelector(".chunk-context");
    if (ctx) {
      ctx.classList.toggle("visible");
      return;
    }
    ctx = document.createElement("div");
    ctx.className = "chunk-context";
    ctx.innerHTML = `<em>Showing context for chunk ${startIdx}–${endIdx} (up to 3 utt each side; populated on server expansion).</em>`;
    li.appendChild(ctx);
    ctx.classList.add("visible");
  }

  function copyChapter(card) {
    const title = card.querySelector(".chapter-title").textContent;
    const chunks = Array.from(card.querySelectorAll(".chunk-item")).map(li => li.textContent).join("\n");
    const text = `${title}\n\n${chunks}`;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).catch(err => console.warn("clipboard failed:", err));
    }
    // Visual feedback
    const btn = card.querySelector(".copy-btn");
    const orig = btn.textContent;
    btn.textContent = "Copied!";
    setTimeout(() => { btn.textContent = orig; }, 1200);
  }

  async function process() {
    const text = input.value.trim();
    if (!text) {
      status.textContent = "Please paste a transcript first.";
      return;
    }
    const flatTexts = text.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
    processBtn.disabled = true;
    status.textContent = "Processing…";
    status.className = "processing";
    container.innerHTML = "";  // clear
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "Streaming…";
    container.appendChild(empty);

    try {
      const resp = await fetch(`${API_BASE}/api/v1/meetings/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ flat_texts: flatTexts }),
      });
      if (!resp.ok) {
        status.textContent = `Error: ${resp.status}`;
        processBtn.disabled = false;
        return;
      }
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let eventCount = 0;
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        // Parse SSE events: "event: <type>\ndata: <json>\n\n"
        let idx;
        while ((idx = buffer.indexOf("\n\n")) >= 0) {
          const block = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          const lines = block.split("\n");
          let evtType = null, evtData = null;
          for (const line of lines) {
            if (line.startsWith("event: ")) evtType = line.slice(7).trim();
            else if (line.startsWith("data: ")) evtData = line.slice(6);
          }
          if (evtType === "end") {
            status.textContent = `Done. ${eventCount} events.`;
            processBtn.disabled = false;
            return;
          }
          if (evtType && evtData) {
            try {
              const data = JSON.parse(evtData);
              handleEvent(evtType, data);
              eventCount++;
            } catch (e) {
              console.warn("SSE parse error:", e, evtData);
            }
          }
        }
      }
    } catch (e) {
      status.textContent = `Network error: ${e.message}`;
      processBtn.disabled = false;
    }
  }

  function handleEvent(type, data) {
    switch (type) {
      case "segment-closed":
        addChapterCard(data.segment_id);
        updateChapterMeta(data.segment_id, data.utterances_start, data.utterances_end);
        break;
      case "title-emitted":
        updateChapterTitle(data.segment_id, data.title);
        break;
      case "chunk-closed":
        addChunkToChapter(
          data.segment_id, data.chunk_id,
          data.utterances_start, data.utterances_end,
          data.rolling_summary
        );
        break;
      case "utterance-accepted":
      case "depth-score-updated":
        // Informational; not rendered to keep UI minimal
        break;
      case "meeting-completed":
        // Final recap attached; could render a summary, but cards already
        // have everything we need.
        break;
      default:
        // Unknown event type; ignore
        break;
    }
  }

  processBtn.addEventListener("click", process);
});
