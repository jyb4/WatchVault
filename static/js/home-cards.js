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
    const shift = (direction) => viewport.scrollBy({ left: direction * viewport.clientWidth * 0.88, behavior: "smooth" });
    rail.querySelector("[data-rail-prev]")?.addEventListener("click", () => shift(-1));
    rail.querySelector("[data-rail-next]")?.addEventListener("click", () => shift(1));
  });
})();
