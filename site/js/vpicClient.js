// site/js/vpicClient.js
//
// EXCEPCIÓN DELIBERADA a la "Regla de escalado" de CONTRACTS.md ("el
// frontend solo lee datos a través de site/js/dataClient.js... ningún otro
// archivo de site/ debe hacer fetch directo a data/build/*.json").
//
// Por qué es una excepción y no una violación: esa regla protege el
// catálogo PROPIO del proyecto (parts.json/vehicles.json/categories.json,
// hoy generado por pipeline/build_index.py, mañana quizás servido por
// Supabase). vPIC (NHTSA) NO es un dato de nuestro catálogo: es un
// servicio público de terceros (igual que eBay para precios) que solo
// sirve para el flujo "elige tu vehículo sin VIN" (marca → año → modelo).
// Por eso este archivo es SU PROPIO módulo, separado de dataClient.js, y
// NUNCA se mezclan sus llamadas con el fetch de nuestros JSON. Si el
// líder prefiere que esto no exista como módulo aparte, la alternativa
// documentada en el PR (Opción B: pipeline/generate_makes_models.json
// pre-generado) está descartada a favor de esta porque no requiere que
// nadie mantenga un script aparte ni commitear un snapshot que se
// desactualiza; a cambio, el usuario necesita internet para el
// drill-down (ya la necesita para ver ofertas de eBay, así que es
// consistente con el resto del sitio).
//
// Verificado a mano (no asumido): vpic.nhtsa.dot.gov responde
// `access-control-allow-origin: *` en GetMakesForVehicleType y
// GetModelsForMakeYear, así que un fetch desde el navegador del usuario
// (origen GitHub Pages o localhost) funciona sin proxy ni backend propio.
//
// Replica EXACTAMENTE la misma lógica de filtrado que
// pipeline/fetch_vehicles.py (ver sus docstrings de get_all_makes /
// get_models_for_make_year) para que el camino VIN (Python, en el
// pipeline de build) y el camino drill-down (JS, en el navegador)
// lleguen al mismo tipo de resultado para una misma marca/año. Los
// mismos "problemas conocidos" documentados allá (marcas límite tipo
// camión, "Mitsubishi Fuso" mezclado con "Mitsubishi" en
// GetModelsForMakeYear) aplican aquí tal cual — no se intentó arreglar
// en JS lo que ya se documentó como no resuelto en Python.

const VPIC_API_ROOT = "https://vpic.nhtsa.dot.gov/api/vehicles";
const DEFAULT_TIMEOUT_MS = 10000;

// Mismos dos tipos que _TIPOS_VEHICULO_AUTO en pipeline/fetch_vehicles.py.
const TIPOS_VEHICULO_AUTO = ["car", "multipurpose passenger vehicle (mpv)"];

// Rango de años razonable para el selector (vPIC decodifica VINs desde
// 1980 aprox.; se limita a partir de 1990 para no alargar el <select>
// con años poco útiles para piezas de reemplazo, y hasta el año actual + 1
// para cubrir modelos del año siguiente que ya se vendan).
export function getYearRange() {
  const currentYear = new Date().getFullYear();
  const years = [];
  for (let y = currentYear + 1; y >= 1990; y--) years.push(y);
  return years;
}

function _titleCaseIfUpper(name) {
  // Mismo criterio que fetch_vehicles.py: solo convierte a Title Case si
  // el nombre crudo viene todo en mayúsculas (vPIC siempre lo hace, pero
  // por si cambia, se respeta ya-mixto-case tal cual).
  return name === name.toUpperCase() ? titleCase(name) : name;
}

