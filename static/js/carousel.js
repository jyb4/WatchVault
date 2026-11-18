(() => {
  document.querySelectorAll("[data-carousel]").forEach((carousel) => {
    const slides = [...carousel.querySelectorAll(".carousel-slide")];
    const dots = [...carousel.querySelectorAll(".carousel-dot")];
    if (slides.length < 2) return;
    let current = 0;
    const show = (index) => {
      current = (index + slides.length) % slides.length;
      slides.forEach((slide, slideIndex) => {
        const active = slideIndex === current;
        slide.classList.toggle("is-active", active);
        slide.setAttribute("aria-hidden", String(!active));
      });
      dots.forEach((dot, dotIndex) => dot.classList.toggle("is-active", dotIndex === current));
    };
    dots.forEach((dot, index) => dot.addEventListener("click", () => show(index)));
    setInterval(() => show(current + 1), 7000);
  });
})();
