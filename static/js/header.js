(() => {
  const header = document.querySelector("[data-header]");
  if (!header) return;
  const updateHeader = () => header.classList.toggle("is-solid", window.scrollY > 24);
  updateHeader();
  window.addEventListener("scroll", updateHeader, { passive: true });
})();
