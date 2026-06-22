const cases = [
  { label: "Model 03", root: "assets/supplement/models/model-03" },
  { label: "Model 04", root: "assets/supplement/models/model-04" },
  { label: "Model 06", root: "assets/supplement/models/model-06" },
  { label: "Model 07", root: "assets/supplement/models/model-07" },
  { label: "Model 09", root: "assets/supplement/models/model-09" },
  { label: "Model 10", root: "assets/supplement/models/model-10" },
  { label: "Model 13", root: "assets/supplement/models/model-13" },
  { label: "Model 16", root: "assets/supplement/models/model-16" },
  { label: "Model 18", root: "assets/supplement/models/model-18" },
];

const variantFiles = {
  full: "full.glb",
  geometry: "geometry_gray.glb",
};

let activeCaseIndex = 0;
const activeVariants = {
  hero: "full",
  asset: "full",
};

function setViewerState(viewer, state) {
  if (!viewer) return;
  viewer.dataset.loadState = state;
}

function markViewerLoading(viewer) {
  setViewerState(viewer, "loading");
}

function markViewerLoaded(viewer) {
  setViewerState(viewer, "loaded");
}

function markViewerError(viewer) {
  setViewerState(viewer, "error");
}

function modelPath(item, variant) {
  return `${item.root}/${variantFiles[variant]}`;
}

function setModel(target, caseIndex = activeCaseIndex) {
  const item = cases[caseIndex];
  const variant = activeVariants[target] || "full";
  const viewer = document.querySelector(target === "hero" ? "#heroModel" : "#assetModel");
  if (!viewer || !item) return;

  markViewerLoading(viewer);
  viewer.setAttribute("src", modelPath(item, variant));
}

function setCase(index) {
  const item = cases[index];
  if (!item) return;
  activeCaseIndex = index;

  setModel("asset", index);

  const input = document.querySelector("#assetInput");
  const caption = document.querySelector("#assetCaption");
  if (input) input.src = `${item.root}/input.jpg`;
  if (caption) caption.textContent = `Input image for ${item.label}`;

  document.querySelectorAll(".asset-button").forEach((button) => {
    const isActive = Number(button.dataset.case) === index;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  });
}

function setVariant(target, variant) {
  if (!variantFiles[variant]) return;
  activeVariants[target] = variant;
  setModel(target);

  document.querySelectorAll(`.variant-button[data-target="${target}"]`).forEach((button) => {
    const isActive = button.dataset.variant === variant;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  });
}

document.querySelectorAll(".asset-button").forEach((button) => {
  button.setAttribute("aria-pressed", button.classList.contains("is-active") ? "true" : "false");
  button.addEventListener("click", () => setCase(Number(button.dataset.case)));
});

document.querySelectorAll(".variant-button").forEach((button) => {
  button.setAttribute("aria-pressed", button.classList.contains("is-active") ? "true" : "false");
  button.addEventListener("click", () => setVariant(button.dataset.target, button.dataset.variant));
});

document.querySelectorAll("model-viewer").forEach((viewer) => {
  markViewerLoading(viewer);
  viewer.addEventListener("load", () => markViewerLoaded(viewer));
  viewer.addEventListener("error", () => markViewerError(viewer));
});

document.querySelectorAll("[data-tri-compare]").forEach((compare) => {
  const frame = compare.querySelector(".compare-frame");
  const handle = compare.querySelector(".compare-handle");
  if (!frame || !handle) return;

  const state = {
    x: 50,
    y: 47,
  };

  const clamp = (value) => Math.max(0, Math.min(value, 100));

  const setSplit = (x, y) => {
    state.x = clamp(x);
    state.y = clamp(y);
    compare.style.setProperty("--split-x", `${state.x}%`);
    compare.style.setProperty("--split-y", `${state.y}%`);
    handle.setAttribute("aria-valuetext", `X ${Math.round(state.x)}%, Y ${Math.round(state.y)}%`);
  };

  const updateFromPointer = (event) => {
    const rect = frame.getBoundingClientRect();
    setSplit(((event.clientX - rect.left) / rect.width) * 100, ((event.clientY - rect.top) / rect.height) * 100);
  };

  const startDrag = (event) => {
    event.preventDefault();
    handle.focus({ preventScroll: true });
    updateFromPointer(event);

    const onMove = (moveEvent) => updateFromPointer(moveEvent);
    const onEnd = () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onEnd);
      window.removeEventListener("pointercancel", onEnd);
    };

    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onEnd);
    window.addEventListener("pointercancel", onEnd);
  };

  const keyboardAdjust = (event) => {
    const keys = ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"];
    if (!keys.includes(event.key)) return;

    event.preventDefault();
    const step = event.shiftKey ? 5 : 2;
    const nextX = state.x + (event.key === "ArrowRight" ? step : event.key === "ArrowLeft" ? -step : 0);
    const nextY = state.y + (event.key === "ArrowDown" ? step : event.key === "ArrowUp" ? -step : 0);
    setSplit(nextX, nextY);
  };

  frame.addEventListener("pointerdown", startDrag);
  handle.addEventListener("keydown", keyboardAdjust);

  setSplit(state.x, state.y);
});

const reveals = document.querySelectorAll(".reveal");
if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.16 },
  );

  reveals.forEach((element) => observer.observe(element));
} else {
  reveals.forEach((element) => element.classList.add("is-visible"));
}
