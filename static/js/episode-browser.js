(() => {
  document.querySelectorAll("[data-episode-browser]").forEach((browser) => {
    const tabs = browser.querySelectorAll("[data-season-tab]");
    const panels = browser.querySelectorAll("[data-season-panel]");
    const activate = (season) => {
      tabs.forEach((tab) => {
        const active = tab.dataset.seasonTab === season;
        tab.setAttribute("aria-selected", String(active));
        tab.tabIndex = active ? 0 : -1;
      });
      panels.forEach((panel) => { panel.hidden = panel.dataset.seasonPanel !== season; });
    };
    tabs.forEach((tab) => {
      tab.addEventListener("click", () => activate(tab.dataset.seasonTab));
      tab.addEventListener("keydown", (event) => {
        if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
        event.preventDefault();
        const index = Array.from(tabs).indexOf(tab);
        const next = (index + (event.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length;
        tabs[next].focus();
        activate(tabs[next].dataset.seasonTab);
      });
    });
  });
})();
