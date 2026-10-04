// site/js/categoryTree.js
//
// Dos piezas de UI relacionadas, ambas sin fetch (reciben los datos ya
// cargados por app.js vía dataClient.js, ver CONTRACTS.md):
//
//   - renderCategoryGrid(categories, onSelectCategory, selectedSlug)
//     Grid reutilizable de categorías (SVG + nombre). Lo usa tanto el
//     home (T-E5, "categorías destacadas", SIN vehículo resuelto) como
//     renderVehicleTree de abajo (CON vehículo resuelto). Se extrajo a su
//     propia función para no duplicar el markup del grid en dos lugares.
//
//   - renderVehicleTree(vehicle, categories, onSelectCategory)
//     El árbol "vehículo -> categorías de pieza" que ya existía (flujo
//     VIN / wizard). Internamente ahora usa renderCategoryGrid.

/**
 * @param {Array<{slug,name_es,svg}>} categories
 * @param {(slug: string) => void} onSelectCategory
 * @param {string|null} [selectedSlug] si se da, esa categoría arranca con
 *   aria-pressed="true" (no se usa hoy, pero deja el grid reutilizable
 *   para un futuro "recordar última categoría").
 * @returns {HTMLElement} un <ul class="category-grid">
 */
export function renderCategoryGrid(categories, onSelectCategory, selectedSlug = null) {
  const list = document.createElement("ul");
  list.className = "category-grid";
  list.setAttribute("role", "list");

  categories.forEach((cat) => {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "category-btn";
    btn.setAttribute("aria-pressed", cat.slug === selectedSlug ? "true" : "false");
    btn.dataset.slug = cat.slug;

    const img = document.createElement("img");
    img.src = `./assets/categories/${cat.svg}`;
    img.alt = "";
    img.setAttribute("aria-hidden", "true");

    const label = document.createElement("span");
    label.className = "category-name";
    label.textContent = cat.name_es;

    btn.appendChild(img);
    btn.appendChild(label);
    btn.addEventListener("click", () => {
      list.querySelectorAll(".category-btn").forEach((b) => b.setAttribute("aria-pressed", "false"));
      btn.setAttribute("aria-pressed", "true");
      onSelectCategory(cat.slug);
    });

    li.appendChild(btn);
    list.appendChild(li);
  });

  return list;
}

/**
 * @param {object} vehicle { make, model, year, trim, engine }
 * @param {Array<{slug,name_es,svg}>} categories
 * @param {(slug: string) => void} onSelectCategory
 * @returns {HTMLElement}
 */
export function renderVehicleTree(vehicle, categories, onSelectCategory) {
  const wrapper = document.createElement("section");
  wrapper.setAttribute("aria-label", "Árbol de vehículo y categorías de pieza");

  const card = document.createElement("div");
  card.className = "vehicle-card";

  const h2 = document.createElement("h2");
  h2.textContent = `${vehicle.make} ${vehicle.model} ${vehicle.year}`;
  card.appendChild(h2);

  const meta = document.createElement("p");
  meta.className = "vehicle-meta";
  const metaBits = [];
  if (vehicle.trim) metaBits.push(`Versión: ${vehicle.trim}`);
  if (vehicle.engine) metaBits.push(`Motor: ${vehicle.engine}`);
  meta.textContent = metaBits.join(" · ");
  card.appendChild(meta);

  wrapper.appendChild(card);

  const h3 = document.createElement("h3");
  h3.textContent = "Elige la categoría de la pieza";
  h3.style.fontSize = "1rem";
  wrapper.appendChild(h3);

  wrapper.appendChild(renderCategoryGrid(categories, onSelectCategory));
  return wrapper;
}
