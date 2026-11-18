(() => {
  const sidebar = document.querySelector(".app-sidebar");
  const toggle = document.querySelector(".sidebar-toggle");
  const glyph = document.querySelector(".toggle-glyph");
  const label = document.querySelector(".sidebar-toggle .nav-label");
  if (!sidebar || !toggle || !glyph) return;

  const setOpen = (open) => {
    document.body.classList.toggle("sidebar-open", open);
    toggle.setAttribute("aria-expanded", String(open));
    toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    glyph.textContent = open ? "‹" : "☰";
    if (label) label.textContent = open ? "Close menu" : "Open menu";
  };

  toggle.addEventListener("click", () => setOpen(!document.body.classList.contains("sidebar-open")));
  document.addEventListener("click", (event) => {
    if (document.body.classList.contains("sidebar-open") && !sidebar.contains(event.target)) setOpen(false);
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") setOpen(false);
  });
})();
