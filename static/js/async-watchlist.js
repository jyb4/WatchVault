(() => {
  const announce = (message, isError = false) => {
    let notice = document.querySelector("[data-watchlist-notice]");
    if (!notice) {
      notice = document.createElement("p");
      notice.className = "watchlist-notice";
      notice.dataset.watchlistNotice = "";
      notice.setAttribute("role", "status");
      document.body.append(notice);
    }
    notice.textContent = message;
    notice.classList.toggle("is-error", isError);
    notice.classList.add("is-visible");
    window.clearTimeout(notice.dismissTimer);
    notice.dismissTimer = window.setTimeout(() => notice.classList.remove("is-visible"), 2600);
  };

  const updateDetail = (data) => {
    const summary = document.querySelector("[data-detail-progress]");
    if (!summary) return;
    const status = summary.querySelector("[data-detail-status]");
    const current = summary.querySelector("[data-detail-current]");
    if (status) status.textContent = `In your list · ${data.status_display}`;
    if (current) {
      current.hidden = !data.season;
      if (data.season) current.textContent = `Current: S${data.season} · E${data.episode}`;
    }
  };

  const updateEpisodeButtons = (data) => {
    document.querySelectorAll("[data-watchlist-action='episode-set']").forEach((form) => {
      const season = Number(form.querySelector("[name='season']")?.value);
      const episode = Number(form.querySelector("[name='episode']")?.value);
      const current = season === data.season && episode === data.episode;
      form.closest(".episode-card")?.classList.toggle("is-current", current);
      const button = form.querySelector("button");
      if (button) button.textContent = current ? "Current episode" : "Set as current";
    });
  };

  const updateTrackingCard = (form, data) => {
    const card = form.closest("[data-watchlist-card]");
    if (!card) return;
    if (data.status !== "watching") {
      if (card.closest(".my-list-grid")) {
        const heading = card.querySelector("[data-watchlist-heading]");
        const next = card.querySelector("[data-watchlist-next]");
        if (heading) heading.textContent = data.status_display;
        if (next) next.textContent = "This show is complete.";
        form.replaceWith(Object.assign(document.createElement("a"), {
          className: "up-next-choose",
          href: form.closest(".up-next-copy")?.querySelector("a")?.href || "#",
          textContent: "Browse episode guide",
        }));
      } else {
        card.classList.add("is-leaving");
        window.setTimeout(() => card.remove(), 220);
      }
      announce("Show marked completed.");
      return;
    }
    const heading = card.querySelector("[data-watchlist-heading]");
    const next = card.querySelector("[data-watchlist-next]");
    const count = card.querySelector("[data-watchlist-count]");
    const bar = card.querySelector("[data-watchlist-bar]");
    const button = form.querySelector("button");
    if (heading) heading.textContent = `S${data.season} · E${data.episode}${data.is_season_finale ? " · FINALE" : ""}`;
    if (next && data.episode_title) next.textContent = `Up next: “${data.episode_title}”`;
    if (count && data.season_episode_total) count.textContent = `${data.episode} / ${data.season_episode_total} eps`;
    if (bar) bar.style.width = `${data.progress_percent || 0}%`;
    if (button) button.textContent = `✓ Mark E${data.episode} watched`;
    announce("Progress saved.");
  };

  document.querySelectorAll("form[data-watchlist-action]").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = event.submitter || form.querySelector("button[type='submit']");
      if (!button || button.disabled) return;
      const originalLabel = button.textContent;
      button.disabled = true;
      button.textContent = "Saving…";
      try {
        const response = await fetch(form.action, {
          method: "POST",
          body: new FormData(form),
          credentials: "same-origin",
          headers: { Accept: "application/json", "X-Requested-With": "XMLHttpRequest" },
        });
        const data = await response.json().catch(() => null);
        if (!response.ok || !data) throw new Error(data?.detail || "We could not save that change.");
        const action = form.dataset.watchlistAction;
        if (action === "remove") {
          const card = form.closest("[data-watchlist-card]");
          card?.classList.add("is-leaving");
          window.setTimeout(() => card?.remove(), 220);
          announce("Removed from My List.");
        } else if (action === "add") {
          const summary = document.createElement("div");
          summary.className = "detail-progress-summary";
          summary.dataset.detailProgress = "";
          summary.innerHTML = `<span data-detail-status>In your list · ${data.status_display}</span><strong data-detail-current hidden></strong><a href="#episodes">Choose an episode</a>`;
          form.replaceWith(summary);
          announce("Added to My List.");
        } else if (action === "episode-set") {
          updateDetail(data);
          updateEpisodeButtons(data);
          announce("Current episode saved.");
        } else if (action === "mark-watched") {
          updateTrackingCard(form, data);
        }
        if (!["add", "remove"].includes(action) && document.contains(button)) button.disabled = false;
      } catch (error) {
        announce(error.message || "We could not save that change.", true);
        button.disabled = false;
        button.textContent = originalLabel;
      }
    });
  });
})();
