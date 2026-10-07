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
 * TODAS las entradas del catálogo que corresponden a ese vehículo (T-B22).
 *
 * POR QUÉ: el catálogo se arma POR VARIANTE (motor) y la mayoría de los modelos-año tienen dos
 * (medido en el catálogo del 07/10/2026: 123 de 127). `vehiculoEnCatalogo` devolvía la primera, así
 * que el sitio podía mostrar las pastillas del 1.8 a quien tiene el 2.0 sin decirlo. Un número
 * exacto para el motor equivocado es peor que no dar número: hay que saber que hay varias.
 *
 * @returns {Array<object>} entradas del índice; vacío si no hay ninguna (nunca inventa).
 */
export function vehiculosEnCatalogo(catalogo, vehiculo) {
  const vehiculos = (catalogo && catalogo.vehiculos) || [];
  if (!vehiculo) return [];

  const vin = String(vehiculo.vin || "").trim().toUpperCase();
  if (vin) {
    const porVin = vehiculos.filter((v) => String(v.vin || "").trim().toUpperCase() === vin);
    if (porVin.length) return porVin;
  }

  const marca = normalizar(vehiculo.make || vehiculo.marca);
  const modelo = normalizar(vehiculo.model || vehiculo.modelo);
  const anio = String(vehiculo.year || vehiculo.anio || "").trim();
  if (!marca || !modelo || !anio) return [];

  return vehiculos.filter((v) => {
    const d = v.vehiculo || {};
    const mismaMarca = normalizar(d.make) === marca;
    const mismoAnio = String(d.year || "").trim() === anio;
    const suyo = normalizar(d.model);
    const mismoModelo = suyo === modelo || suyo.includes(modelo) || modelo.includes(suyo);
    return mismaMarca && mismoAnio && mismoModelo;
  });
}

/**
 * El combustible, en el idioma del cliente (T-B24).
 *
 * La API (TecDoc, en inglés británico) dice `Petrol`, `Petrol/Liquified Petroleum Gas (LPG)`… y eso
 * NO se le puede mostrar a nadie tal cual. Peor: en República Dominicana "gas" se usa para las dos
 * cosas — "voy a echar gas" (gasolina) y "mi carro es a gas" (GLP) —, así que **nunca** se escribe
 * "gas" a secas: sería pedirle al cliente que adivine. Siempre "Gasolina" o "Gas (GLP)", completos.
 *
 * Tabla acordada con el usuario (07/10/2026) — no cambiarla sin hablarlo:
 *   Petrol                             -> Gasolina
 *   Petrol/Liquified Petroleum Gas (LPG) -> Gasolina / Gas (GLP)
 *   Diesel                             -> Diésel
 *   Petrol/Ethanol                     -> Gasolina / Etanol
 *   Petrol/Electric                    -> Híbrido
 *   Gasoline                           -> Gasolina
 * Un valor nuevo se muestra tal cual (mejor raro que mentir), pero esta lista es la buena.
 *
 * "Gasoline" se añadió el 07/10/2026 al rellenar el combustible del catálogo (T-B25): es la
 * palabra que usa la ficha del VIN (NHTSA/vPIC) para lo mismo que TecDoc llama "Petrol". Sin
 * esta línea el visitante vería "Gasoline" en inglés — y el combustible es justo uno de los
 * tres datos que no se pueden callar.
 */
export function traducirCombustible(valor) {
  const v = String(valor || "").trim();
  if (!v) return "";
  const tabla = {
    Petrol: "Gasolina",
    Gasoline: "Gasolina",
    "Petrol/Liquified Petroleum Gas (LPG)": "Gasolina / Gas (GLP)",
    Diesel: "Diésel",
    "Petrol/Ethanol": "Gasolina / Etanol",
    "Petrol/Electric": "Híbrido",
  };
  // Comparación sin distinguir mayúsculas: la API no siempre respeta el formato.
  const clave = Object.keys(tabla).find((k) => k.toLowerCase() === v.toLowerCase());
  return clave ? tabla[clave] : v;
}

/** La cilindrada con un decimal: "2.0 L", no "2 L" (es como la escribe el mercado). */
function litros(valor) {
  const n = Number(valor);
  return Number.isFinite(n) ? n.toFixed(1) : String(valor);
}

