// site/js/numerosOriginales.js
//
// T-B26 / 4.2: qué números ORIGINALES (los del fabricante del carro) enseña una ficha de pieza.
//
// Regla de producto (Omar, 07/10/2026): se muestran PRIMERO los números originales siempre que los
// tengamos; si no los hay, vale el número de reemplazo (aftermarket) mientras sea la pieza correcta.
//
// Qué es un "original" aquí: un número del bloque `oem` de ESE artículo (TecDoc) cuya marca es la del
// vehículo. Es el cruce del propio artículo —no la lista general del vehículo (`originales.json`, 100+
// números sin posición ni marca de pieza)—, así que cada original está atado a la pieza que se enseña.
//
// TecDoc también cruza números de OTRAS marcas que usaron la misma pieza (un disco de Toyota también
// figura como Subaru o Pontiac). Esos NO se llaman "original" del carro: se separan en `deOtras`.
// Nunca se inventa ni se completa nada: si el artículo no trae `oem`, devuelve vacío.

// Piezas "de rendimiento" (EBC, JAPOCAT…): TecDoc les cruza el número original del carro porque le
// MONTAN, pero no son la pieza original ni la de uso normal. No se presentan como "Original" ni suben
// al principio: se enseñan con su propio número y la equivalencia en una línea aparte.
const ALTO_RENDIMIENTO = /^(high performance|sports?)\b/i;

export function esAltoRendimiento(pieza) {
  return ALTO_RENDIMIENTO.test(limpia(pieza && pieza.pieza));
}

/** Cuántos originales de la marca del carro se enseñan como máximo en la ficha (el resto se cuenta). */
export const MAX_ORIGINALES_VISIBLES = 4;

function limpia(s) {
  return String(s == null ? "" : s).trim();
}

function mismaMarca(a, b) {
  return limpia(a).toUpperCase() === limpia(b).toUpperCase() && limpia(a) !== "";
}

/**
 * Separa los números `oem` de un artículo en los de la marca del vehículo y los de otras marcas.
 * Quita duplicados (sin distinguir mayúsculas, espacios ni guiones) y conserva el orden en que vienen.
 *
 * @param {{originales?:Array<{numero:string, marca:string|null}>}} pieza
 * @param {string} marcaVehiculo p. ej. "Toyota"
 * @returns {{propios:string[], deOtras:Array<{marca:string, numeros:string[]}>}}
 */
export function separarOriginales(pieza, marcaVehiculo) {
  const lista = pieza && Array.isArray(pieza.originales) ? pieza.originales : [];
  const propios = [];
  const vistosPropios = new Set();
  const porMarca = new Map();

  for (const o of lista) {
    const numero = limpia(o && o.numero);
    if (!numero) continue;
    // Toyota escribe el mismo número con y sin guion (04466-02170 / 0446602170): es uno solo.
    const clave = numero.toUpperCase().replace(/[^A-Z0-9]/g, "");
    if (mismaMarca(o.marca, marcaVehiculo)) {
      if (vistosPropios.has(clave)) continue;
      vistosPropios.add(clave);
      propios.push(numero);
    } else {
      const marca = limpia(o.marca);
      if (!marca) continue; // sin marca no se puede decir de quién es: no se enseña
      const grupo = porMarca.get(marca.toUpperCase()) || { marca, numeros: [], vistos: new Set() };
      if (grupo.vistos.has(clave)) continue;
      grupo.vistos.add(clave);
      grupo.numeros.push(numero);
      porMarca.set(marca.toUpperCase(), grupo);
    }
  }

  const deOtras = [...porMarca.values()].map(({ marca, numeros }) => ({ marca, numeros }));
  return { propios, deOtras };
}

/**
 * Lo que dice la ficha de una pieza sobre sus números, en el orden en que se enseña.
 *
 * - `principal`: lo que va arriba. Si hay originales de la marca del carro, son esos; si no, el número
 *   de reemplazo de la pieza.
 * - `reemplazo`: el número de reemplazo, solo cuando hay originales arriba (para no perderlo).
 * - `masOriginales`: cuántos originales de la marca quedaron fuera por el tope visible.
 * - `tambienOriginalDe`: el cruce con otras marcas, solo si NO hay original propio (si lo hay, ese cruce
 *   es ruido).
 *
 * - `sustituyeA`: solo en piezas de alto rendimiento: a qué original del carro equivalen (sin llamarlas
 *   "original").
 *
 * @returns {{tipo:"original"|"reemplazo", principal:{etiqueta:string, numeros:string[]},
 *   reemplazo:{marca:string, numero:string}|null, masOriginales:number,
 *   tambienOriginalDe:{marca:string, numeros:string[]}|null,
 *   sustituyeA:{marca:string, numeros:string[]}|null}}
 */
export function numerosDeLaFicha(pieza, marcaVehiculo, max = MAX_ORIGINALES_VISIBLES) {
  const { propios, deOtras } = separarOriginales(pieza, marcaVehiculo);
  const reemplazo = { marca: limpia(pieza && pieza.marca), numero: limpia(pieza && pieza.numero) };

  if (esAltoRendimiento(pieza)) {
    return {
      tipo: "reemplazo",
      principal: { etiqueta: reemplazo.marca, numeros: reemplazo.numero ? [reemplazo.numero] : [] },
      reemplazo: null,
      masOriginales: 0,
      tambienOriginalDe: null,
      sustituyeA: propios.length ? { marca: limpia(marcaVehiculo), numeros: propios.slice(0, 2) } : null,
    };
  }

  if (propios.length) {
    return {
      tipo: "original",
      principal: { etiqueta: `Original ${limpia(marcaVehiculo)}`.trim(), numeros: propios.slice(0, max) },
      reemplazo,
      masOriginales: Math.max(0, propios.length - max),
      tambienOriginalDe: null,
      sustituyeA: null,
    };
  }

  const otra = deOtras[0] || null;
  return {
    tipo: "reemplazo",
    principal: { etiqueta: reemplazo.marca, numeros: reemplazo.numero ? [reemplazo.numero] : [] },
    reemplazo: null,
    masOriginales: 0,
    tambienOriginalDe: otra ? { marca: otra.marca, numeros: otra.numeros.slice(0, 2) } : null,
    sustituyeA: null,
  };
}

/**
 * Orden de las fichas: primero las piezas normales con original de la marca del carro, luego las
 * normales sin original y al final las de alto rendimiento. Es estable: dentro de cada grupo se
 * respeta el orden que ya traían (marca y número).
 */
export function ordenarPiezasConOriginalPrimero(piezas, marcaVehiculo) {
  const con = [];
  const sin = [];
  const rendimiento = [];
  for (const p of piezas || []) {
    if (esAltoRendimiento(p)) rendimiento.push(p);
    else (separarOriginales(p, marcaVehiculo).propios.length ? con : sin).push(p);
  }
  return [...con, ...sin, ...rendimiento];
}
