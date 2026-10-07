// site/js/dataClient.js
//
// ÚNICO módulo de site/ que puede leer data/build/*.json (regla de escalado,
// ver CONTRACTS.md sección "Regla de escalado"). Expone EXACTAMENTE estas
// tres funciones; ningún otro archivo de site/ debe hacer fetch directo a
// data/build/*.json:
//
//   - searchPart(q)   -> busca por part_number_norm o texto libre
//   - getPart(id)     -> una parte por id
//   - getVehicles()   -> lista de vehículos conocidos
//
// -----------------------------------------------------------------------
// POR QUÉ HAY FIXTURES DE DESARROLLO (leer antes de tocar esto)
// -----------------------------------------------------------------------
// Al momento de escribir este módulo, T-D1 (pipeline/build_index.py) todavía
// NO ha generado data/build/parts.json ni data/build/vehicles.json (ver
// TASKS.md). Solo existe data/build/categories.json (de T-F1, ya aprobado).
//
// Para no bloquear el frontend, cada loader intenta primero la ruta "real"
// dentro de site/ (site/data/build/<archivo>.json — ver nota de despliegue
// abajo) y, si el fetch falla (404, repo todavía sin ese archivo, o se abrió
// site/index.html con file:// y el navegador bloquea fetch), cae a una
// fixture de desarrollo embebida en site/js/fixtures/*.fixture.json que
// tiene EXACTAMENTE la misma forma que describe CONTRACTS.md.
//
// --> Cuando T-D1 entregue data/build/*.json reales (y se copien dentro de
//     site/data/build/, ver nota de despliegue), este módulo debería seguir
//     funcionando SIN CAMBIOS: el fetch real tendrá éxito y la fixture deja
//     de usarse. Si algún día el catálogo migra a Supabase u otra base,
//     el único módulo que cambia es este archivo (regla de escalado).
//
// NOTA DE DESPLIEGUE (asumido por el agente de frontend, pendiente de
// confirmar con T-D1 / T-G2): data/build/*.json vive en la raíz del repo,
// pero este sitio está pensado para servirse como una carpeta estática
// independiente (`cd site && python3 -m http.server`), donde rutas como
// "../data/build/parts.json" quedarían FUERA de la raíz servida. Por eso
// este módulo pide "./data/build/<archivo>.json" (es decir, dentro de
// site/). Para producción, se asume que el pipeline de build o el workflow
// de deploy (T-G2, deploy-site.yml) copiará data/build/*.json dentro de
// site/data/build/ antes de publicar. categories.json ya se copió a mano
// aquí porque T-F1/categorías ya está aprobado en main; ver
// problemas_conocidos del PR de T-E1 para más detalle de este supuesto.

import {
  categoriasParaSlug, filtrarArticulos, FRAGMENTOS_POR_SLUG, vehiculoEnCatalogo,
} from "./catalogoMap.js";

const REAL_PATHS = {
  parts: "./data/build/parts.json",
  vehicles: "./data/build/vehicles.json",
  categories: "./data/build/categories.json",
  // T-B19: el catálogo está PARTIDO. Esto es solo el índice (vehículo -> qué categorías tiene y
  // en qué archivo). Antes era un único archivo de 10,3 MB con 8 vehículos (~1,3 MB por visita,
  // y ~350 MB con la flota del país). Ahora cada visita baja el índice y el trozo que necesita.
  catalogo: "./data/build/catalogo/index.json",
};

// catalogo A PROPÓSITO no está aquí: si el archivo real no existe, esta función devuelve lista
// vacía en vez de tirar de una fixture. Un catálogo de mentira mostraría NÚMEROS DE PARTE
// INVENTADOS a un cliente real, y eso es peor que no mostrar nada: rompe la única promesa del
// producto. Las demás claves sí tienen fixture porque son datos de desarrollo (y el sitio avisa
// con un banner cuando se usan).
const FIXTURE_PATHS = {
  parts: "./js/fixtures/parts.fixture.json",
  vehicles: "./js/fixtures/vehicles.fixture.json",
  categories: "./js/fixtures/categories.fixture.json",
};