/**
 * Cómo se llama esta variante para que la persona la reconozca (T-B22).
 * Se arma con lo que trae el catálogo: cilindrada y potencia si están, y si no el nombre del motor
 * tal como lo da TecDoc ("1.3 Dual-VVTi (NRE180_)"). Nunca queda vacío: si no hay dato se dice que
 * es la única conocida, que es la verdad.
 */
export function etiquetaDeVariante(entrada) {
  if (!entrada) return "";
  const v = entrada.vehiculo || {};
  const partes = [];
  if (v.cilindrada_l != null && v.cilindrada_l !== "") partes.push(`${litros(v.cilindrada_l)} L`);
  // PS y HP NO son lo mismo (un PS es ~0,986 HP): cada uno se dice con su unidad. El catálogo
  // guarda lo que da TecDoc (PS) y la ficha del VIN lo que da la NHTSA (HP).
  if (v.potencia_ps != null && v.potencia_ps !== "") partes.push(`${v.potencia_ps} PS`);
  if (v.potencia_hp != null && v.potencia_hp !== "") partes.push(`${v.potencia_hp} HP`);
  if (v.combustible) partes.push(traducirCombustible(v.combustible));
  if (v.motor) partes.push(String(v.motor));
  if (!partes.length && v.variante) partes.push(String(v.variante));
  if (!partes.length && entrada.nombres && entrada.nombres.variante) partes.push(String(entrada.nombres.variante));
  return partes.join(" · ") || "variante única";
}

/**
 * Cómo se llama el mercado del catálogo (T-B25).
 *
 * POR QUÉ: la regla del proyecto es que ningún número se enseña sin decir de qué mercado es. El
 * catálogo se resolvió con un filtro de país y ese filtro viaja en el índice (`pais_filtro`); aquí
 * se traduce a una palabra. Un país que no esté en la tabla se muestra por su número ("Mercado 214")
 * — nunca con un nombre inventado.
 */
const MERCADOS = {
  67: "República Dominicana",
  261: "Estados Unidos",
};

export function nombreDeMercado(pais) {
  if (pais === null || pais === undefined || pais === "") return "";
  const n = Number(pais);
  if (Number.isFinite(n) && MERCADOS[n]) return MERCADOS[n];
  return `Mercado ${pais}`;
}

/**
 * Las variantes de un vehículo, listas para el selector (T-B22/T-B25).
 *
 * Recibe las entradas del índice (`vehiculosEnCatalogo`) y devuelve `{clave, etiqueta}`. Y resuelve
 * un caso que se ve al hacerlo: dos variantes pueden quedar con la MISMA etiqueta (mismo motor y
 * mismo combustible en dos generaciones). Si el visitante ve dos botones iguales no puede elegir,
 * así que a las repetidas se les añade el nombre con el que las llama el catálogo.
 */
export function etiquetasDeVariantes(entradas) {
  const lista = (entradas || []).map((e) => ({ clave: e.clave, etiqueta: etiquetaDeVariante(e) }));
  const veces = new Map();
  for (const item of lista) veces.set(item.etiqueta, (veces.get(item.etiqueta) || 0) + 1);
  return lista.map((item, i) => {
    if (veces.get(item.etiqueta) < 2) return item;
    const crudo = (entradas[i].vehiculo || {}).variante || (entradas[i].nombres || {}).variante || "";
    return crudo && !item.etiqueta.includes(crudo)
      ? { ...item, etiqueta: `${item.etiqueta} · ${crudo}` }
      : item;
  });
}

/**
 * De qué mercado y de qué motor es un número de parte, en una línea (T-B25).
 *
 * Es la etiqueta que va ENCIMA del bloque de piezas. Los tres datos son obligatorios: mercado,
 * motor y combustible. Si al catálogo le falta uno, se dice que falta — nunca se calla ni se
 * supone ("si es un Corolla será gasolina" es exactamente lo que no se puede hacer).
 */
export function etiquetaDeVarianteCompleta(entrada, pais, etiquetaMotor) {
  const v = (entrada && entrada.vehiculo) || {};
  const partes = [];
  const mercado = nombreDeMercado(pais);
  if (mercado) partes.push(`Mercado: ${mercado}`);
  partes.push(`Motor: ${etiquetaMotor || etiquetaDeVariante(entrada)}`);
  partes.push(
    v.combustible
      ? `Combustible: ${traducirCombustible(v.combustible)}`
      : "Combustible: sin confirmar en el catálogo"
  );
  return partes.join(" · ");
}

