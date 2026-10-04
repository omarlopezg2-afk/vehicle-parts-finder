// site/tests/vehicleSession.test.js
//
// Tests de Node (node --test, sin dependencias) para
// site/js/vehicleSession.js (T-E4, "Mi vehículo" persistente).
//
// Node (sin --experimental-webstorage) no define `localStorage` global,
// así que se instala un polyfill mínimo en memoria ANTES de importar el
// módulo (vehicleSession.js solo usa getItem/setItem/removeItem, que es
// toda la superficie que necesita este fake).

import { test, describe, beforeEach } from "node:test";
import assert from "node:assert/strict";

function installFakeLocalStorage() {
  const store = new Map();
  globalThis.localStorage = {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => store.set(k, String(v)),
    removeItem: (k) => store.delete(k),
    clear: () => store.clear(),
  };
  return globalThis.localStorage;
}

installFakeLocalStorage();

const {
  saveVehicle,
  loadVehicle,
  clearVehicle,
  formatVehicleLabel,
} = await import("../js/vehicleSession.js");

describe("vehicleSession.js", () => {
  beforeEach(() => {
    globalThis.localStorage.clear();
  });

  test("loadVehicle regresa null si no hay nada guardado", () => {
    assert.equal(loadVehicle(), null);
  });

  test("saveVehicle + loadVehicle hace round-trip del objeto completo", () => {
    const vehicle = {
      id: "veh-mitsubishi-outlander-sport-2020",
      make: "Mitsubishi",
      model: "Outlander Sport",
      year: 2020,
      trim: "ES 2.0",
      engine: "2.0L 4B11",
    };
    saveVehicle(vehicle);
    assert.deepEqual(loadVehicle(), vehicle);
  });

  test("clearVehicle borra lo guardado", () => {
    saveVehicle({ make: "Toyota", model: "Corolla", year: 2015 });
    assert.ok(loadVehicle());
    clearVehicle();
    assert.equal(loadVehicle(), null);
  });

  test("saveVehicle ignora valores no-objeto sin lanzar", () => {
    saveVehicle(null);
    saveVehicle(undefined);
    saveVehicle("no-es-un-objeto");
    assert.equal(loadVehicle(), null);
  });

  test("loadVehicle regresa null si el valor guardado no es un objeto JSON válido", () => {
    globalThis.localStorage.setItem("vpf:selectedVehicle", "esto no es json {");
    assert.equal(loadVehicle(), null);
  });

  test("loadVehicle regresa null si el valor guardado es un array", () => {
    globalThis.localStorage.setItem("vpf:selectedVehicle", JSON.stringify([1, 2, 3]));
    assert.equal(loadVehicle(), null);
  });

  test("formatVehicleLabel arma 'Marca Modelo Año'", () => {
    assert.equal(
      formatVehicleLabel({ make: "Mitsubishi", model: "Outlander Sport", year: 2020 }),
      "Mitsubishi Outlander Sport 2020"
    );
  });

  test("formatVehicleLabel regresa cadena vacía sin vehículo", () => {
    assert.equal(formatVehicleLabel(null), "");
    assert.equal(formatVehicleLabel(undefined), "");
  });
});
