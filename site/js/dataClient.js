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

const REAL_PATHS = {
  parts: "./data/build/parts.json",
  vehicles: "./data/build/vehicles.json",
  categories: "./data/build/categories.json",
};

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
    return (
      (p.part_number && p.part_number.toLowerCase().includes(needle)) ||
      (p.name && p.name.toLowerCase().includes(needle)) ||
      (p.brand && p.brand.toLowerCase().includes(needle)) ||
      (p.part_number_norm && p.part_number_norm.includes(normQuery))
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
 * Busca un vehículo cuyo campo de desarrollo "vin" (ver fixture, NO existe
 * en el contrato real de vehicles.json) coincide con el VIN dado.
 * @param {string} vin ya limpio (ver site/js/vin.js)
 * @returns {Promise<object|null>}
 */
export async function matchVehicleByVIN(vin) {
  const vehicles = await getVehicles();
  const needle = String(vin || "").trim().toUpperCase();
  return vehicles.find((v) => (v.vin || "").toUpperCase() === needle) || null;
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