// Cache en memoria por clave para no repetir fetches en la misma sesión.
const _cache = new Map();

// Permite inyectar un "fetch" distinto en tests de Node (donde no hay
// fetch de navegador con rutas relativas a un servidor HTTP real).
let _fetchImpl = typeof fetch === "function" ? fetch : null;

export function _setFetchForTests(fn) {
  _fetchImpl = fn;
  _cache.clear();
  _cacheTrozos.clear();
}

async function _loadJSON(key) {
  if (_cache.has(key)) return _cache.get(key);

  const realUrl = REAL_PATHS[key];
  const fixtureUrl = FIXTURE_PATHS[key];

  let data = null;
  let usedFixture = false;

  try {
    const res = await _fetchImpl(realUrl);
    if (res && res.ok) {
      data = await res.json();
    } else {
      throw new Error(`fetch de ${realUrl} respondió status ${res && res.status}`);
    }
  } catch (_realErr) {
    // Archivo real no disponible todavía (T-D1 pendiente) o bloqueado por
    // file://. Caemos a la fixture de desarrollo documentada arriba.
    if (!fixtureUrl) {
      throw new Error(
        `dataClient: "${key}" no tiene fixture a propósito (ver REAL_PATHS): si el archivo real no está, no se inventa nada.`
      );
    }
    try {
      const res2 = await _fetchImpl(fixtureUrl);
      data = await res2.json();
      usedFixture = true;
    } catch (fixtureErr) {
      throw new Error(
        `dataClient: no se pudo cargar "${key}" ni desde ${realUrl} ni desde la fixture ${fixtureUrl}: ${fixtureErr.message}`
      );
    }
  }

  const result = { data, usedFixture };
  _cache.set(key, result);
  return result;
}

function _normalizePartNumber(raw) {
  // Misma regla que pipeline/normalize.py (CONTRACTS.md): mayúsculas, sin
  // espacios, guiones, puntos ni barras.
  return String(raw || "")
    .toUpperCase()
    .replace(/[\s\-.\/]/g, "");
}

// ---------------------------------------------------------------------------
// T-B14: el catálogo con número de parte (AUTODOC/TecDoc vía RapidAPI)
// ---------------------------------------------------------------------------
// Vive aquí y no en otro archivo porque este módulo es el ÚNICO que lee
// data/build/*.json (regla de escalado). La traducción de categorías y el
// emparejamiento de vehículos están en catalogoMap.js, que es lógica pura y se
// prueba sola.

/**
 * El vehículo del sitio, tal como lo entiende el catálogo (o null).
 */
export async function getVehiculoEnCatalogo(vehiculo) {
  const { catalogo } = await getCatalogo();
  return vehiculoEnCatalogo(catalogo, vehiculo);
}

/**
 * Carga el catálogo. Devuelve `{ catalogo: null }` si el archivo no está o falla: nunca lanza,
 * porque no tener catálogo es un estado válido (el sitio simplemente no muestra números).
 */
export async function getCatalogo() {
  try {
    const { data } = await _loadJSON("catalogo");
    return { catalogo: data || null };
  } catch (_err) {
    return { catalogo: null };
  }
}

// Cache de trozos ya descargados en esta sesión (un vehículo-categoría).
const _cacheTrozos = new Map();

async function _cargarTrozo(rutaRelativa) {
  if (_cacheTrozos.has(rutaRelativa)) return _cacheTrozos.get(rutaRelativa);
  const url = `./data/build/${rutaRelativa}`;
  const res = await _fetchImpl(url);
  if (!res || !res.ok) throw new Error(`fetch de ${url} respondió ${res && res.status}`);
  const datos = await res.json();
  _cacheTrozos.set(rutaRelativa, datos);
  return datos;
}

/**
 * Las piezas con número de parte para una categoría del sitio y un vehículo.
 * Descarga SOLO los trozos que corresponden a esa categoría (normalmente uno, ~6 KB).
 * @returns {Promise<Array<{numero,marca,pieza,foto,especificaciones,originales}>>}
 */
