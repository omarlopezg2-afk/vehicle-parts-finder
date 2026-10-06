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
// lleguen al mismo tipo de resultado para una misma marca/año. El
// "problema conocido" de marcas límite tipo camión en getAllMakes
// (Freightliner, Blue Bird, Orion Bus colándose en car+MPV) se resolvió
// en T-A3 con `MARCAS_INDUSTRIALES_EXCLUIDAS` (idéntica a
// `_MARCAS_INDUSTRIALES_EXCLUIDAS` en fetch_vehicles.py; ver ese
// comentario para el razonamiento completo). El otro "problema conocido"
// documentado allá ("Mitsubishi Fuso" mezclado con "Mitsubishi" en
// GetModelsForMakeYear) sigue sin resolver — no se intentó arreglar en
// JS lo que ya se documentó como no resuelto en Python, porque T-A3 solo
// tocó getAllMakes/get_all_makes.

const VPIC_API_ROOT = "https://vpic.nhtsa.dot.gov/api/vehicles";
const DEFAULT_TIMEOUT_MS = 10000;

// Mismos dos tipos que _TIPOS_VEHICULO_AUTO en pipeline/fetch_vehicles.py.
const TIPOS_VEHICULO_AUTO = ["car", "multipurpose passenger vehicle (mpv)"];

// T-A3 — MISMO CRITERIO REPLICADO EN pipeline/fetch_vehicles.py
// (_MARCAS_INDUSTRIALES_EXCLUIDAS / get_all_makes). Si se cambia esta
// lista, cambiar la de allá IDÉNTICA, o Python y JS mostrarán marcas
// distintas para el mismo usuario (camino VIN vs camino drill-down).
//
// POR QUÉ EXISTE ESTA LISTA (investigación contra la API real de vPIC, no
// asumida — ver PR de T-A3 para el detalle completo):
// La unión car+MPV (arriba) ya filtra la enorme mayoría de fabricantes
// industriales: de ~207 marcas que vPIC devuelve bajo el tipo "truck",
// solo 3 "se cuelan" también en car+MPV al momento de escribir esto
// (verificado a mano contra GetMakesForVehicleType/car, .../multipurpose
// passenger..., y .../truck): FREIGHTLINER, BLUE BIRD y ORION BUS. Las
// ~204 restantes (Peterbilt, Kenworth, Mack, International, Western Star,
// Autocar, Capacity Trucks, Thomas Built, Oshkosh, Navistar, Hino, etc.)
// NUNCA aparecen en car/MPV y ya quedan fuera solo con el filtro de
// tipos — no necesitan estar en esta lista para que el resultado hoy sea
// correcto, pero se agregan igual como lista de exclusión EXPLÍCITA (no
// heurística) para no depender de que vPIC nunca reclasifique una marca
// de camión/bus hacia car/MPV en el futuro; es más fácil de auditar y de
// extender a mano que inventar una regla automática.
//
// Fuente de la lista: fabricantes de camiones pesados/semirremolques/
// buses comerciales ampliamente conocidos (dominio público, ninguno vende
// autos ni SUV de consumo), más los 3 confirmados arriba que sí aparecen
// en car/MPV hoy. Comparación exacta por nombre en MAYÚSCULAS tal como lo
// devuelve vPIC (NO por substring, para no atrapar por accidente nombres
// legítimos que contienen la palabra, ej. "SPRINTER (DODGE OR
// FREIGHTLINER)" es una van MPV real de Mercedes-Benz/Dodge y debe
// quedarse).
//
// MARCAS LÍMITE que se decidió NO excluir (ver razonamiento en el PR):
// - ISUZU: vPIC la clasifica bajo car Y bajo MPV (no solo truck), y
//   vendió SUVs de consumo en EE. UU. por décadas (Trooper, Rodeo, Axiom,
//   Ascender) hasta 2009. Aunque hoy en EE. UU. solo vende camiones
//   medianos comerciales, el filtro aquí es sobre el catálogo vPIC (que
//   incluye histórico), así que se mantiene DENTRO.
const MARCAS_INDUSTRIALES_EXCLUIDAS = new Set([
  // Confirmadas: aparecen en car/MPV hoy pero son 100% industriales.
  "FREIGHTLINER",
  "BLUE BIRD",
  "ORION BUS",
  // Defensa en profundidad: fabricantes de camiones pesados/buses
  // ampliamente conocidos que hoy NO aparecen en car/MPV (confirmado
  // contra la API real), pero se excluyen explícitamente por si vPIC
  // cambia su clasificación más adelante.
  "PETERBILT",
  "KENWORTH",
  "MACK",
  "INTERNATIONAL",
  "WESTERN STAR",
  "AUTOCAR",
  "AUTOCAR INDUSTRIES",
  "CAPACITY TRUCKS",
  "THOMAS BUILT",
  "OSHKOSH",
  "NAVISTAR",
  "HINO",
  "SPARTAN MOTORS",
  "PIERCE MANUFACTURING",
  "CRANE CARRIER COMPANY (CCC)",
  "E-ONE",
  "KALMAR",
  "DENNIS EAGLE",
]);

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
 * nombre, MENOS la lista explícita de fabricantes industriales en
 * `MARCAS_INDUSTRIALES_EXCLUIDAS`) que get_all_makes() en
 * pipeline/fetch_vehicles.py.
 *
 * FILTRO ADICIONAL (T-A3): la unión car+MPV por sí sola deja colar algunos
 * fabricantes 100% industriales (camiones pesados/buses comerciales) que
 * vPIC también cataloga bajo esos tipos — confirmado contra la API real:
 * FREIGHTLINER, BLUE BIRD y ORION BUS aparecen en car/MPV junto a
 * Toyota/BMW/Mitsubishi. Por eso, después de la unión, se excluyen por
 * nombre exacto las marcas en `MARCAS_INDUSTRIALES_EXCLUIDAS` (lista
 * explícita y auditable, no heurística — ver el comentario junto a esa
 * constante para el razonamiento completo y las marcas límite que se
 * decidió mantener, ej. Isuzu).
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
        if (MARCAS_INDUSTRIALES_EXCLUIDAS.has(nombreCrudo.toUpperCase())) continue;
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
 * Decodifica un VIN completo (17 caracteres) contra el servicio público de la
 * NHTSA (vPIC) y devuelve los datos del vehículo que ese VIN identifica.
 *
 * POR QUÉ EXISTE: hasta ahora el flujo VIN dependía por completo de
 * data/build/vehicles.json (matchVehicleByVIN) — solo funcionaba si ESE VIN ya
 * estaba en nuestro catálogo. Con el decodificador, **cualquier** VIN válido del
 * mercado estadounidense identifica su vehículo (marca, modelo, año, versión,
 * carrocería, motor, tracción, transmisión), y con eso se busca el fitment por
 * año/marca/modelo, que es exactamente como lo pide el `compatibility_filter` de
 * eBay (esa API NO acepta VIN — ver docs/placa-y-chasis-fuentes.md).
 *
 * Es la pieza que hace posible el texto de la portada: "pega el VIN de tu
 * matrícula". Verificado a mano: el VIN real de un Mitsubishi Outlander Sport
 * 2020 devuelve 154 campos con ErrorCode 0 (dígito verificador correcto).
 *
 * @param {string} vin VIN ya limpio (ver site/js/vin.js -> cleanVIN)
 * @param {object} [opts] { timeoutMs, fetchImpl } — para tests
 * @returns {Promise<object|null>} null si la red falla, si el VIN no tiene 17
 *   caracteres o si vPIC no devuelve nada; nunca lanza excepción.
 */
