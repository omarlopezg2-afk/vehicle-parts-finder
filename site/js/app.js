// site/js/app.js
//
// Orquestador de la UI. Este archivo (y categoryTree.js / partCard.js /
// pegarNumero.js / vehiclePicker.js) NUNCA hace fetch directo a
// data/build/*.json: todo pasa por las funciones de dataClient.js
// (searchPart, getPart, getVehicles, y las extensiones documentadas ahí:
// matchVehicleByVIN, matchVehicleByMakeModelYear, getPartsByFitment,
// getPartsByCategory, getCategories). Ver CONTRACTS.md, sección "Regla de
// escalado". vehicleSession.js tampoco hace fetch: solo lee/escribe
// localStorage (ver su propia cabecera).
//
// --- Fase 2.5 (T-E3/T-E4/T-E5/T-E6), resumen de las decisiones de layout ---
// T-E3: el buscador (VIN/número de parte) y el selector de vehículo
//   (vehiclePicker.js) viven AMBOS, siempre visibles, lado a lado en
//   #home-paths (apilados en móvil por CSS, ver styles.css) — ya no hay
//   botón que oculte uno de los dos. vehiclePicker.js se monta una sola
//   vez al cargar la página (ver mountVehiclePicker()).
// T-E4: en cuanto se resuelve un vehículo (por VIN o por el wizard), se
//   guarda con vehicleSession.saveVehicle() y se muestra en una barra fija
//   (#vehicle-bar) con botón "Cambiar vehículo". Al recargar la página
//   dentro de la misma sesión del navegador, loadVehicle() lo recupera y
//   se salta directo al árbol de categorías de ese vehículo.
// T-E5: el grid de categorías (#home-categories) se muestra siempre en el
//   home, ANTES de resolver un vehículo. Clic en una categoría SIN
//   vehículo resuelto -> runCategoryBrowse() (ver esa función para la
//   justificación de la decisión: mostrar directo las piezas de esa
//   categoría, en vez de forzar a elegir vehículo primero). Clic CON
//   vehículo ya resuelto -> runCategorySelection() (fitment real).

import {
  searchPart,
  getPart,
  getVehicles,
  getCategories,
  matchVehicleByVIN,
  matchVehicleByMakeModelYear,
  getPartsByFitment,
  getPartsByCategory,
  _isUsingFixture,
} from "./dataClient.js";
import { isLikelyVIN, cleanVIN } from "./vin.js";
import { renderVehicleTree, renderCategoryGrid } from "./categoryTree.js";
import { renderPartCard } from "./partCard.js";
import { renderPegarNumeroBox } from "./pegarNumero.js";
import { renderVehiclePicker } from "./vehiclePicker.js";
import { saveVehicle, loadVehicle, clearVehicle, formatVehicleLabel } from "./vehicleSession.js";

const resultsEl = document.getElementById("results");
const form = document.getElementById("search-form");
const input = document.getElementById("search-input");
const fixtureBanner = document.getElementById("fixture-banner");
const vehiclePickerContainer = document.getElementById("vehicle-picker-container");
const vehicleBar = document.getElementById("vehicle-bar");
const vehicleBarLabel = document.getElementById("vehicle-bar-label");
const vehicleBarChangeBtn = document.getElementById("vehicle-bar-change");
const homeCategoriesGrid = document.getElementById("home-categories-grid");

function clearResults() {
  resultsEl.innerHTML = "";
}

function renderEmptyState(message) {
  clearResults();
  const p = document.createElement("p");
  p.className = "empty-state";
  p.textContent = message;
  resultsEl.appendChild(p);
}

function renderBreadcrumb(items) {
  const nav = document.createElement("nav");
  nav.className = "breadcrumb";
  nav.setAttribute("aria-label", "Ruta de navegación");
  items.forEach((item, idx) => {
    if (idx > 0) {
      const sep = document.createElement("span");
      sep.textContent = "›";
      nav.appendChild(sep);
    }
    if (item.onClick) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = item.label;
      btn.addEventListener("click", item.onClick);
      nav.appendChild(btn);
    } else {
      const span = document.createElement("span");
      span.textContent = item.label;
      nav.appendChild(span);
    }
  });
  return nav;
}

