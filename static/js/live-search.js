(() => {
  const dialog = document.querySelector("[data-search-dialog]");
  const input = document.querySelector("[data-live-search]");
  const results = document.querySelector("[data-live-results]");
  const status = document.querySelector("[data-search-status]");
  const open = document.querySelector("[data-search-open]");
  const close = document.querySelector("[data-search-close]");
  if (!dialog || !input || !results || !status || !open || !close) return;
  let externalTimer;
  let localController;
  let externalController;
  let localItems = [];
  let externalItems = [];
  let localLoading = false;
  let externalLoading = false;
  const localCache = new Map();
  const render = () => {
    const items = [...localItems, ...externalItems];
    results.replaceChildren();
    if (!items.length) {
      results.textContent = (localLoading || externalLoading) ? "Searching for shows…" : "No matching shows found.";
      return;
    }
    items.forEach((item, index) => {
      const link = document.createElement("a"); link.href = item.url; link.className = "live-result";
      if (item.source === "TVmaze") { link.target = "_blank"; link.rel = "noopener noreferrer"; }
      const rank = document.createElement("b"); rank.textContent = String(index + 1).padStart(2, "0");
      const image = document.createElement("img"); image.src = item.poster || ""; image.alt = item.poster ? `Poster for ${item.title}` : ""; image.loading = "lazy"; image.decoding = "async";
      const text = document.createElement("span"); const title = document.createElement("strong"); title.textContent = item.title; const meta = document.createElement("small"); meta.textContent = `${item.meta} · ${item.source}`; text.append(title, meta);
      const arrow = document.createElement("i"); arrow.textContent = "›"; link.append(rank, image, text, arrow); results.append(link);
    });
  };
  const loadLocal = async () => {
    const query = input.value.trim();
    if (localController) localController.abort(); localController = new AbortController();
    externalItems = [];
    localLoading = !localCache.has(query);
    if (localCache.has(query)) { localItems = localCache.get(query); render(); return; }
    localItems = [];
    render();
    try { const response = await fetch(`/api/local-search/?q=${encodeURIComponent(query)}`, { signal: localController.signal }); const data = await response.json(); if (input.value.trim() !== query) return; localItems = data.results; localCache.set(query, data.results); }
    catch (error) { if (error.name !== "AbortError") results.textContent = "Search is temporarily unavailable."; }
    finally { if (input.value.trim() === query) { localLoading = false; render(); } }
  };
  const loadExternal = async () => {
    const query = input.value.trim();
    if (query.length < 2) return;
    if (externalController) externalController.abort(); externalController = new AbortController();
    try { const response = await fetch(`/api/external-search/?q=${encodeURIComponent(query)}`, { signal: externalController.signal }); const data = await response.json(); if (input.value.trim() !== query) return; externalItems = data.results; status.textContent = `Search results for “${query}”`; }
    catch (error) { if (error.name !== "AbortError") status.textContent = "Showing WatchVault matches"; }
    finally { if (input.value.trim() === query) { externalLoading = false; render(); } }
  };
  const search = () => { clearTimeout(externalTimer); if (externalController) externalController.abort(); const query = input.value.trim(); externalLoading = query.length >= 2; status.textContent = query ? `Searching for “${query}”` : "Trending in WatchVault"; loadLocal(); externalTimer = setTimeout(loadExternal, 180); };
  const show = () => { dialog.showModal(); input.focus(); search(); };
  open.addEventListener("click", show); close.addEventListener("click", () => dialog.close());
  input.addEventListener("input", search);
  document.addEventListener("keydown", (event) => { if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") { event.preventDefault(); show(); } });
  dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
})();
