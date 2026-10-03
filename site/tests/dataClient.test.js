// site/tests/dataClient.test.js
//
// Tests de Node (node --test, sin dependencias) para site/js/dataClient.js.
// No usan un servidor HTTP real: se inyecta un "fetch" falso con
// _setFetchForTests que lee los archivos de fixtures directamente del
// disco con fs, simulando las dos rutas que dataClient.js intenta:
//   1) ./data/build/<archivo>.json  (archivo "real", puede no existir)
//   2) ./js/fixtures/<archivo>.fixture.json (fixture de desarrollo)
//
// Cómo correr: desde site/ -> `node --test tests/`
// (requiere Node 18+; en este repo se probó con Node 24).

import { test, describe, beforeEach } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  searchPart,
  getPart,
  getVehicles,
  getCategories,
  matchVehicleByVIN,
  getPartsByFitment,
  _setFetchForTests,
} from "../js/dataClient.js";

const siteDir = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

// Simula fetch(url) -> { ok, status, json() }. Resuelve rutas relativas
// ("./data/build/parts.json", "./js/fixtures/parts.fixture.json") contra
// site/. Para probar el caso "archivo real SÍ existe" se puede apuntar
// REAL_EXISTS a true en un test puntual.
function makeFakeFetch({ realExists = false } = {}) {
  return async function fakeFetch(url) {
    const relPath = url.replace(/^\.\//, "");
    const isRealPath = relPath.startsWith("data/build/");

    if (isRealPath && !realExists && !relPath.includes("categories")) {
      // Simula que T-D1 todavía no entregó parts.json / vehicles.json.
      return { ok: false, status: 404, json: async () => ({}) };
    }

    const fullPath = path.join(siteDir, relPath);
    try {
      const text = await readFile(fullPath, "utf-8");
      return { ok: true, status: 200, json: async () => JSON.parse(text) };
    } catch (err) {
      return { ok: false, status: 404, json: async () => ({}) };
    }
  };
}

describe("dataClient.js", () => {
  beforeEach(() => {
    _setFetchForTests(makeFakeFetch());
  });

  test("searchPart encuentra por part_number_norm exacto (con guiones/espacios)", async () => {
    const results = await searchPart("1230-A114"); // con guion, debe normalizar
    assert.equal(results.length, 1);
    assert.equal(results[0].id, "mitsubishi-filtro-aceite-1230a114");
  });

  test("searchPart encuentra por texto libre (nombre o marca)", async () => {
    const results = await searchPart("wix");
    assert.ok(results.length >= 1);
    assert.ok(results.some((p) => p.brand === "WIX"));
  });

  test("searchPart regresa vacío si no hay coincidencias", async () => {
    const results = await searchPart("no-existe-esto-123456");
    assert.deepEqual(results, []);
  });

  test("searchPart regresa vacío con query vacía", async () => {
    const results = await searchPart("   ");
    assert.deepEqual(results, []);
  });

  test("getPart regresa la parte correcta por id", async () => {
    const part = await getPart("mitsubishi-pastillas-freno-mz690219");
    assert.ok(part);
    assert.equal(part.name, "Pastillas de freno delanteras");
  });

  test("getPart regresa null si el id no existe", async () => {
    const part = await getPart("no-existe");
    assert.equal(part, null);
  });

  test("getVehicles regresa un arreglo no vacío con la forma esperada", async () => {
    const vehicles = await getVehicles();
    assert.ok(Array.isArray(vehicles));
    assert.ok(vehicles.length > 0);
    const v = vehicles[0];
    assert.ok("make" in v && "model" in v && "year" in v);
  });

  test("getCategories regresa las categorías de categories.json", async () => {
    const categories = await getCategories();
    assert.ok(Array.isArray(categories));
    assert.ok(categories.some((c) => c.slug === "filtro-aceite"));
  });

  test("matchVehicleByVIN encuentra el vehículo por VIN de fixture", async () => {
    const vehicle = await matchVehicleByVIN("JA4AP3AW9LZ012345");
    assert.ok(vehicle);
    assert.equal(vehicle.make, "Mitsubishi");
  });

  test("matchVehicleByVIN regresa null si el VIN no está en la fixture", async () => {
    const vehicle = await matchVehicleByVIN("AAAAAAAAAAAAAAAAA");
    assert.equal(vehicle, null);
  });

  test("getPartsByFitment filtra por vehículo y categoría", async () => {
    const parts = await getPartsByFitment(
      "veh-mitsubishi-outlander-sport-2020",
      "filtro-aceite"
    );
    assert.ok(parts.length >= 1);
    assert.ok(parts.every((p) => p.category === "filtro-aceite"));
  });

  test("getPartsByFitment sin categoría regresa todas las piezas de ese vehículo", async () => {
    const parts = await getPartsByFitment("veh-mitsubishi-outlander-sport-2020");
    const categoriesFound = new Set(parts.map((p) => p.category));
    assert.ok(categoriesFound.size >= 2); // filtro-aceite, pastillas-freno, bateria
  });
});
