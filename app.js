
document.addEventListener("DOMContentLoaded", () => {
  const API = "https://podverse-ai-studio.onrender.com";

  const fileInput = document.querySelector('input[type="file"]');
  const urlInput = document.querySelector('input[type="url"]');
  const button = document.querySelector("button");
  const status = document.getElementById("status");

  if (!button || !urlInput || !status) {
    console.error("PodVerse: Required HTML elements not found.");
    return;
  }

  let selectedClips = [];

  let results = document.getElementById("clip-results");

  if (!results) {
    results = document.createElement("div");
    results.id = "clip-results";
    results.style.cssText =
      "margin-top:24px;color:white;line-height:1.6;";
    status.insertAdjacentElement("afterend", results);
  }

  const getNumber = (selectors, fallback) => {
    for (const selector of selectors) {
      const element = document.querySelector(selector);
      if (element && element.value) {
        const value = Number(element.value);
        if (Number.isFinite(value) && value > 0) return value;
      }
    }
    return fallback;
  };

  button.addEventListener("click", async (event) => {
    event.preventDefault();

    const url = urlInput.value.trim();
    const platforms = [
      ...document.querySelectorAll(".platform input:checked")
    ].map(item => item.value);

    if (!url) {
      status.textContent = "Please enter a YouTube link.";
      return;
    }

    if (platforms.length === 0) {
      status.textContent = "Please select at least one platform.";
      return;
    }

    status.textContent = "Step 1/3: Extracting YouTube transcript...";
    results.innerHTML = "";
    button.disabled = true;

    try {
      const transcriptResponse = await fetch(`${API}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url })
      });

      const transcriptData = await transcriptResponse.json();

      if (!transcriptResponse.ok || !transcriptData.success) {
        throw new Error(
          transcriptData.detail ||
          transcriptData.message ||
          "Transcript could not be extracted."
        );
      }

      const rawSegments =
        transcriptData.transcript_segments ||
        transcriptData.segments ||
        transcriptData.transcript ||
        [];

      const segments = rawSegments.map(segment => ({
        start: Number(segment.start || 0),
        end: Number(
          segment.end ??
          (Number(segment.start || 0) + Number(segment.duration || 0))
        ),
        text: String(segment.text || "")
      })).filter(segment =>
        segment.end > segment.start && segment.text.trim()
      );

      if (!segments.length) {
        throw new Error("No usable transcript segments were found.");
      }

      status.textContent =
        "Step 2/3: AI is finding the best podcast moments...";

      const duration = getNumber(
        ['#duration', '[name="duration"]', 'select[name="clipDuration"]'],
        60
      );

      const count = getNumber(
        ['#count', '[name="count"]', 'select[name="clipCount"]'],
        3
      );

      const aiResponse = await fetch(`${API}/analyze-semantic`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          segments,
          duration,
          count
        })
      });

      const aiData = await aiResponse.json();

      if (!aiResponse.ok || !aiData.success) {
        throw new Error(
          typeof aiData.detail === "string"
            ? aiData.detail
            : JSON.stringify(aiData.detail || aiData)
        );
      }

      selectedClips = aiData.clips || [];

      if (!selectedClips.length) {
        throw new Error("AI could not find suitable clips. Try another video.");
      }

      status.textContent =
        `Step 3/3: AI found ${selectedClips.length} potential clips.`;

      results.innerHTML = `
        <h2>AI Selected Podcast Clips</h2>
        <p>Selected platforms: ${platforms.join(", ")}</p>
        ${selectedClips.map((clip, index) => `
          <div style="
            background:#20232d;
            padding:16px;
            margin:12px 0;
            border-radius:12px;
          ">
            <h3>${index + 1}. ${escapeHTML(clip.hook)}</h3>
            <p>${escapeHTML(clip.reason)}</p>
            <p><strong>Start:</strong> ${formatTime(clip.start)}
            &nbsp; <strong>End:</strong> ${formatTime(clip.end)}
            &nbsp; <strong>Duration:</strong> ${clip.duration}s</p>
            <p>${escapeHTML(clip.text)}</p>
          </div>
        `).join("")}
      `;

    } catch (error) {
      console.error(error);
      status.textContent = `Error: ${error.message}`;
    } finally {
      button.disabled = false;
    }
  });

  function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, char => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;"
    })[char]);
  }

  function formatTime(seconds) {
    const value = Math.max(0, Math.floor(Number(seconds) || 0));
    return `${Math.floor(value / 60)}:${String(value % 60).padStart(2, "0")}`;
  }
});
