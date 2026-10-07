// site/js/catalogoMap.js
//
// T-B14: traducir el catálogo de AUTODOC al lenguaje del sitio.
//
// EL PROBLEMA QUE RESUELVE
// AUTODOC (TecDoc) nombra las categorías en su propio idioma técnico en inglés —"Disc Brake",
// "Lubrication", "Air Supply", "Wiper Blade/-Rubber"— y el sitio tiene sus propias categorías en
// español ("pastillas-freno", "filtro-aceite", "limpiaparabrisas"...). Sin traducción, el número de
// parte existe pero no aparece donde el visitante lo busca: es exactamente lo que pasó el
// 07/10/2026, cuando el usuario buscó "Filtro de aceite" y el sitio dijo que no tenía nada, aunque
// el catálogo guardado ya tuviera 9 filtros de aceite para su motor.
//
// POR QUÉ SE TRADUCE POR EL NOMBRE DE LA PIEZA Y NO POR LA CATEGORÍA
// Las categorías de AUTODOC son **grupos** y son ambiguas: "Lubrication" contiene juntas del tapón
// de vaciado, juntas del cárter y filtros de aceite; "Disc Brake" contiene pastillas, discos y
// pinzas. El nombre de la pieza ("Brake Pad Set, disc brake", "Oil Filter") sí es inequívoco. Por
// eso cada categoría del sitio declara los **fragmentos del nombre de la pieza** que le pertenecen.
//
// REGLAS
//  - Un fragmento que no aparece en ninguna pieza simplemente no da resultados (nada de relleno).
//  - Los fragmentos se comparan normalizados (minúsculas, sin acentos) y se buscan como subcadena
//    del nombre de la pieza, que es como viene de la API ("Brake Pad Set, disc brake").
//  - Una categoría del sitio puede estar cubierta por VARIAS categorías de AUTODOC a la vez.

/**
 * Categoría del sitio -> fragmentos del nombre de la pieza (en inglés, tal como los da AUTODOC).
 * Si una categoría del sitio no está aquí, es que el catálogo no la cubre todavía (p. ej. batería:
 * AUTODOC la tiene, pero nuestro recorrido del 07/10/2026 no la trajo). No se inventa nada.
 */
export const FRAGMENTOS_POR_SLUG = {
  "pastillas-freno": ["brake pad"],
  // OJO: aquí NO va "disc brake". Ese texto aparece dentro del nombre de las pastillas
  // ("Brake Pad Set, disc brake"), así que la página de discos mostraba pastillas — lo cazó la
  // verificación en navegador del 07/10/2026. "brake disc" sí es inequívoco.
  "discos-freno": ["brake disc"],
  caliper: ["brake caliper"],
  "manguera-freno": ["brake hose", "brake line"],
  "filtro-aceite": ["oil filter"],
  "filtro-aire": ["air filter"],
  "filtro-cabina": ["cabin filter", "pollen filter"],
  "filtro-combustible": ["fuel filter"],
  limpiaparabrisas: ["wiper blade", "wiper arm", "wiper rubber"],
  bujia: ["spark plug", "glow plug"],
  amortiguador: ["shock absorber", "suspension strut"],
  radiador: ["radiator"],
  "bomba-agua": ["water pump"],
  termostato: ["thermostat"],
  rotula: ["ball joint", "control arm", "track control"],
  "terminal-direccion": ["tie rod", "track rod"],
  "rodamiento-rueda": ["wheel bearing"],
  correa: ["timing belt", "v-ribbed belt", "drive belt", "tensioner"],
  alternador: ["alternator"],
  "motor-arranque": ["starter"],
  "bomba-combustible": ["fuel pump"],
  "sensor-oxigeno": ["lambda sensor", "oxygen sensor"],
  "bobina-encendido": ["ignition coil"],
  "soporte-motor": ["engine mount", "engine mounting"],
};

/** Normaliza texto para comparar (minúsculas, sin acentos). No borra paréntesis ni números. */
export function normalizar(texto) {
  return String(texto || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Encuentra el vehículo del catálogo que corresponde al vehículo del sitio.
 * Primero por VIN (exacto y sin ambigüedad) y, si el vehículo del sitio no lo trae, por
 * año + marca + modelo normalizados.
 */
export function vehiculoEnCatalogo(catalogo, vehiculo) {
  const vehiculos = (catalogo && catalogo.vehiculos) || [];
  if (!vehiculo) return null;

  const vin = String(vehiculo.vin || "").trim().toUpperCase();
  if (vin) {
    const porVin = vehiculos.find((v) => String(v.vin || "").trim().toUpperCase() === vin);
    if (porVin) return porVin;
  }

  const marca = normalizar(vehiculo.make || vehiculo.marca);
  const modelo = normalizar(vehiculo.model || vehiculo.modelo);
  const anio = String(vehiculo.year || vehiculo.anio || "").trim();
  if (!marca || !modelo || !anio) return null;

  return (
    vehiculos.find((v) => {
      const d = v.vehiculo || {};
      const mismaMarca = normalizar(d.make) === marca;
      const mismoAnio = String(d.year || "").trim() === anio;
      const suyo = normalizar(d.model);
      const mismoModelo = suyo === modelo || suyo.includes(modelo) || modelo.includes(suyo);
      return mismaMarca && mismoAnio && mismoModelo;
    }) || null
  );
}

/**
 * Las piezas del catálogo que corresponden a una categoría del sitio, para ese vehículo.
 * Devuelve [] si no hay nada: nunca rellena.
 *
 * @returns {Array<{numero:string, marca:string, pieza:string, foto:string|null}>}
 */
export function piezasDeCategoria(catalogo, vehiculo, slug) {
  const fragmentos = FRAGMENTOS_POR_SLUG[slug];
  if (!fragmentos || !fragmentos.length) return [];

  const entrada = vehiculoEnCatalogo(catalogo, vehiculo);
  if (!entrada) return [];

  const buscados = fragmentos.map(normalizar);
  const salida = [];
  const vistos = new Set();

  for (const cat of entrada.categorias || []) {
    for (const art of cat.articulos || []) {
      const nombre = normalizar(art.pieza);
      if (!buscados.some((f) => nombre.includes(f))) continue;
      // La misma pieza puede venir dos veces de AUTODOC con distinta marca (es legítimo), pero
      // no queremos duplicar exactamente el mismo número + marca.
      const clave = `${art.numero}|${art.marca}`.toUpperCase();
      if (vistos.has(clave)) continue;
      vistos.add(clave);
      salida.push({
        numero: art.numero,
        marca: art.marca,
        pieza: art.pieza,
        foto: art.foto || null,
        // T-B16: lo que convierte el número en "la pieza exacta". Van tal cual desde el catálogo
        // (pueden venir vacíos: solo las piezas detalladas los tienen).
        especificaciones: art.especificaciones || null,
        originales: Array.isArray(art.oem) ? art.oem : [],
      });
    }
  }

  // Ordenadas por marca y número: estable y fácil de leer en pantalla.
  salida.sort((a, b) => a.marca.localeCompare(b.marca, "es") || a.numero.localeCompare(b.numero, "es"));
  return salida;
}

/**
 * Qué categorías del sitio tienen números para ese vehículo. Sirve para avisar en las fichas y
 * para no mostrar un bloque vacío.
 *
 * @returns {string[]} slugs con al menos una pieza
 */
export function slugsConNumeros(catalogo, vehiculo) {
  return Object.keys(FRAGMENTOS_POR_SLUG).filter(
    (slug) => piezasDeCategoria(catalogo, vehiculo, slug).length > 0
  );
}
