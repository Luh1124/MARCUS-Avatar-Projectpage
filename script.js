const cases = [
  { label: "Model 03", root: "assets/supplement/models/model-03" },
  { label: "Model 04", root: "assets/supplement/models/model-04" },
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

function modelPath(item, variant) {
  return `${item.root}/${variantFiles[variant]}`;
}

function setModel(target, caseIndex = activeCaseIndex) {
  const item = cases[caseIndex];
  const variant = activeVariants[target] || "full";
  const viewer = document.querySelector(target === "hero" ? "#heroModel" : "#assetModel");
  if (!viewer || !item) return;

  viewer.setAttribute("src", modelPath(item, variant));
  viewer.setAttribute("poster", `${item.root}/input.jpg`);
}

function setCase(index) {
  const item = cases[index];
  if (!item) return;
  activeCaseIndex = index;

  setModel("asset", index);

  const fallback = document.querySelector("#assetFallback");
  const input = document.querySelector("#assetInput");
  const caption = document.querySelector("#assetCaption");
  if (fallback) fallback.src = `${item.root}/input.jpg`;
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
