const cases = [
  {
    name: "Case 01",
    root: "assets/cases/case-01",
  },
  {
    name: "Case 02",
    root: "assets/cases/case-02",
  },
  {
    name: "Case 03",
    root: "assets/cases/case-03",
  },
];

const imageSlots = {
  inputImage: "input.jpg",
  delightImage: "delight.png",
  mapAlbedo: "albedo.png",
  mapNormal: "normal.png",
  mapRoughness: "roughness.png",
  mapSpecular: "specular.png",
  mapDisplacement: "displacement.png",
};

function setCase(index) {
  const selected = cases[index];
  if (!selected) return;

  const model = document.querySelector("#resultModel");
  const fallback = document.querySelector("#modelFallback");
  if (model) {
    model.setAttribute("src", `${selected.root}/model.glb`);
    model.setAttribute("poster", `${selected.root}/input.jpg`);
  }
  if (fallback) {
    fallback.src = `${selected.root}/input.jpg`;
  }

  Object.entries(imageSlots).forEach(([id, file]) => {
    const img = document.querySelector(`#${id}`);
    if (img) {
      img.src = `${selected.root}/${file}`;
    }
  });

  document.querySelectorAll(".case-button").forEach((button) => {
    const isActive = Number(button.dataset.case) === index;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  });
}

document.querySelectorAll(".case-button").forEach((button) => {
  button.setAttribute("aria-pressed", button.classList.contains("is-active") ? "true" : "false");
  button.addEventListener("click", () => setCase(Number(button.dataset.case)));
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