export async function getNumerosDeCategoria(vehiculo, slug) {
  const { catalogo } = await getCatalogo();
  if (!catalogo) return [];
  const entrada = vehiculoEnCatalogo(catalogo, vehiculo);
  if (!entrada) return [];

  const categorias = categoriasParaSlug(entrada, slug);
  if (!categorias.length) return [];

  const articulos = [];
  for (const cat of categorias) {
    try {
      const trozo = await _cargarTrozo(cat.archivo);
      for (const a of trozo.articulos || []) articulos.push(a);
    } catch (_err) {
      // Un trozo que no baja no puede tumbar la página: se ignora y se muestra lo que haya.
    }
  }
  return filtrarArticulos(articulos, slug);
}

/**
 * Qué categorías del sitio tienen número de parte para ese vehículo.
 * Se resuelve con el ÍNDICE, sin descargar ningún trozo.
 */
export async function getSlugsConNumeros(vehiculo) {
  const { catalogo } = await getCatalogo();
  if (!catalogo) return [];
  const entrada = vehiculoEnCatalogo(catalogo, vehiculo);
  if (!entrada) return [];
  return Object.keys(FRAGMENTOS_POR_SLUG).filter(
    (slug) => categoriasParaSlug(entrada, slug).length > 0
  );
}

/** Los números originales del fabricante para ese vehículo (se descarga solo si se pide). */
export async function getOriginalesDelVehiculo(vehiculo) {
  const { catalogo } = await getCatalogo();
  if (!catalogo) return [];
  const entrada = vehiculoEnCatalogo(catalogo, vehiculo);
  if (!entrada || !entrada.originales || !entrada.originales.archivo) return [];
  try {
    const trozo = await _cargarTrozo(entrada.originales.archivo);
    return trozo.originales || [];
  } catch (_err) {
    return [];
  }
}

/**
 * Busca partes por part_number_norm (match exacto tras normalizar) o, si no
 * hay match exacto, por texto libre en part_number, name o brand
 * (coincidencia parcial, sin distinguir mayúsculas/minúsculas).
 *
 * @param {string} q texto tecleado por el usuario
 * @returns {Promise<Array<object>>} partes que coinciden (puede ser vacío)
 */
export async function searchPart(q) {
  const query = String(q || "").trim();
  if (!query) return [];

  const { data: parts } = await _loadJSON("parts");
  const normQuery = _normalizePartNumber(query);

  const exact = parts.filter((p) => p.part_number_norm === normQuery);
  if (exact.length > 0) return exact;

  const needle = query.toLowerCase();
  return parts.filter((p) => {
    // other_names (agregado a CONTRACTS.md el 04/10/2026, campo opcional
    // de T-D2): sinónimos/nombres alternativos de la misma pieza. Se
    // matchea igual que name/brand, sin distinguir mayúsculas/minúsculas,
    // para que alguien que busca por el nombre "de la calle" (ej. "clip de
    // parrilla") encuentre la pieza aunque el nombre canónico sea otro.
    // Puede no existir (fixtures/partes viejas antes del campo) o venir
    // vacío: el `|| []` cubre ambos casos sin romper.
    const otherNames = Array.isArray(p.other_names) ? p.other_names : [];
    return (
      (p.part_number && p.part_number.toLowerCase().includes(needle)) ||
      (p.name && p.name.toLowerCase().includes(needle)) ||
      (p.brand && p.brand.toLowerCase().includes(needle)) ||
      (p.part_number_norm && p.part_number_norm.includes(normQuery)) ||
      otherNames.some((n) => String(n || "").toLowerCase().includes(needle))
    );
  });
}

/**
 * @param {string} id
 * @returns {Promise<object|null>} la parte con ese id, o null si no existe.
 */
export async function getPart(id) {
  if (!id) return null;
  const { data: parts } = await _loadJSON("parts");
  return parts.find((p) => p.id === id) || null;
}

/**
 * @returns {Promise<Array<object>>} todos los vehículos conocidos por el
 * catálogo (uno por combinación marca/modelo/año/versión ya resuelta).
 */
export async function getVehicles() {
  const { data: vehicles } = await _loadJSON("vehicles");
  return vehicles;
}

