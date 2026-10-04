// site/js/categoryTree.js
//
// Tres piezas relacionadas, todas sin fetch (reciben los datos ya
// cargados por app.js vía dataClient.js, ver CONTRACTS.md):
//
//   - groupCategories(categories)
//     Función PURA (sin DOM) que agrupa la lista plana de categorías por
//     `group_slug`/`group_name_es` (CONTRACTS.md, sección
//     categories.json, jerarquía de 2 niveles agregada 04/10/2026 para
//     T-F2/T-E7). Se exporta aparte de renderCategoryGrid para poder
//     testearla con `node --test` sin necesitar DOM/jsdom (ver
//     site/tests/categoryTree.test.js). Si una categoría no trae
//     group_slug/group_name_es (fixture vieja, o site/data/build/
//     categories.json todavía no sincronizado con el build real), cae en
//     un grupo de respaldo "Otros" en vez de desaparecer u lanzar error.
//
//   - renderCategoryGrid(categories, onSelectCategory, selectedSlug)
//     Grid reutilizable de categorías, AHORA agrupado en un acordeón de
//     2 niveles (grupo -> slugs hoja) en vez de la lista plana de 13
//     items que había antes de T-E7. Lo usa tanto el home (T-E5,
//     "categorías destacadas", SIN vehículo resuelto) como
//     renderVehicleTree de abajo (CON vehículo resuelto) — misma firma
//     que antes de T-E7, así que app.js no necesitó cambios.
//
//   - renderVehicleTree(vehicle, categories, onSelectCategory)
//     El árbol "vehículo -> categorías de pieza" que ya existía (flujo
//     VIN / wizard). Internamente sigue usando renderCategoryGrid, ahora
//     agrupado.
//
// --- Diseño del árbol agrupado (T-E7) ---
// Cada grupo es un <button aria-expanded="…" aria-controls="…"> seguido
// de un <ul class="category-grid" hidden> con los slugs hoja de ese
// grupo (mismo markup/clase que ya existía para los botones hoja — no se
// tocó esa lógica, solo lo que los envuelve). Expandir/colapsar es un
// simple toggle de `aria-expanded` + el atributo `hidden` del panel; no
// hace falta JS de teclado a medida porque:
//   - Los <button> nativos ya responden a Enter/Espacio disparando
//     "click" (que es el único listener que se necesita).
//   - El atributo `hidden` saca los botones hoja del árbol de
//     accesibilidad Y del orden de tabulación automáticamente (un
//     elemento con `hidden` no es focusable). Por eso Tab va de un grupo
//     colapsado directo al siguiente grupo, y en cuanto un grupo se
//     expande (se quita `hidden`), Tab entra a sus slugs hoja antes de
//     seguir al próximo grupo — exactamente el orden pedido en la tarea,
//     sin reimplementar manejo de flechas ni roving tabindex.
// Si se abre con una `selectedSlug` que pertenece a un grupo, ese grupo
// arranca expandido (para no esconder la categoría ya elegida al volver
// a renderizar); el resto arranca colapsado.

const FALLBACK_GROUP_SLUG = "otros";
const FALLBACK_GROUP_NAME_ES = "Otros";

/**
 * Agrupa una lista plana de categorías por `group_slug`/`group_name_es`,
 * preservando el orden de primera aparición de cada grupo (y de las
 * categorías dentro de cada grupo). No muta el arreglo de entrada.
 *
 * @param {Array<{slug:string,name_es:string,svg:string,group_slug?:string,group_name_es?:string}>} categories
 * @returns {Array<{slug:string, name_es:string, categories: Array}>}
 */
export function groupCategories(categories) {
  const order = [];
  const bySlug = new Map();

  (categories || []).forEach((cat) => {
    const groupSlug = cat.group_slug || FALLBACK_GROUP_SLUG;
    const groupName = cat.group_name_es || FALLBACK_GROUP_NAME_ES;

    if (!bySlug.has(groupSlug)) {
      const group = { slug: groupSlug, name_es: groupName, categories: [] };
      bySlug.set(groupSlug, group);
      order.push(group);
    }
    bySlug.get(groupSlug).categories.push(cat);
  });

  return order;
}

function _buildLeafButton(cat, container, onSelectCategory, selectedSlug) {
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
    // El "pressed" se resetea sobre TODO el árbol (container), no solo
    // dentro del grupo actual, para que solo haya un slug hoja marcado a
    // la vez aunque esté en otro grupo ya expandido.
    container.querySelectorAll(".category-btn").forEach((b) => b.setAttribute("aria-pressed", "false"));
    btn.setAttribute("aria-pressed", "true");
    onSelectCategory(cat.slug);
  });

  li.appendChild(btn);
  return li;
}

let _groupIdCounter = 0;

/**
 * @param {Array<{slug,name_es,svg,group_slug?,group_name_es?}>} categories
 * @param {(slug: string) => void} onSelectCategory
 * @param {string|null} [selectedSlug] si se da, ese slug hoja arranca con
 *   aria-pressed="true" Y el grupo al que pertenece arranca expandido
 *   (para no esconder la categoría ya elegida).
 * @returns {HTMLElement} un <div class="category-groups"> (acordeón de
 *   grupo -> slugs hoja).
 */
export function renderCategoryGrid(categories, onSelectCategory, selectedSlug = null) {
  const groups = groupCategories(categories);

  const container = document.createElement("div");
  container.className = "category-groups";
  container.setAttribute("role", "list");

  groups.forEach((group) => {
    const groupHasSelected = group.categories.some((c) => c.slug === selectedSlug);
    const panelId = `cat-group-panel-${group.slug}-${_groupIdCounter++}`;

    const item = document.createElement("div");
    item.className = "category-group";
    item.setAttribute("role", "listitem");

    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "category-group-toggle";
    toggle.setAttribute("aria-expanded", groupHasSelected ? "true" : "false");
    toggle.setAttribute("aria-controls", panelId);
    toggle.dataset.groupSlug = group.slug;

    const label = document.createElement("span");
    label.className = "category-group-name";
    label.textContent = group.name_es;

    const count = document.createElement("span");
    count.className = "category-group-count";
    count.textContent = String(group.categories.length);
    count.setAttribute("aria-hidden", "true");

    const chevron = document.createElement("span");
    chevron.className = "category-group-chevron";
    chevron.setAttribute("aria-hidden", "true");
    chevron.textContent = "▾";

    toggle.appendChild(label);
    toggle.appendChild(count);
    toggle.appendChild(chevron);

    const panel = document.createElement("ul");
    panel.className = "category-grid category-group-panel";
    panel.id = panelId;
    panel.setAttribute("role", "list");
    panel.hidden = !groupHasSelected;

    group.categories.forEach((cat) => {
      panel.appendChild(_buildLeafButton(cat, container, onSelectCategory, selectedSlug));
    });

    toggle.addEventListener("click", () => {
      const expanded = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", expanded ? "false" : "true");
      panel.hidden = expanded;
    });

    item.appendChild(toggle);
    item.appendChild(panel);
    container.appendChild(item);
  });

  return container;
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
