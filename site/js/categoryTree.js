// site/js/categoryTree.js
//
// Renderiza el árbol simple "vehículo -> categorías de pieza" para el flujo
// de búsqueda por VIN. NO hace fetch: recibe el vehículo y la lista de
// categorías ya cargados por app.js (que a su vez solo los pidió a
// dataClient.js, como manda la regla de escalado de CONTRACTS.md).

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

  const list = document.createElement("ul");
  list.className = "category-grid";
  list.setAttribute("role", "list");

  categories.forEach((cat) => {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "category-btn";
    btn.setAttribute("aria-pressed", "false");
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

  wrapper.appendChild(list);
  return wrapper;
}
