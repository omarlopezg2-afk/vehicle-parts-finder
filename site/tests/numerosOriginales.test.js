// site/tests/numerosOriginales.test.js
//
// Originales primero cuando los hay; si no, el número de reemplazo. Nunca se inventa ninguno.
import { test, describe } from "node:test";
import assert from "node:assert/strict";
import {
  separarOriginales,
  numerosDeLaFicha,
  ordenarPiezasConOriginalPrimero,
  MAX_ORIGINALES_VISIBLES,
} from "../js/numerosOriginales.js";

const DISCO = {
  numero: "25513 V",
  marca: "AP",
  pieza: "Brake Disc",
  originales: [
    { numero: "19184293", marca: "PONTIAC" },
    { numero: "4351202240", marca: "TOYOTA" },
    { numero: "4351202270", marca: "toyota" },
    { numero: "4351202240", marca: "TOYOTA" }, // repetido
    { numero: "SU003-02101", marca: "SUBARU" },
    { numero: "435120D110", marca: "TOYOTA (FAW)" }, // otra empresa: no es "Toyota" a secas
    { numero: "SIN-MARCA", marca: null },
  ],
};
const PASTILLA = { numero: "13.0465-5690.2", marca: "ATE-APAC", pieza: "Brake Pad Set, disc brake", originales: [] };

describe("separarOriginales", () => {
  test("separa los de la marca del carro y quita repetidos (sin distinguir mayúsculas)", () => {
    const { propios } = separarOriginales(DISCO, "Toyota");
    assert.deepEqual(propios, ["4351202240", "4351202270"]);
  });
  test("el mismo número con y sin guion cuenta una sola vez", () => {
    const pieza = { originales: [
      { numero: "0446602170", marca: "TOYOTA" },
      { numero: "04466-02170", marca: "TOYOTA" },
      { numero: "04466 02170", marca: "Toyota" },
    ] };
    assert.deepEqual(separarOriginales(pieza, "Toyota").propios, ["0446602170"]);
  });
  test("agrupa los de otras marcas y descarta los que no dicen de quién son", () => {
    const { deOtras } = separarOriginales(DISCO, "Toyota");
    const marcas = deOtras.map((g) => g.marca);
    assert.deepEqual(marcas, ["PONTIAC", "SUBARU", "TOYOTA (FAW)"]);
    assert.ok(!JSON.stringify(deOtras).includes("SIN-MARCA"));
  });
  test("sin originales o sin pieza devuelve vacío (no inventa)", () => {
    assert.deepEqual(separarOriginales(PASTILLA, "Toyota"), { propios: [], deOtras: [] });
    assert.deepEqual(separarOriginales(null, "Toyota"), { propios: [], deOtras: [] });
    assert.deepEqual(separarOriginales({ originales: "x" }, "Toyota"), { propios: [], deOtras: [] });
  });
  test("si no sabemos la marca del carro, nada se llama original", () => {
    assert.deepEqual(separarOriginales(DISCO, "").propios, []);
    assert.deepEqual(separarOriginales(DISCO, undefined).propios, []);
  });
});

describe("numerosDeLaFicha", () => {
  test("con original de la marca: el original va arriba y el de reemplazo se conserva debajo", () => {
    const f = numerosDeLaFicha(DISCO, "Toyota");
    assert.equal(f.tipo, "original");
    assert.equal(f.principal.etiqueta, "Original Toyota");
    assert.deepEqual(f.principal.numeros, ["4351202240", "4351202270"]);
    assert.deepEqual(f.reemplazo, { marca: "AP", numero: "25513 V" });
    assert.equal(f.tambienOriginalDe, null);
    assert.equal(f.masOriginales, 0);
  });
  test("sin original de la marca: arriba va el número de reemplazo", () => {
    const f = numerosDeLaFicha(PASTILLA, "Toyota");
    assert.equal(f.tipo, "reemplazo");
    assert.deepEqual(f.principal, { etiqueta: "ATE-APAC", numeros: ["13.0465-5690.2"] });
    assert.equal(f.reemplazo, null);
    assert.equal(f.tambienOriginalDe, null);
  });
  test("solo cruces de otras marcas: se dicen como 'también original de', no como original del carro", () => {
    const pieza = { ...PASTILLA, originales: [{ numero: "MN102628", marca: "MITSUBISHI" }] };
    const f = numerosDeLaFicha(pieza, "Toyota");
    assert.equal(f.tipo, "reemplazo");
    assert.deepEqual(f.tambienOriginalDe, { marca: "MITSUBISHI", numeros: ["MN102628"] });
  });
  test("tope visible: cuenta los que quedan fuera en vez de volcar cientos de números", () => {
    const muchos = {
      numero: "X1",
      marca: "AP",
      originales: Array.from({ length: 12 }, (_, i) => ({ numero: `T${i}`, marca: "TOYOTA" })),
    };
    const f = numerosDeLaFicha(muchos, "Toyota");
    assert.equal(f.principal.numeros.length, MAX_ORIGINALES_VISIBLES);
    assert.equal(f.masOriginales, 12 - MAX_ORIGINALES_VISIBLES);
  });
});

describe("ordenarPiezasConOriginalPrimero", () => {
  test("las que tienen original de la marca van primero, respetando el orden previo", () => {
    const a = { numero: "A", marca: "AAA", originales: [] };
    const b = { numero: "B", marca: "BBB", originales: [{ numero: "1", marca: "TOYOTA" }] };
    const c = { numero: "C", marca: "CCC", originales: [{ numero: "2", marca: "SUBARU" }] };
    const d = { numero: "D", marca: "DDD", originales: [{ numero: "3", marca: "TOYOTA" }] };
    const r = ordenarPiezasConOriginalPrimero([a, b, c, d], "Toyota");
    assert.deepEqual(r.map((p) => p.numero), ["B", "D", "A", "C"]);
  });
  test("no pierde ni duplica piezas", () => {
    const r = ordenarPiezasConOriginalPrimero([PASTILLA, DISCO], "Toyota");
    assert.equal(r.length, 2);
  });
});
