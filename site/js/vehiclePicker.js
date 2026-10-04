// site/js/vehiclePicker.js
//
// Wizard "elige tu vehículo sin VIN" (marca → año → modelo), camino
// alterno al flujo VIN que PLAN.md siempre describió ("VIN, o
// marca/modelo/año/versión"). Desde T-E3 (Fase 2.5) vive SIEMPRE visible
// en la misma pantalla de búsqueda, en su propia columna junto al
// buscador de VIN/número de parte (ver #home-paths en index.html) — ya
// no hay botón que lo oculte.
//
// Este módulo NO hace fetch a data/build/*.json (eso sigue siendo solo
// trabajo de dataClient.js, ver CONTRACTS.md). Las dos fuentes de datos
// que usa:
//   - site/js/vpicClient.js  → marcas y modelos reales de vPIC (API de
//     terceros, EXCEPCIÓN deliberada y documentada a la regla de
//     escalado — ver cabecera de ese archivo).
//   - dataClient.matchVehicleByMakeModelYear(make, model, year) → una vez
//     elegidos los tres valores, busca el vehículo en NUESTRO catálogo
//     (data/build/vehicles.json) para entrar al mismo árbol de categorías
//     que usa el flujo VIN.
//
// Accesibilidad: cada paso es un <fieldset>/<select> normal (navegable
// con Tab/flechas/Enter como cualquier <select> nativo, sin reinventar un
// combobox custom). El botón que abre el wizard tiene aria-expanded y el
// contenedor se anuncia con aria-live a través del mismo #results que ya
// usa el resto de la app (ver app.js).

import { getAllMakes, getModelsForMakeYear, getYearRange } from "./vpicClient.js";

/**
 * @param {(make: string, model: string, year: number) => void} onComplete
 *   Se llama cuando el usuario eligió marca + año + modelo. app.js decide
 *   qué hacer con eso (buscar el vehículo en el catálogo y mostrar el
 *   árbol de categorías, igual que con el flujo VIN).
 * @returns {{ element: HTMLElement, focusFirstField: () => void }}
 */
