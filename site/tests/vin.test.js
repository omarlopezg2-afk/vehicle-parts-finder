// site/tests/vin.test.js
//
// Tests de la detección simple "¿esto es un VIN o un número de parte?".

import { test, describe } from "node:test";
import assert from "node:assert/strict";
import { isLikelyVIN, cleanVIN } from "../js/vin.js";

describe("vin.js", () => {
  test("detecta un VIN válido de 17 alfanuméricos", () => {
    assert.equal(isLikelyVIN("JA4AP3AW9LZ012345"), true);
  });

  test("ignora espacios al evaluar", () => {
    assert.equal(isLikelyVIN(" JA4AP3AW9LZ012345 "), true);
  });

  test("rechaza algo más corto que 17 caracteres (número de parte típico)", () => {
    assert.equal(isLikelyVIN("1230A114"), false);
  });

  test("rechaza algo más largo que 17 caracteres", () => {
    assert.equal(isLikelyVIN("JA4AP3AW9LZ0123456"), false);
  });

  test("rechaza caracteres no alfanuméricos aunque tenga 17 de longitud total", () => {
    assert.equal(isLikelyVIN("JA4AP3-AW9LZ01234"), false);
  });

  test("cleanVIN pasa a mayúsculas y quita espacios", () => {
    assert.equal(cleanVIN(" ja4ap3aw9lz012345 "), "JA4AP3AW9LZ012345");
  });
});
