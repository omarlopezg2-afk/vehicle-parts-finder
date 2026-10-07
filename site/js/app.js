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
import { decodeVIN } from "./vpicClient.js";
import { getNumerosDeCategoria, getSlugsConNumeros } from "./dataClient.js";
import { renderVehicleTree, renderCategoryGrid } from "./categoryTree.js";
import { renderPartCard } from "./partCard.js";
import { renderPegarNumeroBox } from "./pegarNumero.js";
import { renderVehiclePicker } from "./vehiclePicker.js";
import { saveVehicle, loadVehicle, clearVehicle, formatVehicleLabel } from "./vehicleSession.js";
import { navegar, alCambiarRuta, alNavegar, estadoDesdeHash } from "./router.js";
import { renderBandaDeConfianza } from "./confianza.js";

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
  navegar({ vista: "inicio" }); // T-E5: la URL vuelve al inicio con la vista
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
        onClick: () => {
          navegar({
            vista: "vehiculo",
            make: vehicle.make,
            model: vehicle.model,
            year: String(vehicle.year),
          });
          runVinFlow(vehicle);
        },
      },
      {
        label: categories.find((c) => c.slug === categorySlug)?.name_es || categorySlug,
      },
    ])
  );

  const [parts, numeros] = await Promise.all([
    getPartsByFitment(vehicle.id, categorySlug),
    getNumerosDeCategoria(vehicle, categorySlug),
  ]);

  if (numeros.length) {
    resultsEl.appendChild(renderNumerosDeParte(numeros, vehicle));
  }

  if (parts.length === 0) {
    const p = document.createElement("p");
    p.className = "empty-state";
    // El mensaje depende de lo que SÍ haya: decir "no tenemos piezas" cuando arriba está el
    // número de la pieza sería confundir al visitante (y fue justo lo que pasó al probarlo).
    p.textContent = numeros.length
      ? "Arriba tienes el número de la pieza. De esta categoría todavía no tenemos ofertas de compra para tu vehículo."
      : "Todavía no tenemos piezas registradas en esta categoría para tu vehículo.";
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

// T-B14: el número de parte. Va ARRIBA de las ofertas a propósito: el visitante que llega con una
// avería quiere saber CUÁL es la pieza; las ofertas (precio y dónde comprarla) vienen después.
// Las dos fuentes son distintas y se complementan: AUTODOC/TecDoc da el número y la marca; eBay
// da la oferta. Cuando eBay no tiene nada en esa categoría (le pasa al filtro de aceite y a la
// batería), solo se ve esta parte — y antes el sitio decía "no tenemos piezas" aunque el número
// estuviera guardado. Eso lo reportó el usuario probando el 07/10/2026.
// Traduce a español las especificaciones que da TecDoc y elige las que de verdad discriminan
// (posición, medidas, tipo de disco, sistema de freno). Se muestran pocas a propósito: el resto
// solo añade ruido en una ficha pequeña.
const ESPECIFICACIONES_UTILES = [
  [/fitting position/i, "Posición", { "front axle": "Delantera", "rear axle": "Trasera" }],
  [/brake disc type/i, "Disco", null],
  [/outer diameter/i, "Diámetro exterior", null],
  [/^thickness/i, "Espesor", null],
  [/brake system/i, "Sistema de freno", null],
  [/wear warning/i, "Aviso de desgaste", null],
];

function detallesDeLaPieza(pieza, vehiculo) {
  const lineas = [];
  const esp = pieza.especificaciones || {};

  for (const [patron, etiqueta, traducciones] of ESPECIFICACIONES_UTILES) {
    const clave = Object.keys(esp).find((k) => patron.test(k));
    if (!clave) continue;
    let valor = String(esp[clave]).trim();
    if (!valor) continue;
    if (traducciones) valor = traducciones[valor.toLowerCase()] || valor;
    lineas.push({ clase: "numero-detalle", texto: `${etiqueta}: ${valor}` });
    if (lineas.length >= 3) break;
  }

  // El número original del fabricante: lo que la gente reconoce y lo que pide en la tienda.
  // Cuidado con la etiqueta: TecDoc cruza los números de OTRAS marcas que usaron la misma pieza
  // (una pastilla de este Mitsubishi también es "original" de un Chrysler). Llamar "Original" a
  // un número de Chrysler bajo un Mitsubishi confunde, así que se prefiere el de la marca del
  // vehículo y, si no lo hay, se dice claramente de quién es.
  const originales = Array.isArray(pieza.originales) ? pieza.originales.slice() : [];
  if (originales.length) {
    const marcaVehiculo = String((vehiculo && vehiculo.make) || "").toUpperCase();
    originales.sort((a, b) => {
      const sa = String(a.marca || "").toUpperCase() === marcaVehiculo ? 0 : 1;
      const sb = String(b.marca || "").toUpperCase() === marcaVehiculo ? 0 : 1;
      return sa - sb;
    });
    const primero = originales[0];
    const numeros = originales.slice(0, 2).map((o) => o.numero).filter(Boolean);
    if (numeros.length) {
      const suya = String(primero.marca || "").toUpperCase() === marcaVehiculo;
      const marca = primero.marca ? `${primero.marca} ` : "";
      lineas.push({
        clase: "numero-original",
        texto: suya
          ? `Original ${marca}${numeros.join(" · ")}`.trim()
          : `También original de ${marca}${numeros.join(" · ")}`.trim(),
      });
    }
  }
  return lineas;
}

function renderNumerosDeParte(numeros, vehiculo) {
  const seccion = document.createElement("section");
  seccion.className = "numeros-parte";

  const h = document.createElement("h2");
  h.textContent = numeros.length === 1 ? "Número de la pieza" : `Números de la pieza (${numeros.length})`;
  seccion.appendChild(h);

  const nota = document.createElement("p");
  nota.className = "search-hint";
  nota.textContent =
    "Confirmado por catálogo técnico (TecDoc) para tu vehículo exacto. Con este número cualquier " +
    "tienda te da la pieza correcta.";
  seccion.appendChild(nota);

  const grid = document.createElement("div");
  grid.className = "numeros-grid";
  for (const pieza of numeros) {
    const ficha = document.createElement("div");
    ficha.className = "numero-ficha";

    if (pieza.foto) {
      const img = document.createElement("img");
      img.src = pieza.foto;
      img.alt = pieza.pieza || "Foto de la pieza";
      img.loading = "lazy";
      img.referrerPolicy = "no-referrer";
      // Si la imagen no carga, se quita sin romper la ficha: el número es el dato, la foto ayuda.
      img.addEventListener("error", () => img.remove());
      ficha.appendChild(img);
    }

    const numero = document.createElement("div");
    numero.className = "numero";
    numero.textContent = pieza.numero;
    ficha.appendChild(numero);

    const marca = document.createElement("div");
    marca.className = "numero-marca";
    marca.textContent = pieza.marca;
    ficha.appendChild(marca);

    const nombre = document.createElement("div");
    nombre.className = "numero-nombre";
    nombre.textContent = pieza.pieza;
    ficha.appendChild(nombre);

    // T-B16: lo que distingue una pieza de otra del mismo tipo. "Delantera · 302 mm" es lo que
    // convierte una lista de marcas en la pieza exacta del coche.
    for (const linea of detallesDeLaPieza(pieza, vehiculo)) {
      const d = document.createElement("div");
      d.className = linea.clase;
      d.textContent = linea.texto;
      ficha.appendChild(d);
    }

    grid.appendChild(ficha);
  }
  seccion.appendChild(grid);
  return seccion;
}

async function runVinFlow(vehicle) {
  clearResults();
  const categories = await getCategories();

  resultsEl.appendChild(
    renderBreadcrumb([{ label: `${vehicle.make} ${vehicle.model} ${vehicle.year}` }])
  );

  // T-B17 (1/2): el patrón del selector de Mitsubishi que el usuario señaló —"y ahí te ofrece las
  // categorías que tienen en catálogo"— aplicado a lo nuestro: se enseña ARRIBA lo que de verdad
  // tenemos cubierto para ese vehículo exacto, y debajo queda el árbol completo para explorar. Sin
  // esto, el visitante tiene que adivinar cuál de las 34 categorías devolverá algo.
  const conDatos = await getSlugsConNumeros(vehicle);
  if (conDatos.length) {
    const seccion = document.createElement("section");
    seccion.className = "categorias-con-datos";

    const h = document.createElement("h2");
    h.textContent = `Con pieza confirmada para tu vehículo (${conDatos.length})`;
    seccion.appendChild(h);

    const nota = document.createElement("p");
    nota.className = "search-hint";
    nota.textContent =
      "Estas categorías ya tienen el número de la pieza para tu vehículo. Debajo puedes explorar el " +
      "catálogo completo.";
    seccion.appendChild(nota);

    const lista = document.createElement("div");
    lista.className = "chips-categorias";
    for (const slug of conDatos) {
      const categoria = categories.find((c) => c.slug === slug);
      if (!categoria) continue;
      const chip = document.createElement("button");
      chip.type = "button";
      chip.textContent = categoria.name_es || slug;
      chip.addEventListener("click", () => {
        navegar({
          vista: "vehiculo",
          make: vehicle.make,
          model: vehicle.model,
          year: String(vehicle.year),
          categoria: slug,
        });
        runCategorySelection(vehicle, slug, categories);
      });
      lista.appendChild(chip);
    }
    seccion.appendChild(lista);
    resultsEl.appendChild(seccion);
  }

  const tree = renderVehicleTree(vehicle, categories, (slug) => {
    // T-E5: la categoría dentro del vehículo tiene su propia URL, así que "atrás"
    // devuelve al árbol en vez de salir del sitio.
    navegar({
      vista: "vehiculo",
      make: vehicle.make,
      model: vehicle.model,
      year: String(vehicle.year),
      categoria: slug,
    });
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

// --- T-B9: el VIN como entrada de verdad ---
//
// Antes, un VIN solo servía si ese vehículo ya estaba en nuestro catálogo
// (matchVehicleByVIN busca el id `vin-<VIN>` de data/build/vehicles.json): con
// un catálogo de un vehículo, cualquier otro VIN recibía un "no encontramos".
// Ahora el VIN primero se busca en el catálogo y, si no está, se DECODIFICA con
// vPIC (servicio público de la NHTSA, sin llave y con CORS abierto) para saber
// qué vehículo es; con marca/modelo/año se busca el fitment, que es como lo pide
// eBay. La investigación completa (DGII, placa, QR del marbete y por qué el VIN
// es la entrada correcta) está en docs/placa-y-chasis-fuentes.md.
async function resolverVehiculoPorVIN(vin) {
  const enCatalogo = await matchVehicleByVIN(vin);
  if (enCatalogo) {
    return { vehicle: enCatalogo, decodificado: null, origen: "catalogo" };
  }

  const decodificado = await decodeVIN(vin);
  if (!decodificado || !decodificado.make || !decodificado.model || !decodificado.year) {
    return { vehicle: null, decodificado, origen: null };
  }

  const porAtributos = await matchVehicleByMakeModelYear(
    decodificado.make,
    decodificado.model,
    decodificado.year
  );
  return {
    vehicle: porAtributos || null,
    decodificado,
    origen: porAtributos ? "fitment" : null,
  };
}

// El VIN identifica un vehículo aunque su fitment todavía no esté en nuestro
// catálogo. En ese caso se muestra la ficha del vehículo (datos oficiales de la
// NHTSA) y un mensaje honesto: sabemos exactamente qué carro es, pero todavía no
// tenemos piezas suyas registradas. Es información real, no un callejón sin
// salida: el visitante confirma que leímos bien su VIN.
function renderVehiculoDecodificado(d) {
  clearResults();
  resultsEl.appendChild(renderBreadcrumb([{ label: `VIN ${d.vin}` }]));

  const card = document.createElement("div");
  card.className = "vehiculo-card";

  const h = document.createElement("h2");
  h.textContent = [d.make, d.model, d.year].filter(Boolean).join(" ");
  card.appendChild(h);

  const aviso = document.createElement("p");
  aviso.className = "search-hint";
  aviso.textContent = d.valido
    ? "Identificamos tu vehículo por el VIN (datos oficiales de la NHTSA). Todavía no tenemos piezas registradas para él."
    : "El VIN no pasó la verificación oficial (dígito de control). Revísalo: un VIN tiene 17 caracteres y no usa las letras I, O ni Q.";
  card.appendChild(aviso);

  const filas = [
    ["Marca", d.make],
    ["Modelo", d.model],
    ["Año", d.year],
    ["Versión", d.trim || d.series],
    ["Carrocería", d.bodyClass],
    [
      "Motor",
      [
        d.displacementL ? `${d.displacementL} L` : "",
        d.engineCylinders ? `${d.engineCylinders} cil.` : "",
        d.engineHP ? `${d.engineHP} HP` : "",
      ]
        .filter(Boolean)
        .join(" · "),
    ],
    ["Tracción", d.driveType],
    ["Transmisión", d.transmission],
    ["Combustible", d.fuelType],
    ["Fabricado en", d.plantCountry],
  ].filter(([, valor]) => valor);

  const dl = document.createElement("dl");
  dl.className = "vehiculo-datos";
  for (const [etiqueta, valor] of filas) {
    const dt = document.createElement("dt");
    dt.textContent = etiqueta;
    const dd = document.createElement("dd");
    dd.textContent = valor;
    dl.appendChild(dt);
    dl.appendChild(dd);
  }
  card.appendChild(dl);

  const siguiente = document.createElement("p");
  siguiente.className = "search-hint";
  siguiente.textContent =
    "Mientras tanto puedes buscar por número de parte, o elegir tu vehículo en el selector de arriba.";
  card.appendChild(siguiente);

  resultsEl.appendChild(card);
}

async function runVinSearch(vin) {
  clearResults();
  const { vehicle, decodificado } = await resolverVehiculoPorVIN(vin);

  if (vehicle) {
    await resolveVehicleAndShowTree(vehicle);
    return;
  }
  if (!decodificado) {
    renderEmptyState(
      `No pudimos identificar el VIN "${vin}". Comprueba que sean 17 caracteres ` +
        "(un VIN no usa las letras I, O ni Q) o busca por número de parte."
    );
    return;
  }
  renderVehiculoDecodificado(decodificado);
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
    navegar({ vista: "vin", vin });
    await runVinSearch(vin);
  } else {
    navegar({ vista: "numero", numero: query });
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
    navegar({
      vista: "vehiculo",
      make: vehicle.make,
      model: vehicle.model,
      year: String(vehicle.year),
    });
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
        navegar({
          vista: "vehiculo",
          make: savedVehicle.make,
          model: savedVehicle.model,
          year: String(savedVehicle.year),
          categoria: slug,
        });
        await runCategorySelection(savedVehicle, slug, categories);
      } else {
        navegar({ vista: "categoria", categoria: slug });
        await runCategoryBrowse(slug, categories);
      }
    })
  );
}

