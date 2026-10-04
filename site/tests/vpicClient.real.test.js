// site/tests/vpicClient.real.test.js
//
// T-A3 — Tests contra la API REAL de vPIC (sin fetchImpl falso), a
// diferencia de vpicClient.test.js (que usa respuestas fijas para no
// depender de red en CI, ver su comentario de cabecera). Este archivo
// existe porque la tarea pide validar el filtro de marcas industriales
// (MARCAS_INDUSTRIALES_EXCLUIDAS) contra datos reales, no contra un fixture
// que ya asume el resultado esperado — igual que
// pipeline/tests/test_fetch_vehicles_makes.py en Python.
//
// Requiere red (vpic.nhtsa.dot.gov) y el `fetch` global de Node (nativo
// desde Node 18+, usado aquí sin opts.fetchImpl). Si no hay red, estos
// tests fallan con un error de conexión — es esperado, igual que en el
// lado Python (pipeline/tests/test_fetch_vehicles_makes.py).
//
// Se incluye en el glob estándar `tests/*.test.js` (ver site/tests/README.md
// para el conteo total), así que correr la suite completa también requiere
// red para estos 2 casos — mismo trade-off ya aceptado en pipeline/tests/.

import { test, describe } from "node:test";
import assert from "node:assert/strict";

import { getAllMakes } from "../js/vpicClient.js";

describe("vpicClient.js — getAllMakes contra vPIC real (T-A3)", () => {
  test("excluye fabricantes de camiones pesados conocidos", async () => {
    const makes = await getAllMakes();
    const names = new Set(makes.map((m) => m.name));
    // Freightliner aparece en car+MPV sin el filtro de T-A3 (confirmado
    // contra la API real); Peterbilt y Kenworth nunca aparecen en car+MPV
    // pero están en la lista de exclusión explícita como defensa en
    // profundidad.
    assert.ok(!names.has("Freightliner"), "Freightliner no debe aparecer");
    assert.ok(!names.has("Peterbilt"), "Peterbilt no debe aparecer");
    assert.ok(!names.has("Kenworth"), "Kenworth no debe aparecer");
  });

  test("incluye marcas de auto/SUV/pickup de consumo reales", async () => {
    const makes = await getAllMakes();
    const names = new Set(makes.map((m) => m.name));
    assert.ok(names.has("Mitsubishi"), "Mitsubishi debe aparecer");
    assert.ok(names.has("Toyota"), "Toyota debe aparecer");
    assert.ok(names.has("Ford"), "Ford debe aparecer");
  });
});