function titleCase(str) {
  return str
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

async function _fetchJSON(url, { timeoutMs = DEFAULT_TIMEOUT_MS, fetchImpl = fetch } = {}) {
  const controller = typeof AbortController !== "undefined" ? new AbortController() : null;
  const timer = controller ? setTimeout(() => controller.abort(), timeoutMs) : null;
  try {
    const res = await fetchImpl(url, controller ? { signal: controller.signal } : undefined);
    if (!res.ok) {
      throw new Error(`vPIC devolvió HTTP ${res.status} para ${url}`);
    }
    return await res.json();
  } finally {
    if (timer) clearTimeout(timer);
  }
}

/**
 * Lista de marcas de auto/SUV disponibles en vPIC, para el paso 1 del
 * drill-down. Mismo criterio de filtrado (unión car + MPV, deduplicado por
 * nombre) que get_all_makes() en pipeline/fetch_vehicles.py.
 *
 * @param {object} [opts] { timeoutMs, fetchImpl } — para tests.
 * @returns {Promise<Array<{id:number,name:string}>>} puede ser [] si falla
 *   la red; nunca lanza excepción (mismo patrón defensivo que el pipeline).
 */
export async function getAllMakes(opts = {}) {
  const porNombre = new Map();

  for (const tipo of TIPOS_VEHICULO_AUTO) {
    const url = `${VPIC_API_ROOT}/GetMakesForVehicleType/${encodeURIComponent(tipo)}?format=json`;
    try {
      const datos = await _fetchJSON(url, opts);
      const resultados = Array.isArray(datos && datos.Results) ? datos.Results : [];
      for (const item of resultados) {
        const nombreCrudo = (item.MakeName || "").trim();
        const idCrudo = item.MakeId;
        if (!nombreCrudo || idCrudo === undefined || idCrudo === null) continue;
        const nombre = _titleCaseIfUpper(nombreCrudo);
        if (!porNombre.has(nombre)) porNombre.set(nombre, idCrudo);
      }
    } catch (err) {
      console.warn(`vpicClient.getAllMakes: fallo consultando tipo "${tipo}":`, err);
      // Sigue con el otro tipo; si ambos fallan, se devuelve lo que haya
      // (puede ser lista vacía), igual que el pipeline hace con stderr.
    }
  }

  return Array.from(porNombre.entries())
    .map(([name, id]) => ({ id, name }))
    .sort((a, b) => a.name.localeCompare(b.name, "en", { sensitivity: "base" }));
}

/**
 * Modelos de `make` para el año `year`, para el paso 3 del drill-down
 * (después de elegir año). Mismo endpoint y mismo "problema conocido" que
 * get_models_for_make_year() en pipeline/fetch_vehicles.py: vPIC compara
 * por substring/prefijo de marca, así que puede incluir sub-marcas con
 * nombre similar (ej. "Mitsubishi Fuso" junto con "Mitsubishi").
 *
 * @param {string} make
 * @param {number} year
 * @param {object} [opts]
 * @returns {Promise<Array<{id:number,name:string}>>} [] si no hay datos o
 *   falla la red; nunca lanza excepción.
 */
export async function getModelsForMakeYear(make, year, opts = {}) {
  const marca = (make || "").trim();
  const anio = Number(year);
  if (!marca || !Number.isInteger(anio)) return [];

  const url =
    `${VPIC_API_ROOT}/GetModelsForMakeYear/make/${encodeURIComponent(marca)}` +
    `/modelyear/${anio}?format=json`;

  let datos;
  try {
    datos = await _fetchJSON(url, opts);
  } catch (err) {
    console.warn(`vpicClient.getModelsForMakeYear: fallo para ${marca}/${anio}:`, err);
    return [];
  }

  const resultados = Array.isArray(datos && datos.Results) ? datos.Results : [];
  const porNombre = new Map();
  for (const item of resultados) {
    const nombre = (item.Model_Name || "").trim();
    const idCrudo = item.Model_ID;
    if (!nombre || idCrudo === undefined || idCrudo === null) continue;
    if (!porNombre.has(nombre)) porNombre.set(nombre, idCrudo);
  }

  return Array.from(porNombre.entries())
    .map(([name, id]) => ({ id, name }))
    .sort((a, b) => a.name.localeCompare(b.name, "en", { sensitivity: "base" }));
}
