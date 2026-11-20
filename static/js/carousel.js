(() => {
  document.querySelectorAll("[data-carousel]").forEach((carousel) => {
    const slides = [...carousel.querySelectorAll(".hero-slide")];
    const dots = [...carousel.querySelectorAll(".carousel-dot")];
    if (slides.length < 2) return;

    let current = Math.max(0, slides.findIndex((slide) => slide.classList.contains("is-active")));
    let rotationTimer;

    const show = (index) => {
      current = (index + slides.length) % slides.length;
      slides.forEach((slide, slideIndex) => {
        const active = slideIndex === current;
        slide.classList.toggle("is-active", active);
        slide.setAttribute("aria-hidden", String(!active));
      });
      dots.forEach((dot, dotIndex) => dot.classList.toggle("is-active", dotIndex === current));
    };

    const stopRotation = () => window.clearInterval(rotationTimer);
    const startRotation = () => {
      stopRotation();
      rotationTimer = window.setInterval(() => show(current + 1), 7000);
    };

    dots.forEach((dot, index) => {
      dot.addEventListener("click", () => {
        show(index);
        startRotation();
      });
    });

    carousel.querySelector("[data-carousel-prev]")?.addEventListener("click", () => {
      show(current - 1);
      startRotation();
    });
    carousel.querySelector("[data-carousel-next]")?.addEventListener("click", () => {
      show(current + 1);
      startRotation();
    });

    let swipeStart = null;
    carousel.addEventListener("pointerdown", (event) => {
      if (event.target.closest("button, a")) return;
      swipeStart = event.clientX;
    });
    carousel.addEventListener("pointerup", (event) => {
      if (swipeStart === null) return;
      const distance = event.clientX - swipeStart;
      swipeStart = null;
      if (Math.abs(distance) < 50) return;
      show(current + (distance < 0 ? 1 : -1));
      startRotation();
    });

    carousel.addEventListener("mouseenter", stopRotation);
    carousel.addEventListener("mouseleave", startRotation);
    carousel.addEventListener("focusin", stopRotation);
    carousel.addEventListener("focusout", (event) => {
      if (!carousel.contains(event.relatedTarget)) startRotation();
    });

    document.addEventListener("visibilitychange", () => {
      if (document.hidden) stopRotation();
      else startRotation();
    });

    show(current);
    startRotation();
  });
})();
