(() => {
  document.querySelectorAll("[data-poster-image]").forEach((image) => {
    const showFallback = () => {
      image.classList.add("is-hidden");
      image.parentElement?.querySelector("[data-poster-fallback]")?.classList.remove("is-hidden");
    };
    image.addEventListener("error", showFallback, { once: true });
    if (image.complete && !image.naturalWidth) showFallback();
  });

  document.querySelectorAll("[data-card-rail]").forEach((rail) => {
    const viewport = rail.querySelector("[data-rail-viewport]");
    if (!viewport) return;
    const previous = rail.querySelector("[data-rail-prev]");
    const next = rail.querySelector("[data-rail-next]");
    const shift = (direction) => viewport.scrollBy({ left: direction * viewport.clientWidth * 0.88, behavior: "smooth" });
    previous?.addEventListener("click", () => shift(-1));
    next?.addEventListener("click", () => shift(1));
    const updateArrows = () => {
      const canScroll = viewport.scrollWidth > viewport.clientWidth + 1;
      [previous, next].forEach((arrow) => { if (arrow) arrow.hidden = !canScroll; });
    };
    updateArrows();
    new ResizeObserver(updateArrows).observe(viewport);
  });
})();
