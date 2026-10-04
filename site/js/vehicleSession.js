// site/js/vehicleSession.js
//
// "Mi vehículo" persistente (T-E4): una vez que el usuario resuelve su
// vehículo (por VIN o por el wizard marca→año→modelo, ver app.js), lo
// recordamos en localStorage para que no tenga que volver a escribir el
// VIN ni repetir el wizard mientras dure la sesión del navegador (misma
// pestaña/perfil — localStorage no expira solo; "Cambiar vehículo" lo
// borra a mano, ver clearVehicle()).
//
// Este módulo NO hace fetch ni toca data/build/*.json: solo guarda/lee el
// objeto vehículo (misma forma que un elemento de data/build/vehicles.json,
// ver CONTRACTS.md) que dataClient.js ya resolvió. No es parte de la
// "superficie" de 3 funciones de dataClient.js (searchPart/getPart/
// getVehicles): es almacenamiento de sesión del lado del navegador, una
// categoría de dato distinta al catálogo, por eso vive en su propio
// módulo chico (mismo criterio que vpicClient.js: un servicio/concepto
// distinto se aísla en su propio archivo en vez de mezclarse con
// dataClient.js).

const STORAGE_KEY = "vpf:selectedVehicle";

function _storageAvailable() {
  try {
    return typeof localStorage !== "undefined" && localStorage !== null;
  } catch (_err) {
    // Algunos navegadores lanzan al acceder a localStorage en ciertos
    // modos (ej. storage completamente deshabilitado por política). No es
    // fatal: el usuario simplemente repetirá el VIN/wizard la próxima vez.
    return false;
  }
}

/**
 * @param {object} vehicle objeto con la forma de data/build/vehicles.json
 *   (al menos make/model/year; normalmente trae también id/trim/engine).
 */
export function saveVehicle(vehicle) {
  if (!vehicle || typeof vehicle !== "object") return;
  if (!_storageAvailable()) return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(vehicle));
  } catch (err) {
    // Cuota llena, modo privado que bloquea escritura, etc. No rompe el
    // flujo actual (el vehículo ya se está mostrando en pantalla); solo
    // no persiste para la próxima carga.
    console.warn("vehicleSession: no se pudo guardar el vehículo", err);
  }
}

/**
 * @returns {object|null} el vehículo guardado, o null si no hay nada
 *   guardado o el valor guardado no es JSON de un objeto válido.
 */
export function loadVehicle() {
  if (!_storageAvailable()) return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
    return parsed;
  } catch (err) {
    console.warn("vehicleSession: no se pudo leer el vehículo guardado", err);
    return null;
  }
}

/** Borra el vehículo recordado (botón "Cambiar vehículo" en la barra). */
export function clearVehicle() {
  if (!_storageAvailable()) return;
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (err) {
    console.warn("vehicleSession: no se pudo borrar el vehículo guardado", err);
  }
}

/**
 * Texto corto para mostrar en la barra persistente, ej.
 * "Mitsubishi Outlander Sport 2020".
 * @param {object} vehicle
 * @returns {string}
 */
export function formatVehicleLabel(vehicle) {
  if (!vehicle) return "";
  return [vehicle.make, vehicle.model, vehicle.year].filter(Boolean).join(" ");
}
