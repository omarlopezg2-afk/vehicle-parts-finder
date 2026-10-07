// site/js/vinOrigen.js
//
// De qué PAÍS es el carro, leído del propio VIN (ISO 3779) — sin red y sin API.
//
// Los 3 primeros caracteres del VIN son el WMI (identificador del fabricante) y los dos primeros
// ya dicen el país donde se FABRICÓ. Eso es lo que sabemos con certeza; NO es el mercado al que se
// vendió el carro: un Toyota "JT…" fabricado en Japón puede haber salido con la guía a la izquierda
// para EE.UU. o RD. Por eso este módulo dice "fabricado en", nunca "mercado".
//
// Regla del proyecto (AGENTS.md, regla 2): si el país no está en la tabla, se devuelve `null`.
// Nunca se adivina. La tabla solo lleva los rangos asignados que se conocen con seguridad.
//
// Además detecta el CHASIS JAPONÉS DE MERCADO INTERNO (código de modelo + guion + serie, p. ej.
// "NZE141-1234567"). Un carro con ese número NO tiene VIN de 17 caracteres: es un JDM, nació con la
// guía a la derecha y en RD se le hace el cambio. Esa señal, y no la "J" del VIN, es la que activa
// el aviso de la dirección.

/** @typedef {{pais:string, codigo:string}} OrigenDeVin */

// Orden alfanumérico del segundo carácter del WMI: 0-9 y luego A-Z (sin I, O, Q).
const ORDEN = "0123456789ABCDEFGHJKLMNPRSTUVWXYZ";

// Cada fila: [primer carácter, segundo desde, segundo hasta, país]. Solo lo asignado sin ambigüedad.
const RANGOS = [
  // América del Norte
  ["1", "0", "Z", "Estados Unidos"],
  ["4", "0", "Z", "Estados Unidos"],
  ["5", "0", "Z", "Estados Unidos"],
  ["2", "A", "W", "Canadá"],
  ["3", "A", "W", "México"],
  // Asia
  ["J", "A", "T", "Japón"],
  ["K", "L", "R", "Corea del Sur"],
  ["L", "0", "Z", "China"],
  ["M", "A", "E", "India"],
  ["M", "L", "R", "Tailandia"],
  ["N", "L", "R", "Turquía"],
  // Europa
  ["S", "A", "M", "Reino Unido"],
  ["S", "U", "Z", "Polonia"],
  ["T", "J", "P", "República Checa"],
  ["V", "F", "R", "Francia"],
  ["V", "S", "W", "España"],
  ["W", "0", "Z", "Alemania"],
  ["Y", "S", "W", "Suecia"],
  ["Z", "A", "R", "Italia"],
  // América del Sur y Oceanía
  ["9", "3", "9", "Brasil"],
  ["9", "A", "E", "Brasil"],
  ["6", "A", "W", "Australia"],
];

function posicion(c) {
  return ORDEN.indexOf(c);
}

/**
 * País donde se fabricó el carro, según los dos primeros caracteres del VIN.
 *
 * @param {string} vin
 * @returns {OrigenDeVin|null} `null` si el VIN no tiene forma de VIN o el país no está en la tabla.
 */
export function origenDeVin(vin) {
  const v = String(vin || "").trim().toUpperCase().replace(/\s+/g, "");
  if (!/^[A-Z0-9]{17}$/.test(v)) return null;
  const a = v[0];
  const b = v[1];
  const pb = posicion(b);
  if (pb < 0) return null; // la I, la O y la Q no existen en un VIN
  for (const [primero, desde, hasta, pais] of RANGOS) {
    if (primero !== a) continue;
    if (pb >= posicion(desde) && pb <= posicion(hasta)) return { pais, codigo: `${a}${b}` };
  }
  return null;
}

// Chasis japonés de mercado interno: código de modelo (empieza por letra), guion y serie de 5 a 8
// dígitos. Ejemplos: NZE141-1234567, ZRE182-3012345, GRX133-6000123, GX110-1234567.
// Un VIN nunca lleva guion y tiene 17 caracteres.
const CHASIS_JDM = /^([A-Z]{1,4}\d{2,3}[A-Z]?)-(\d{5,8})$/;

/**
 * Si lo escrito es un chasis japonés de mercado interno, devuelve su código de modelo.
 *
 * @param {string} texto
 * @returns {{codigoModelo:string, serie:string}|null}
 */
export function chasisJapones(texto) {
  const t = String(texto || "").trim().toUpperCase().replace(/\s+/g, "");
  const m = CHASIS_JDM.exec(t);
  return m ? { codigoModelo: m[1], serie: m[2] } : null;
}
