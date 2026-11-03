/**
 * Interactive Scientific Image Lightbox & Zoom Viewer
 * Zero external dependencies. High performance pan, zoom, and fullscreen controls.
 */
document.addEventListener("DOMContentLoaded", function () {
  // Create Lightbox DOM elements
  const overlay = document.createElement("div");
  overlay.id = "sci-lightbox-overlay";
  overlay.innerHTML = `
    <div class="sci-lightbox-backdrop"></div>
    <div class="sci-lightbox-toolbar">
      <span class="sci-lightbox-title"></span>
      <div class="sci-lightbox-actions">
        <button id="sci-zoom-in" title="Zoom In (+)"><svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg></button>
        <button id="sci-zoom-out" title="Zoom Out (-)"><svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M19 13H5v-2h14v2z"/></svg></button>
        <button id="sci-zoom-reset" title="Reset View"><svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46A7.93 7.93 0 0 0 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74A7.93 7.93 0 0 0 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/></svg></button>
        <a id="sci-download" download title="Download High-Res File"><svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM17 13l-5 5-5-5h3V9h4v4h3z"/></svg></a>
        <button id="sci-close" title="Close (Esc)"><svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg></button>
      </div>
    </div>
    <div class="sci-lightbox-stage">
      <img id="sci-lightbox-img" alt="" />
    </div>
  `;
  document.body.appendChild(overlay);

  const imgEl = overlay.querySelector("#sci-lightbox-img");
  const titleEl = overlay.querySelector(".sci-lightbox-title");
  const downloadEl = overlay.querySelector("#sci-download");
  const stage = overlay.querySelector(".sci-lightbox-stage");

  let scale = 1;
  let posX = 0, posY = 0;
  let isDragging = false;
  let startX = 0, startY = 0;

  function updateTransform() {
    imgEl.style.transform = `translate(${posX}px, ${posY}px) scale(${scale})`;
  }

  function resetView() {
    scale = 1;
    posX = 0;
    posY = 0;
    updateTransform();
  }

  function openLightbox(src, alt) {
    imgEl.src = src;
    imgEl.alt = alt || "Scientific Visual";
    titleEl.textContent = alt || "Scientific Figure Inspection";
    downloadEl.href = src;
    resetView();
    overlay.classList.add("active");
    document.body.style.overflow = "hidden";
  }

  function closeLightbox() {
    overlay.classList.remove("active");
    document.body.style.overflow = "";
    imgEl.src = "";
  }

  // Bind clicks to all markdown content images
  function bindImages() {
    const images = document.querySelectorAll(".md-content img");
    images.forEach(img => {
      if (img.closest("#sci-lightbox-overlay")) return;
      img.classList.add("sci-zoomable");
      img.addEventListener("click", function (e) {
        e.preventDefault();
        openLightbox(this.src, this.alt || this.getAttribute("title"));
      });
    });
  }

  bindImages();

  // Toolbar actions
  overlay.querySelector("#sci-zoom-in").addEventListener("click", () => {
    scale = Math.min(scale * 1.3, 5);
    updateTransform();
  });
  overlay.querySelector("#sci-zoom-out").addEventListener("click", () => {
    scale = Math.max(scale / 1.3, 0.4);
    updateTransform();
  });
  overlay.querySelector("#sci-zoom-reset").addEventListener("click", resetView);
  overlay.querySelector("#sci-close").addEventListener("click", closeLightbox);
  overlay.querySelector(".sci-lightbox-backdrop").addEventListener("click", closeLightbox);

  // Keyboard navigation
  window.addEventListener("keydown", (e) => {
    if (!overlay.classList.contains("active")) return;
    if (e.key === "Escape") closeLightbox();
    else if (e.key === "+" || e.key === "=") { scale = Math.min(scale * 1.25, 5); updateTransform(); }
    else if (e.key === "-") { scale = Math.max(scale / 1.25, 0.4); updateTransform(); }
    else if (e.key === "0") resetView();
  });

  // Mouse wheel zoom
  stage.addEventListener("wheel", (e) => {
    e.preventDefault();
    const delta = e.deltaY < 0 ? 1.15 : 0.85;
    scale = Math.min(Math.max(scale * delta, 0.4), 6);
    updateTransform();
  }, { passive: false });

  // Drag and pan
  stage.addEventListener("mousedown", (e) => {
    if (e.target !== imgEl) return;
    isDragging = true;
    startX = e.clientX - posX;
    startY = e.clientY - posY;
    stage.style.cursor = "grabbing";
  });

  window.addEventListener("mousemove", (e) => {
    if (!isDragging) return;
    posX = e.clientX - startX;
    posY = e.clientY - startY;
    updateTransform();
  });

  window.addEventListener("mouseup", () => {
    isDragging = false;
    stage.style.cursor = "grab";
  });

  // Re-bind on instant navigation page changes
  if (window.document$) {
    window.document$.subscribe(bindImages);
  }
});