// --- Portada vs. vista activa (dirección B) ---
//
// Sin esto, tras buscar el visitante seguía viendo la portada: el bloque de
// resultados vive al final del documento, más de mil píxeles abajo, así que
// pulsaba "Buscar" y no pasaba nada visible. Con `data-vista` en el <body>, el CSS
// recoge la portada (titular, lema, banda de confianza, selector de vehículo y
// categorías) y deja arriba el buscador y los resultados.
//
// Se marca aquí, en un único sitio, y no en cada flujo.
function sincronizarVista() {
  document.body.dataset.vista = estadoDesdeHash(window.location.hash).vista;
}

// --- T-E5: restaurar la vista que dice la URL ---
//
// Esta es la pieza que hace que el botón "atrás" funcione y que los enlaces sean
// compartibles. Se llama (a) al cargar la página si la URL trae una vista y (b) cada
// vez que el usuario navega con atrás/adelante.
//
// Clave del diseño: aquí NO se llama a `navegar()`. La URL ya es la correcta; volver a
// escribirla ensuciaría el historial y podría provocar un bucle de renders.
async function restaurarVista(estado) {
  document.body.dataset.vista = estado.vista;
  switch (estado.vista) {
    case "numero":
      input.value = estado.numero;
      await runPartNumberSearch(estado.numero);
      return;

    case "categoria": {
      const categories = await getCategories();
      await runCategoryBrowse(estado.categoria, categories);
      return;
    }

    case "vin": {
      // T-B9: el mismo camino que la búsqueda, para que un enlace compartido
      // (#/vin/<VIN>) se resuelva igual que si se hubiera tecleado.
      input.value = estado.vin;
      await runVinSearch(estado.vin);
      return;
    }

    case "vehiculo": {
      const vehicle = await matchVehicleByMakeModelYear(estado.make, estado.model, estado.year);
      if (!vehicle) {
        renderEmptyState(
          `Todavía no tenemos piezas registradas para ${estado.make} ${estado.model} ${estado.year}.`
        );
        return;
      }
      if (estado.categoria) {
        saveVehicle(vehicle);
        showVehicleBar(vehicle);
        const categories = await getCategories();
        await runCategorySelection(vehicle, estado.categoria, categories);
      } else {
        await resolveVehicleAndShowTree(vehicle);
      }
      return;
    }

    default:
      renderEmptyState(
        "Escribe un VIN de 17 caracteres o un número de parte arriba, o elige tu vehículo."
      );
  }
}