/**
 * NO forma parte de la superficie de 3 funciones del contrato (searchPart,
 * getPart, getVehicles): es una ayuda interna para que categoryTree.js no
 * tenga que leer categories.json por su cuenta. Sigue siendo este único
 * archivo el que hace fetch; categoryTree.js solo llama a esta función.
 * Si el líder prefiere que esto no exista, categoryTree.js puede recibir
 * las categorías embebidas como constante en vez de este helper — se deja
 * así por ahora para no duplicar la lista de categorías en dos archivos.
 *
 * @returns {Promise<Array<{slug:string,name_es:string,svg:string}>>}
 */
export async function getCategories() {
  const { data: categories } = await _loadJSON("categories");
  return categories;
}

/**
 * Indica si la última carga de una clave usó la fixture de desarrollo en
 * vez del archivo real. Solo para mostrar un aviso discreto en la UI
 * ("datos de ejemplo, T-D1 todavía no entrega los reales") — no afecta la
 * lógica de negocio.
 */
export async function _isUsingFixture(key) {
  const entry = await _loadJSON(key);
  return entry.usedFixture;
}

// -----------------------------------------------------------------------
// EXTENSIONES más allá de los 3 nombres literales del contrato.
// -----------------------------------------------------------------------
// CONTRACTS.md pide exactamente searchPart/getPart/getVehicles como la
// "superficie" pública, pensada sobre todo para el flujo "ya tengo mi
// número de parte". La tarea de T-E1 también pide un flujo VIN → árbol de
// categorías por vehículo, que necesita dos consultas que el contrato no
// previó: (a) encontrar el vehículo cuyo VIN coincide, y (b) listar las
// piezas de una categoría que ajustan a un vehículo. En vez de inventar
// fetches nuevos fuera de este archivo (que rompería la regla "ningún otro
// archivo de site/ hace fetch directo a data/build/*.json"), se agregan
// aquí dos funciones más, documentadas como una desviación explícita a
// revisar por el líder (ver problemas_conocidos del PR de T-E1). Si el
// líder prefiere que esto viva en otro lado (p. ej. un índice separado que
// construya T-D1), es un cambio contenido a este archivo.

/**
 * Busca un vehículo cuyo VIN coincide con el dado.
 *
 * El contrato real de vehicles.json (T-A1/T-D1, ver CONTRACTS.md) NO tiene
 * un campo `vin` separado: el VIN viaja codificado dentro de `id` con el
 * formato `vin-<VIN>` (ver pipeline/fetch_vehicles.py e id real generado
 * por build_index.py, ej. "vin-JA4AP3AU0LU000302"). Por eso esta función
 * primero intenta extraer el VIN del `id` con ese patrón; si un vehículo
 * no sigue ese formato (p. ej. una fixture antigua con id tipo
 * "veh-marca-modelo-año"), cae a comparar contra un campo `vin` opcional
 * si existe, para no romper fixtures previas.
 *
 * @param {string} vin ya limpio (ver site/js/vin.js)
 * @returns {Promise<object|null>}
 */
export async function matchVehicleByVIN(vin) {
  const vehicles = await getVehicles();
  const needle = String(vin || "").trim().toUpperCase();
  if (!needle) return null;

  return (
    vehicles.find((v) => {
      const idMatch = /^vin-(.+)$/i.exec(String(v.id || ""));
      if (idMatch && idMatch[1].toUpperCase() === needle) return true;
      return (v.vin || "").toUpperCase() === needle;
    }) || null
  );
}

