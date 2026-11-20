(() => {
  const dock = document.querySelector("[data-v2-dock]");
  if (!dock) return;
  const reset = () => { dock.style.removeProperty("--dock-x"); dock.style.removeProperty("--dock-y"); localStorage.removeItem("watchvault-v2-dock"); };
  const saved = localStorage.getItem("watchvault-v2-dock");
  if (saved) { try { const { x, y } = JSON.parse(saved); dock.style.setProperty("--dock-x", `${x}px`); dock.style.setProperty("--dock-y", `${y}px`); } catch (_) { reset(); } }
  let start;
  dock.addEventListener("pointerdown", (event) => { if (event.target.closest("a,button")) return; start = { x:event.clientX, y:event.clientY, left:dock.offsetLeft, top:dock.offsetTop }; dock.setPointerCapture(event.pointerId); });
  dock.addEventListener("pointermove", (event) => { if (!start) return; const x = Math.max(12, Math.min(window.innerWidth - dock.offsetWidth - 12, start.left + event.clientX - start.x)); const y = Math.max(82, Math.min(window.innerHeight - dock.offsetHeight - 12, start.top + event.clientY - start.y)); dock.style.left = `${x}px`; dock.style.top = `${y}px`; dock.style.transform = "rotate(-2deg)"; localStorage.setItem("watchvault-v2-dock", JSON.stringify({x,y})); });
  dock.addEventListener("pointerup", () => { start = null; });
  document.querySelector("[data-v2-dock-reset]")?.addEventListener("click", reset);
})();