/**
 * T-B19: qué categorías del catálogo (archivos ya partidos) corresponden a una categoría del
 * sitio. El catálogo guarda las categorías con el nombre técnico de AUTODOC ("Disc Brake",
 * "Lubrication"); el sitio usa sus propios slugs ("pastillas-freno"). Se emparejan con los mismos
 * fragmentos de nombre de pieza que el resto del módulo, así que hay una sola fuente de verdad.
 *
 * @param {object} vehiculoCatalogo entrada del índice (catalogo/index.json)
 * @param {string} slug categoría del sitio
 * @returns {Array<{slug:string, nombre:string, archivo:string, articulos:number}>}
 */
export function categoriasParaSlug(vehiculoCatalogo, slug) {
  const fragmentos = FRAGMENTOS_POR_SLUG[slug];
  if (!fragmentos || !fragmentos.length || !vehiculoCatalogo) return [];
  const buscados = fragmentos.map(normalizar);
  return (vehiculoCatalogo.categorias || []).filter((c) => {
    // 1) el término con el que se pidió la categoría ("oil filter", "brake pad"): es el fiable.
    const pedido = normalizar(c.buscado || "");
    if (pedido && buscados.some((f) => pedido.includes(f) || f.includes(pedido))) return true;
    // Lo que hay dentro: el nombre de las piezas es la señal más directa (una categoría puede
    // servir a dos del sitio: "Disc Brake" trae pastillas Y discos).
    const productos = (c.productos || []).map(normalizar);
    if (productos.some((p) => buscados.some((f) => p.includes(f)))) return true;
    // 2) y si no, el nombre o la ruta de la categoría (menos fiable: "Lubrication" esconde los
    //    filtros de aceite, por eso no basta con esto).
    const texto = normalizar(c.nombre);
    const ruta = normalizar(c.ruta || "");
    return buscados.some((f) => texto.includes(f) || ruta.includes(f));
  });
}

/**
 * Filtrar una LISTA de artículos por categoría del sitio (el nombre de la pieza manda, no la
 * categoría de AUTODOC, que es un grupo ambiguo). Se usa sobre los artículos de un trozo ya
 * cargado, y también desde `piezasDeCategoria` cuando los artículos vienen del catálogo entero.
 *
 * @returns {Array<{numero,marca,pieza,foto,especificaciones,originales}>}
 */
export function filtrarArticulos(articulos, slug) {
  const fragmentos = FRAGMENTOS_POR_SLUG[slug];
  if (!fragmentos || !fragmentos.length) return [];
  const buscados = fragmentos.map(normalizar);
  const salida = [];
  const vistos = new Set();

  for (const art of articulos || []) {
    const nombre = normalizar(art.pieza);
    if (!buscados.some((f) => nombre.includes(f))) continue;
    const clave = `${art.numero}|${art.marca}`.toUpperCase();
    if (vistos.has(clave)) continue;
    vistos.add(clave);
    salida.push({
      numero: art.numero,
      marca: art.marca,
      pieza: art.pieza,
      foto: art.foto || null,
      especificaciones: art.especificaciones || null,
      originales: Array.isArray(art.oem) ? art.oem : [],
    });
  }

  salida.sort((a, b) => a.marca.localeCompare(b.marca, "es") || a.numero.localeCompare(b.numero, "es"));
  return salida;
}

/**
 * Las piezas del catálogo que corresponden a una categoría del sitio, para ese vehículo.
 * Devuelve [] si no hay nada: nunca rellena.
 *
 * NOTA (T-B19): esta función trabaja sobre las piezas de UNA categoría ya cargada. Quien decide
 * qué archivos descargar es dataClient (con `categoriasParaSlug`), porque el catálogo está partido
 * por vehículo y categoría para no bajar 1,3 MB por visita.
 *
 * @returns {Array<{numero:string, marca:string, pieza:string, foto:string|null}>}
 */
export function piezasDeCategoria(catalogo, vehiculo, slug) {
  const fragmentos = FRAGMENTOS_POR_SLUG[slug];
  if (!fragmentos || !fragmentos.length) return [];

  const entrada = vehiculoEnCatalogo(catalogo, vehiculo);
  if (!entrada) return [];

  const todos = [];
  for (const cat of entrada.categorias || []) {
    for (const art of cat.articulos || []) todos.push(art);
  }
  return filtrarArticulos(todos, slug);
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