/**
 * Busca un vehículo por marca/modelo/año exactos (sin distinguir
 * mayúsculas/minúsculas ni espacios extra), para el flujo "elige tu
 * vehículo sin VIN" (drill-down marca → año → modelo, ver
 * site/js/vehiclePicker.js). Igual que matchVehicleByVIN, es una extensión
 * del contrato original de CONTRACTS.md, documentada aquí y en el PR de
 * T-E2 (drill-down UI).
 *
 * Nota: el drill-down llega a vPIC (vía site/js/vpicClient.js, un módulo
 * aparte — ver su comentario de cabecera para la excepción deliberada a la
 * regla de escalado) y por lo tanto a nombres de marca/modelo con la
 * capitalización/ortografía de vPIC. Esta función normaliza ambos lados
 * (trim + mayúsculas) para que "Mitsubishi"/"mitsubishi" o "Outlander
 * Sport"/"OUTLANDER SPORT" coincidan igual con lo que haya en
 * vehicles.json.
 *
 * @param {string} make
 * @param {string} model
 * @param {number|string} year
 * @returns {Promise<object|null>} el vehículo si existe en el catálogo
 *   (data/build/vehicles.json o su fixture), o null si no hay match. Null
 *   NO es un error: significa "todavía no tenemos piezas para ese
 *   vehículo en el catálogo", algo esperado mientras el catálogo crece.
 */
export async function matchVehicleByMakeModelYear(make, model, year) {
  const vehicles = await getVehicles();
  const needleMake = String(make || "").trim().toUpperCase();
  const needleModel = String(model || "").trim().toUpperCase();
  const needleYear = Number(year);
  if (!needleMake || !needleModel || !Number.isInteger(needleYear)) return null;

  return (
    vehicles.find((v) => {
      const vMake = String(v.make || "").trim().toUpperCase();
      const vModel = String(v.model || "").trim().toUpperCase();
      const vYear = Number(v.year);
      return vMake === needleMake && vModel === needleModel && vYear === needleYear;
    }) || null
  );
}

/**
 * Piezas que ajustan a un vehículo (por fitment_ids) y, opcionalmente, que
 * pertenecen a una categoría dada.
 * @param {string} vehicleId
 * @param {string|null} categorySlug si se omite, regresa todas las
 *   categorías que tengan piezas para ese vehículo.
 * @returns {Promise<Array<object>>}
 */
export async function getPartsByFitment(vehicleId, categorySlug = null) {
  const { data: parts } = await _loadJSON("parts");
  return parts.filter((p) => {
    const fits = Array.isArray(p.fitment_ids) && p.fitment_ids.includes(vehicleId);
    if (!fits) return false;
    if (categorySlug && p.category !== categorySlug) return false;
    return true;
  });
}

/**
 * Piezas de una categoría, SIN filtrar por vehículo (T-E5: permite
 * "navegar por categoría" desde el home antes de resolver un vehículo,
 * ver decisión de diseño en el PR de T-E3/T-E5). Extensión del mismo
 * estilo que getPartsByFitment/matchVehicleByVIN: no está en la
 * superficie literal de CONTRACTS.md, pero sigue viviendo solo aquí para
 * no romper la regla de escalado (ningún otro archivo de site/ hace
 * fetch directo a data/build/*.json).
 *
 * @param {string} categorySlug
 * @returns {Promise<Array<object>>} piezas de esa categoría (puede ser
 *   vacío si el catálogo todavía no tiene piezas ahí).
 */
/**
 * Resumen del catálogo para la banda de confianza del inicio (dirección B).
 *
 * Vive aquí y no en confianza.js a propósito: este módulo es el ÚNICO de site/
 * que puede leer data/build/*.json (regla de escalado, CONTRACTS.md).
 *
 * @returns {Promise<{partes:number, ofertas:number, categorias:number, usandoFixture:boolean}>}
 */
export async function getResumenCatalogo() {
  const [partesRes, categoriasRes] = await Promise.all([
    _loadJSON("parts"),
    _loadJSON("categories"),
  ]);

  const partes = Array.isArray(partesRes.data) ? partesRes.data : [];
  const categorias = Array.isArray(categoriasRes.data) ? categoriasRes.data : [];

  const ofertas = partes.reduce(
    (total, parte) => total + ((parte && parte.offers) || []).length,
    0
  );

  return {
    partes: partes.length,
    ofertas,
    categorias: categorias.length,
    usandoFixture: Boolean(partesRes.usedFixture || categoriasRes.usedFixture),
  };
}

export async function getPartsByCategory(categorySlug) {
  if (!categorySlug) return [];
  const { data: parts } = await _loadJSON("parts");
  return parts.filter((p) => p.category === categorySlug);
}
