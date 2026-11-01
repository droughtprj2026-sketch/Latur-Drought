window.MathJax = {
  tex: {
    inlineMath: [["\\(", "\\)"], ["$", "$"]],
    displayMath: [["\\[", "\\]"], ["$$", "$$"]],
    processEscapes: true,
    processEnvironments: true
  },
  options: {
    ignoreHtmlClass: ".*|",
    processHtmlClass: "arithmatex"
  },
  startup: {
    ready: () => {
      MathJax.startup.defaultReady();
      MathJax.startup.promise.then(() => {
        renderMath();
      });
    }
  }
};

function renderMath() {
  if (typeof MathJax !== "undefined" && MathJax.typesetPromise) {
    if (MathJax.startup && MathJax.startup.output && MathJax.startup.output.clearCache) {
      try { MathJax.startup.output.clearCache(); } catch (e) {}
    }
    if (MathJax.typesetClear) {
      try { MathJax.typesetClear(); } catch (e) {}
    }
    if (MathJax.texReset) {
      try { MathJax.texReset(); } catch (e) {}
    }
    MathJax.typesetPromise().catch(function (err) {
      console.warn("MathJax typesetPromise warning:", err);
    });
  }
}

// Hook into Material for MkDocs instant navigation
if (window.document$) {
  window.document$.subscribe(function () {
    renderMath();
  });
}

document.addEventListener("DOMContentLoaded", function () {
  renderMath();
});
