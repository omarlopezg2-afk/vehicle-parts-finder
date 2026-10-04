// site/tests/vpicClient.test.js
//
// Tests de Node (node --test, sin dependencias) para site/js/vpicClient.js.
// Se inyecta un fetchImpl falso (no hay fetch de navegador en Node para
// URLs externas aquí) con respuestas fijas que imitan la forma real de
// vPIC, para no depender de la red en CI. No prueba contra vPIC real: la
// verificación de CORS/respuesta real se hizo a mano (ver PR, sección
// "cómo se eligió la Opción A").

import { test, describe } from "node:test";
import assert from "node:assert/strict";

import { getAllMakes, getModelsForMakeYear, getYearRange } from "../js/vpicClient.js";

function fakeFetchFor(responsesByUrlSubstring) {
  return async function fakeFetch(url) {
    const match = Object.keys(responsesByUrlSubstring).find((k) => url.includes(k));
    if (!match) {
      return { ok: false, status: 404, json: async () => ({}) };
    }
    const body = responsesByUrlSubstring[match];
    return { ok: true, status: 200, json: async () => body };
  };
}

describe("vpicClient.js", () => {
  test("getAllMakes deduplica marcas que aparecen en car y en mpv", async () => {
    const fetchImpl = fakeFetchFor({
      "GetMakesForVehicleType/car": {
        Results: [
          { MakeId: 481, MakeName: "MITSUBISHI" },
          { MakeId: 448, MakeName: "TOYOTA" },
        ],
      },
      "GetMakesForVehicleType/multipurpose": {
        Results: [
          { MakeId: 481, MakeName: "MITSUBISHI" }, // misma marca, otro tipo
          { MakeId: 500, MakeName: "JEEP" },
        ],
      },
    });

    const makes = await getAllMakes({ fetchImpl });
    const names = makes.map((m) => m.name);
    assert.deepEqual(names, ["Jeep", "Mitsubishi", "Toyota"]); // ordenado, sin duplicar Mitsubishi
    assert.equal(makes.find((m) => m.name === "Mitsubishi").id, 481);
  });

  test("getAllMakes devuelve [] (no lanza excepción) si ambas llamadas fallan", async () => {
    const fetchImpl = async () => {
      throw new Error("network down");
    };
    const makes = await getAllMakes({ fetchImpl });
    assert.deepEqual(makes, []);
  });

  test("getAllMakes excluye fabricantes industriales aunque vPIC los liste en car/mpv", async () => {
    // T-A3: simula el caso real confirmado contra vPIC (Freightliner
    // aparece en GetMakesForVehicleType/mpv junto a marcas de consumo).
    const fetchImpl = fakeFetchFor({
      "GetMakesForVehicleType/car": {
        Results: [
          { MakeId: 448, MakeName: "TOYOTA" },
          { MakeId: 1, MakeName: "BMW" },
        ],
      },
      "GetMakesForVehicleType/multipurpose": {
        Results: [
          { MakeId: 481, MakeName: "MITSUBISHI" },
          { MakeId: 582, MakeName: "FREIGHTLINER" }, // debe excluirse
          { MakeId: 999, MakeName: "PETERBILT" }, // defensa en profundidad
        ],
      },
    });

    const makes = await getAllMakes({ fetchImpl });
    const names = makes.map((m) => m.name);
    assert.deepEqual(names, ["Bmw", "Mitsubishi", "Toyota"]);
    assert.ok(!names.includes("Freightliner"));
    assert.ok(!names.includes("Peterbilt"));
  });

  test("getModelsForMakeYear devuelve modelos ordenados y deduplicados", async () => {
    const fetchImpl = fakeFetchFor({
      "GetModelsForMakeYear/make/Mitsubishi/modelyear/2020": {
        Results: [
          { Model_ID: 2, Model_Name: "Outlander Sport" },
          { Model_ID: 1, Model_Name: "Mirage" },
          { Model_ID: 2, Model_Name: "Outlander Sport" }, // duplicado
        ],
      },
    });

    const models = await getModelsForMakeYear("Mitsubishi", 2020, { fetchImpl });
    assert.deepEqual(models, [
      { id: 1, name: "Mirage" },
      { id: 2, name: "Outlander Sport" },
    ]);
  });

  test("getModelsForMakeYear devuelve [] con make vacío o año inválido", async () => {
    const fetchImpl = fakeFetchFor({});
    assert.deepEqual(await getModelsForMakeYear("", 2020, { fetchImpl }), []);
    assert.deepEqual(await getModelsForMakeYear("Mitsubishi", "no-es-año", { fetchImpl }), []);
  });

  test("getModelsForMakeYear devuelve [] (no lanza excepción) si la red falla", async () => {
    const fetchImpl = async () => {
      throw new Error("network down");
    };
    const models = await getModelsForMakeYear("Mitsubishi", 2020, { fetchImpl });
    assert.deepEqual(models, []);
  });

  test("getYearRange incluye el año actual y baja hasta 1990", () => {
    const years = getYearRange();
    const currentYear = new Date().getFullYear();
    assert.ok(years.includes(currentYear));
    assert.ok(years.includes(1990));
    assert.ok(!years.includes(1989));
    // Orden descendente (año más reciente primero, más útil en un <select>).
    assert.equal(years[0], currentYear + 1);
  });
});