export function renderVehiclePicker(onComplete) {
  const section = document.createElement("section");
  section.className = "vehicle-picker";
  section.setAttribute("aria-label", "Elige tu vehículo sin VIN");

  const intro = document.createElement("p");
  intro.className = "search-hint";
  intro.textContent =
    "Elige marca, año y modelo. Usamos el catálogo público de vPIC (NHTSA) " +
    "para esta lista — necesitas internet, igual que para ver ofertas de eBay.";
  section.appendChild(intro);

  const status = document.createElement("p");
  status.className = "vehicle-picker-status";
  status.setAttribute("role", "status");
  status.setAttribute("aria-live", "polite");
  section.appendChild(status);

  const form = document.createElement("form");
  form.className = "vehicle-picker-form";
  form.autocomplete = "off";

  // --- Paso 1: marca ---
  const makeField = _buildSelectField({
    id: "vp-make",
    label: "Marca",
    placeholder: "Elige una marca…",
  });
  form.appendChild(makeField.wrapper);

  // --- Paso 2: año ---
  const yearField = _buildSelectField({
    id: "vp-year",
    label: "Año",
    placeholder: "Elige un año…",
  });
  yearField.select.disabled = true;
  form.appendChild(yearField.wrapper);

  // --- Paso 3: modelo ---
  const modelField = _buildSelectField({
    id: "vp-model",
    label: "Modelo",
    placeholder: "Elige un modelo…",
  });
  modelField.select.disabled = true;
  form.appendChild(modelField.wrapper);

  const submitBtn = document.createElement("button");
  submitBtn.type = "submit";
  submitBtn.className = "btn";
  submitBtn.textContent = "Ver piezas para este vehículo";
  submitBtn.disabled = true;
  form.appendChild(submitBtn);

  section.appendChild(form);

  function _setStatus(msg) {
    status.textContent = msg;
  }

  function _updateSubmitState() {
    submitBtn.disabled = !(makeField.select.value && yearField.select.value && modelField.select.value);
  }

  // --- Carga inicial de marcas ---
  _setStatus("Cargando marcas…");
  makeField.select.disabled = true;
  getAllMakes()
    .then((makes) => {
      if (makes.length === 0) {
        _setStatus(
          "No pudimos cargar la lista de marcas (vPIC sin respuesta o sin internet). " +
            "Intenta de nuevo más tarde, o busca con tu VIN o número de parte."
        );
        return;
      }
      _fillOptions(makeField.select, makes.map((m) => ({ value: m.name, label: m.name })));
      makeField.select.disabled = false;
      // Los años no dependen de vPIC: se llenan de una vez.
      _fillOptions(
        yearField.select,
        getYearRange().map((y) => ({ value: String(y), label: String(y) }))
      );
      _setStatus("Marcas cargadas. Elige una marca para continuar.");
      // focusFirstField() se llamó justo al abrir el wizard, cuando el
      // <select> todavía estaba disabled (un elemento disabled no puede
      // recibir foco: la llamada no hizo nada). Ahora que ya está
      // habilitado, se intenta de nuevo para que el teclado quede en el
      // primer campo útil apenas terminan de cargar las marcas.
      if (document.activeElement === document.body || document.activeElement === null) {
        makeField.select.focus();
      }
    })
    .catch((err) => {
      console.error("vehiclePicker: error cargando marcas", err);
      _setStatus("Ocurrió un error cargando las marcas. Intenta de nuevo más tarde.");
    });

  // --- Marca elegida → habilita año; si año ya elegido, recarga modelos ---
  makeField.select.addEventListener("change", () => {
    modelField.select.disabled = true;
    _fillOptions(modelField.select, []);
    _updateSubmitState();

    if (!makeField.select.value) {
      yearField.select.disabled = true;
      return;
    }
    yearField.select.disabled = false;
    if (yearField.select.value) {
      _loadModels();
    }
  });

  // --- Año elegido → carga modelos para marca+año ---
  yearField.select.addEventListener("change", () => {
    modelField.select.disabled = true;
    _fillOptions(modelField.select, []);
    _updateSubmitState();
    if (makeField.select.value && yearField.select.value) {
      _loadModels();
    }
  });

  modelField.select.addEventListener("change", _updateSubmitState);

  function _loadModels() {
    const make = makeField.select.value;
    const year = yearField.select.value;
    _setStatus(`Cargando modelos de ${make} ${year}…`);
    modelField.select.disabled = true;
    getModelsForMakeYear(make, year)
      .then((models) => {
        if (models.length === 0) {
          _setStatus(
            `No encontramos modelos de ${make} para ${year} en vPIC. ` +
              "Prueba otro año, o busca con tu VIN o número de parte."
          );
          return;
        }
        _fillOptions(modelField.select, models.map((m) => ({ value: m.name, label: m.name })));
        modelField.select.disabled = false;
        _setStatus(`Elige el modelo de ${make} ${year}.`);
      })
      .catch((err) => {
        console.error("vehiclePicker: error cargando modelos", err);
        _setStatus("Ocurrió un error cargando los modelos. Intenta de nuevo más tarde.");
      });
  }

  form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    const make = makeField.select.value;
    const year = Number(yearField.select.value);
    const model = modelField.select.value;
    if (!make || !year || !model) return;
    onComplete(make, model, year);
  });

  return {
    element: section,
    focusFirstField: () => makeField.select.focus(),
  };
}

function _buildSelectField({ id, label, placeholder }) {
  const wrapper = document.createElement("div");
  wrapper.className = "vehicle-picker-field";

  const labelEl = document.createElement("label");
  labelEl.htmlFor = id;
  labelEl.textContent = label;

  const select = document.createElement("select");
  select.id = id;
  select.name = id;

  const placeholderOpt = document.createElement("option");
  placeholderOpt.value = "";
  placeholderOpt.textContent = placeholder;
  select.appendChild(placeholderOpt);

  wrapper.appendChild(labelEl);
  wrapper.appendChild(select);

  return { wrapper, select };
}

function _fillOptions(select, items) {
  // Conserva solo la opción placeholder (primera) y agrega las nuevas.
  const placeholder = select.firstElementChild;
  select.innerHTML = "";
  if (placeholder) select.appendChild(placeholder);
  for (const item of items) {
    const opt = document.createElement("option");
    opt.value = item.value;
    opt.textContent = item.label;
    select.appendChild(opt);
  }
  select.value = "";
}