// --- Estado inicial ---
// Orden de prioridad: (1) la URL manda (enlace compartido o recarga con estado);
// (2) si no hay vista en la URL pero hay vehículo recordado (T-E4), se salta a su
// árbol de categorías —y se deja la URL a tono, sin añadir entrada al historial—;
// (3) si no, mensaje de bienvenida. El buscador, el selector de vehículo (T-E3) y el
// grid de categorías (T-E5) se montan siempre, pase lo que pase.
async function init() {
  mountVehiclePicker();
  await mountHomeCategories();
  await showFixtureBannerIfNeeded();

  // Banda de confianza (dirección B): cifras contadas del catálogo real.
  await renderBandaDeConfianza(document.getElementById("trust-band"));

  // Chips de ejemplo del hero: un visitante que no sabe qué escribir tiene por
  // dónde entrar. Son números que EXISTEN en el catálogo (comprobado), no adornos.
  for (const chip of document.querySelectorAll("[data-ejemplo]")) {
    chip.addEventListener("click", () => {
      input.value = chip.dataset.ejemplo;
      navegar({ vista: "numero", numero: chip.dataset.ejemplo });
      runPartNumberSearch(chip.dataset.ejemplo);
    });
  }

  alNavegar(sincronizarVista);
  sincronizarVista();

  alCambiarRuta((estado) => {
    restaurarVista(estado).catch((error) => {
      console.error("No se pudo restaurar la vista", estado, error);
      renderEmptyState("No pudimos restaurar esa vista. Prueba a buscarlo otra vez.");
    });
  });

  const estadoInicial = estadoDesdeHash(window.location.hash);
  if (estadoInicial.vista !== "inicio") {
    await restaurarVista(estadoInicial);
    return;
  }

  const savedVehicle = loadVehicle();
  if (savedVehicle) {
    showVehicleBar(savedVehicle);
    navegar(
      {
        vista: "vehiculo",
        make: savedVehicle.make,
        model: savedVehicle.model,
        year: String(savedVehicle.year),
      },
      { reemplazar: true }
    );
    await runVinFlow(savedVehicle);
  } else {
    renderEmptyState(
      "Escribe un VIN de 17 caracteres o un número de parte arriba, o elige tu vehículo."
    );
  }
}

init();