async function showFixtureBannerIfNeeded() {
  const keys = ["parts", "vehicles", "categories"];
  const flags = await Promise.all(keys.map((k) => _isUsingFixture(k)));
  if (flags.some(Boolean)) {
    fixtureBanner.hidden = false;
    fixtureBanner.textContent =
      "Mostrando datos de ejemplo (fixture de desarrollo): T-D1 todavía no entrega data/build/*.json reales.";
  } else {
    fixtureBanner.hidden = true;
  }
}

// --- T-E4: barra "Mi vehículo" persistente ---

function showVehicleBar(vehicle) {
  vehicleBarLabel.textContent = formatVehicleLabel(vehicle);
  vehicleBar.hidden = false;
}

function hideVehicleBar() {
  vehicleBar.hidden = true;
  vehicleBarLabel.textContent = "";
}

vehicleBarChangeBtn.addEventListener("click", () => {
  clearVehicle();
  hideVehicleBar();
  renderEmptyState(
    "Escribe un VIN de 17 caracteres o un número de parte arriba, o elige tu vehículo."
  );
});

async function runPartNumberSearch(query) {
  clearResults();
  resultsEl.appendChild(
    renderBreadcrumb([{ label: "Búsqueda por número de parte" }])
  );

  const matches = await searchPart(query);
  const categories = await getCategories();

  if (matches.length === 0) {
    const p = document.createElement("p");
    p.className = "empty-state";
    p.textContent = `No encontramos piezas para "${query}". Revisa el número e inténtalo otra vez.`;
    resultsEl.appendChild(p);
    return;
  }

  const countP = document.createElement("p");
  countP.textContent =
    matches.length === 1
      ? "1 resultado encontrado:"
      : `${matches.length} resultados encontrados:`;
  resultsEl.appendChild(countP);

  for (const part of matches) {
    const card = await renderPartCard(part, categories, getPart, getVehicles);
    resultsEl.appendChild(card);
  }
}

async function runCategorySelection(vehicle, categorySlug, categories) {
  clearResults();
  resultsEl.appendChild(
    renderBreadcrumb([
      {
        label: `${vehicle.make} ${vehicle.model} ${vehicle.year}`,
        onClick: () => runVinFlow(vehicle),
      },
      {
        label: categories.find((c) => c.slug === categorySlug)?.name_es || categorySlug,
      },
    ])
  );

  const parts = await getPartsByFitment(vehicle.id, categorySlug);

  if (parts.length === 0) {
    const p = document.createElement("p");
    p.className = "empty-state";
    p.textContent = "Todavía no tenemos piezas registradas en esta categoría para tu vehículo.";
    resultsEl.appendChild(p);
  } else {
    for (const part of parts) {
      const card = await renderPartCard(part, categories, getPart, getVehicles);
      resultsEl.appendChild(card);
    }
  }

  const box = renderPegarNumeroBox((value) => {
    input.value = value;
    runSearch(value);
  });
  resultsEl.appendChild(box);
}

// --- T-E5: clic en una categoría destacada del home SIN vehículo resuelto ---
//
// Decisión de diseño (ver PR para más detalle): en vez de bloquear al
// usuario pidiéndole primero el vehículo, se muestran directamente TODAS
// las piezas del catálogo en esa categoría (vía getPartsByCategory, sin
// filtrar por fitment). Razón: el objetivo de "categorías destacadas" es
// dejar explorar el catálogo como en factorymitsubishiparts.com/
// RevolutionParts (navegar por tipo de pieza es más natural que obligar
// "primero dime tu auto"); exigir vehículo primero duplicaría el flujo
// VIN/wizard que ya está justo al lado. Se deja un aviso y un atajo claro
// para resolver el vehículo y ver piezas garantizadas por fitment.
async function runCategoryBrowse(categorySlug, categories) {
  clearResults();
  const categoryName = categories.find((c) => c.slug === categorySlug)?.name_es || categorySlug;
  resultsEl.appendChild(renderBreadcrumb([{ label: `Categoría: ${categoryName}` }]));

  const hint = document.createElement("p");
  hint.className = "search-hint";
  hint.textContent =
    "Mostrando piezas de esta categoría para todo el catálogo. Resuelve tu VIN o " +
    "elige tu vehículo arriba para ver solo las que le quedan a tu auto.";
  resultsEl.appendChild(hint);

  const parts = await getPartsByCategory(categorySlug);
  if (parts.length === 0) {
    const p = document.createElement("p");
    p.className = "empty-state";
    p.textContent = "Todavía no tenemos piezas registradas en esta categoría.";
    resultsEl.appendChild(p);
  } else {
    for (const part of parts) {
      const card = await renderPartCard(part, categories, getPart, getVehicles);
      resultsEl.appendChild(card);
    }
  }
}

