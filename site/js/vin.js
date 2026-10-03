// site/js/vin.js
//
// Detección simple de "¿esto que tecleó el usuario es un VIN o un número de
// parte?". Regla pedida por la tarea: VIN = 17 caracteres alfanuméricos.
//
// Nota: un VIN real (ISO 3779) nunca usa las letras I, O ni Q (se confunden
// con 1 y 0), pero la tarea pide explícitamente la regla simple de "17
// alfanuméricos", así que se implementa así. Si el líder quiere la validación
// estricta real, es un cambio de una línea en ALPHANUMERIC_17 más abajo.

const ALPHANUMERIC_17 = /^[A-Z0-9]{17}$/;

/**
 * @param {string} raw texto tecleado por el usuario (se le quitan espacios)
 * @returns {boolean} true si "parece" un VIN (17 alfanuméricos)
 */
export function isLikelyVIN(raw) {
  const cleaned = String(raw || "").trim().toUpperCase().replace(/\s+/g, "");
  return ALPHANUMERIC_17.test(cleaned);
}

/**
 * @param {string} raw
 * @returns {string} el VIN limpio (mayúsculas, sin espacios) para comparar.
 */
export function cleanVIN(raw) {
  return String(raw || "").trim().toUpperCase().replace(/\s+/g, "");
}
