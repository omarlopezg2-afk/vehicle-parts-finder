// site/tests/vinOrigen.test.js
//
// El país de fabricación sale del VIN, sin red. Y lo que no está en la tabla NO se adivina.
import { test, describe } from "node:test";
import assert from "node:assert/strict";
import { origenDeVin, chasisJapones } from "../js/vinOrigen.js";

describe("origenDeVin", () => {
  test("VIN japonés (JA4… Mitsubishi)", () => {
    assert.deepEqual(origenDeVin("JA4AP3AW9LZ012345"), { pais: "Japón", codigo: "JA" });
  });
  test("VIN coreano (KMH… Hyundai, KNA… Kia)", () => {
    assert.equal(origenDeVin("KMHD35LH0GU123456").pais, "Corea del Sur");
    assert.equal(origenDeVin("KNAFK4A60F5123456").pais, "Corea del Sur");
  });
  test("VIN de EE.UU. (1, 4 y 5), Canadá (2) y México (3)", () => {
    assert.equal(origenDeVin("1HGCM82633A123456").pais, "Estados Unidos");
    assert.equal(origenDeVin("4T1BF1FK5GU123456").pais, "Estados Unidos");
    assert.equal(origenDeVin("5NPE24AF0FH123456").pais, "Estados Unidos");
    assert.equal(origenDeVin("2T1BURHE0GC123456").pais, "Canadá");
    assert.equal(origenDeVin("3N1AB7AP5GL123456").pais, "México");
  });
  test("Europa y China", () => {
    assert.equal(origenDeVin("WVWZZZ1KZAW123456").pais, "Alemania");
    assert.equal(origenDeVin("VF1RFB00X56123456").pais, "Francia");
    assert.equal(origenDeVin("LFV3A23C3E3123456").pais, "China");
  });
  test("acepta minúsculas y espacios", () => {
    assert.equal(origenDeVin(" ja4ap3aw9lz012345 ").pais, "Japón");
  });
  test("un país que no está en la tabla devuelve null: no se adivina", () => {
    assert.equal(origenDeVin("XTA21099051234567"), null); // Rusia: fuera de la tabla
    assert.equal(origenDeVin("JZ4AP3AW9LZ012345"), null); // J fuera del rango JA–JT
    assert.equal(origenDeVin("KA4AP3AW9LZ012345"), null); // KA–KE no es Corea
  });
  test("lo que no tiene forma de VIN devuelve null", () => {
    assert.equal(origenDeVin(""), null);
    assert.equal(origenDeVin("JA4AP3AW9LZ01234"), null); // 16
    assert.equal(origenDeVin("JA4AP3-AW9LZ01234"), null);
    assert.equal(origenDeVin("NZE141-1234567"), null);
    assert.equal(origenDeVin(undefined), null);
  });
});

describe("chasisJapones", () => {
  test("reconoce chasis de mercado interno japonés", () => {
    assert.deepEqual(chasisJapones("NZE141-1234567"), { codigoModelo: "NZE141", serie: "1234567" });
    assert.deepEqual(chasisJapones(" zre182-3012345 "), { codigoModelo: "ZRE182", serie: "3012345" });
    assert.equal(chasisJapones("GRX133-6000123").codigoModelo, "GRX133");
    assert.equal(chasisJapones("GX110-1234567").codigoModelo, "GX110");
  });
  test("un VIN no es un chasis japonés, ni un número de parte", () => {
    assert.equal(chasisJapones("JA4AP3AW9LZ012345"), null);
    assert.equal(chasisJapones("04465-02570"), null); // número de pastilla Toyota
    assert.equal(chasisJapones("1230A114"), null);
    assert.equal(chasisJapones(""), null);
  });
});