export async function decodeVIN(vin, opts = {}) {
  const limpio = String(vin || "").trim().toUpperCase().replace(/\s+/g, "");
  if (!/^[A-Z0-9]{17}$/.test(limpio)) return null;

  const url = `${VPIC_API_ROOT}/decodevinvalues/${encodeURIComponent(limpio)}?format=json`;
  let datos;
  try {
    datos = await _fetchJSON(url, opts);
  } catch (err) {
    console.warn(`vpicClient.decodeVIN: fallo para ${limpio}:`, err);
    return null;
  }

  const crudo = Array.isArray(datos && datos.Results) ? datos.Results[0] : null;
  if (!crudo) return null;

  const texto = (v) => String(v == null ? "" : v).trim();
  return {
    vin: limpio,
    // vPIC entrega ErrorCode "0" cuando el VIN se decodifica limpio, lo que
    // incluye que el dígito verificador (9ª posición) cuadre.
    valido: texto(crudo.ErrorCode) === "0",
    make: _titleCaseIfUpper(texto(crudo.Make)),
    model: _titleCaseIfUpper(texto(crudo.Model)),
    year: texto(crudo.ModelYear),
    trim: texto(crudo.Trim),
    series: texto(crudo.Series),
    bodyClass: texto(crudo.BodyClass),
    driveType: texto(crudo.DriveType),
    engineCylinders: texto(crudo.EngineCylinders),
    displacementL: texto(crudo.DisplacementL),
    engineHP: texto(crudo.EngineHP),
    fuelType: texto(crudo.FuelTypePrimary),
    transmission: texto(crudo.TransmissionStyle),
    plantCountry: texto(crudo.PlantCountry),
    errorText: texto(crudo.ErrorText),
  };
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