async function runVinFlow(vehicle) {
  clearResults();
  const categories = await getCategories();

  resultsEl.appendChild(
    renderBreadcrumb([{ label: `${vehicle.make} ${vehicle.model} ${vehicle.year}` }])
  );

  const tree = renderVehicleTree(vehicle, categories, (slug) => {
    runCategorySelection(vehicle, slug, categories);
  });
  resultsEl.appendChild(tree);

  const box = renderPegarNumeroBox((value) => {
    input.value = value;
    runSearch(value);
  });
  resultsEl.appendChild(box);
}

async function resolveVehicleAndShowTree(vehicle) {
  saveVehicle(vehicle);
  showVehicleBar(vehicle);
  await runVinFlow(vehicle);
}

async function runSearch(rawQuery) {
  const query = rawQuery.trim();
  if (!query) {
    renderEmptyState("Escribe un VIN o un número de parte para buscar.");
    return;
  }

  await showFixtureBannerIfNeeded();

  if (isLikelyVIN(query)) {
    const vin = cleanVIN(query);
    const vehicle = await matchVehicleByVIN(vin);
    if (!vehicle) {
      renderEmptyState(
        `No encontramos un vehículo para el VIN "${vin}". Si estás probando con datos de ejemplo, usa un VIN de 17 caracteres que exista en el catálogo actual (ver data/build/vehicles.json), o busca directamente por número de parte.`
      );
      return;
    }
    await resolveVehicleAndShowTree(vehicle);
  } else {
    await runPartNumberSearch(query);
  }
}

form.addEventListener("submit", (ev) => {
  ev.preventDefault();
  runSearch(input.value);
});

// --- T-E3: selector de vehículo (vehiclePicker.js) SIEMPRE visible ---
// Ya no vive detrás de un botón "¿No tienes tu VIN a mano?": se monta una
// sola vez al cargar la página, en la columna "O elige tu vehículo" junto
// al buscador (ver #home-paths en index.html).
function mountVehiclePicker() {
  vehiclePickerContainer.innerHTML = "";
  const picker = renderVehiclePicker(async (make, model, year) => {
    clearResults();
    const vehicle = await matchVehicleByMakeModelYear(make, model, year);
    if (!vehicle) {
      renderEmptyState(
        `Todavía no tenemos piezas registradas para ${make} ${model} ${year} en el catálogo. ` +
          "Si tienes el VIN, intenta buscar con él, o revisa el número de parte directamente."
      );
      return;
    }
    await resolveVehicleAndShowTree(vehicle);
  });
  vehiclePickerContainer.appendChild(picker.element);
}

// --- T-E5: grid de categorías destacadas en el home ---
async function mountHomeCategories() {
  const categories = await getCategories();
  // No se muestra la categoría "genérico (sin foto)" como destacada: es un
  // comodín de respaldo para fotos faltantes, no una categoría real para
  // navegar desde el home.
  const featured = categories.filter((c) => c.slug !== "generico-sin-foto");
  homeCategoriesGrid.innerHTML = "";
  homeCategoriesGrid.appendChild(
    renderCategoryGrid(featured, async (slug) => {
      const savedVehicle = loadVehicle();
      if (savedVehicle) {
        await runCategorySelection(savedVehicle, slug, categories);
      } else {
        await runCategoryBrowse(slug, categories);
      }
    })
  );
}

// --- Estado inicial ---
// Si hay un vehículo recordado (T-E4), se salta directo a su árbol de
// categorías sin pedir VIN ni repetir el wizard. Si no, mensaje de
// bienvenida normal. El buscador y el selector de vehículo (T-E3) y el
// grid de categorías (T-E5) se montan siempre, pase lo que pase.
async function init() {
  mountVehiclePicker();
  await mountHomeCategories();
  await showFixtureBannerIfNeeded();

  const savedVehicle = loadVehicle();
  if (savedVehicle) {
    showVehicleBar(savedVehicle);
    await runVinFlow(savedVehicle);
  } else {
    renderEmptyState(
      "Escribe un VIN de 17 caracteres o un número de parte arriba, o elige tu vehículo."
    );
  }
}

init();
