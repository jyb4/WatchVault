(() => {
  const dialog = document.querySelector("[data-search-dialog]");
  const input = document.querySelector("[data-live-search]");
  const results = document.querySelector("[data-live-results]");
  const status = document.querySelector("[data-search-status]");
  const open = document.querySelector("[data-search-open]");
  const close = document.querySelector("[data-search-close]");
  if (!dialog || !input || !results || !status || !open || !close) return;
  let timer;
  let controller;
  const render = (items) => {
    results.replaceChildren();
    if (!items.length) { results.textContent = "No matching shows found."; return; }
    items.forEach((item, index) => {
      const link = document.createElement("a"); link.href = item.url; link.className = "live-result";
      if (item.source === "TVmaze") { link.target = "_blank"; link.rel = "noopener noreferrer"; }
      const rank = document.createElement("b"); rank.textContent = String(index + 1).padStart(2, "0");
      const image = document.createElement("img"); image.src = item.poster || ""; image.alt = item.poster ? `Poster for ${item.title}` : "";
      const text = document.createElement("span"); const title = document.createElement("strong"); title.textContent = item.title; const meta = document.createElement("small"); meta.textContent = `${item.meta} · ${item.source}`; text.append(title, meta);
      const arrow = document.createElement("i"); arrow.textContent = "›"; link.append(rank, image, text, arrow); results.append(link);
    });
  };
  const load = async () => {
    const query = input.value.trim();
    if (controller) controller.abort(); controller = new AbortController(); status.textContent = query ? `Searching for “${query}”` : "Trending in WatchVault";
    try { const response = await fetch(`/api/live-search/?q=${encodeURIComponent(query)}`, { signal: controller.signal }); const data = await response.json(); render(data.results); }
    catch (error) { if (error.name !== "AbortError") results.textContent = "Search is temporarily unavailable."; }
  };
  const show = () => { dialog.showModal(); input.focus(); load(); };
  open.addEventListener("click", show); close.addEventListener("click", () => dialog.close());
  input.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(load, 250); });
  document.addEventListener("keydown", (event) => { if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") { event.preventDefault(); show(); } });
  dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
})();
