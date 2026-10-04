// site/js/app.js
//
// Orquestador de la UI. Este archivo (y categoryTree.js / partCard.js /
// pegarNumero.js) NUNCA hace fetch directo a data/build/*.json: todo pasa
// por las funciones de dataClient.js (searchPart, getPart, getVehicles, y
// las dos extensiones documentadas ahí: matchVehicleByVIN,
// getPartsByFitment, además de getCategories para los SVG/nombres de
// categoría). Ver CONTRACTS.md, sección "Regla de escalado".

import {
  searchPart,
  getPart,
  getCategories,
  matchVehicleByVIN,
  matchVehicleByMakeModelYear,
  getPartsByFitment,
  _isUsingFixture,
} from "./dataClient.js";
import { isLikelyVIN, cleanVIN } from "./vin.js";
import { renderVehicleTree } from "./categoryTree.js";
import { renderPartCard } from "./partCard.js";
import { renderPegarNumeroBox } from "./pegarNumero.js";
import { renderVehiclePicker } from "./vehiclePicker.js";

const resultsEl = document.getElementById("results");
const form = document.getElementById("search-form");
const input = document.getElementById("search-input");
const fixtureBanner = document.getElementById("fixture-banner");
const toggleVehiclePickerBtn = document.getElementById("toggle-vehicle-picker");
const vehiclePickerContainer = document.getElementById("vehicle-picker-container");

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
    const card = await renderPartCard(part, categories, getPart);
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
      const card = await renderPartCard(part, categories, getPart);
      resultsEl.appendChild(card);
    }
  }

  const box = renderPegarNumeroBox((value) => {
    input.value = value;
    runSearch(value);
  });
  resultsEl.appendChild(box);
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
    await runVinFlow(vehicle);
  } else {
    await runPartNumberSearch(query);
  }
}

form.addEventListener("submit", (ev) => {
  ev.preventDefault();
  runSearch(input.value);
});

// --- Botón "¿No tienes tu VIN a mano? Elige tu vehículo" ---
// Muestra/oculta el wizard de marca→año→modelo (vehiclePicker.js). Al
// completarse, busca el vehículo en NUESTRO catálogo
// (matchVehicleByMakeModelYear, vía dataClient.js) y entra al MISMO árbol
// de categorías que usa el flujo VIN (runVinFlow), para que ambos caminos
// terminen en la misma pantalla.
let vehiclePickerInstance = null;

function closeVehiclePicker() {
  vehiclePickerContainer.hidden = true;
  vehiclePickerContainer.innerHTML = "";
  vehiclePickerInstance = null;
  toggleVehiclePickerBtn.setAttribute("aria-expanded", "false");
  toggleVehiclePickerBtn.textContent = "¿No tienes tu VIN a mano? Elige tu vehículo";
}

function openVehiclePicker() {
  vehiclePickerContainer.innerHTML = "";
  vehiclePickerInstance = renderVehiclePicker(async (make, model, year) => {
    closeVehiclePicker();
    clearResults();

    const vehicle = await matchVehicleByMakeModelYear(make, model, year);
    if (!vehicle) {
      renderEmptyState(
        `Todavía no tenemos piezas registradas para ${make} ${model} ${year} en el catálogo. ` +
          "Si tienes el VIN, intenta buscar con él, o revisa el número de parte directamente."
      );
      return;
    }
    await runVinFlow(vehicle);
  });
  vehiclePickerContainer.appendChild(vehiclePickerInstance.element);
  vehiclePickerContainer.hidden = false;
  toggleVehiclePickerBtn.setAttribute("aria-expanded", "true");
  toggleVehiclePickerBtn.textContent = "Ocultar selector de vehículo";
  vehiclePickerInstance.focusFirstField();
}

toggleVehiclePickerBtn.addEventListener("click", () => {
  if (vehiclePickerContainer.hidden) {
    openVehiclePicker();
  } else {
    closeVehiclePicker();
  }
});

// Estado inicial: mensaje de bienvenida (no hace ninguna búsqueda todavía,
// pero sí comprueba y muestra el aviso de fixture para que quede claro
// desde el primer segundo que son datos de ejemplo).
showFixtureBannerIfNeeded();
renderEmptyState(
  "Escribe un VIN de 17 caracteres o un número de parte arriba y presiona Buscar."
);
