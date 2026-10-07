// site/tests/vinFicha.test.js
import { test, describe } from "node:test";
import assert from "node:assert/strict";
import { litros, paisDeFabricacion, filasDeVin, lineaDeOrigen } from "../js/vinFicha.js";

describe("litros", () => {
  test("redondea a un decimal", () => {
    assert.equal(litros("2.998832712"), "3.0 L");
    assert.equal(litros(1.798), "1.8 L");
    assert.equal(litros("2"), "2.0 L");
  });
  test("lo que no es cilindrada no se enseña", () => {
    assert.equal(litros(""), "");
    assert.equal(litros(null), "");
    assert.equal(litros("abc"), "");
    assert.equal(litros(0), "");
  });
});

describe("filasDeVin", () => {
  const honda = {
    vin: "1HGCM82633A004352", make: "Honda", model: "Accord", year: "2003", trim: "EX-V6",
    bodyClass: "Coupe", displacementL: "2.998832712", engineCylinders: "6", engineHP: "240",
    transmission: "Automatic", fuelType: "Gasoline", plantCountry: "UNITED STATES (USA)",
  };
  test("el motor sale con un decimal y el combustible en español (nunca 'gas' a secas)", () => {
    const f = Object.fromEntries(filasDeVin(honda));
    assert.equal(f["Motor"], "3.0 L · 6 cil. · 240 HP");
    assert.equal(f["Combustible"], "Gasolina");
  });
  test("el país sale en español por el VIN, no en inglés de la NHTSA", () => {
    assert.equal(Object.fromEntries(filasDeVin(honda))["Fabricado en"], "Estados Unidos");
  });
  test("si el VIN no está en la tabla, se enseña lo que diga la NHTSA", () => {
    assert.equal(paisDeFabricacion({ vin: "XXXXXXXXXXXXXXXXX", plantCountry: "NARNIA" }), "NARNIA");
    assert.equal(paisDeFabricacion({ vin: "XXXXXXXXXXXXXXXXX" }), "");
  });
  test("las filas sin dato no salen", () => {
    const filas = filasDeVin({ vin: "XXXXXXXXXXXXXXXXX", make: "X" });
    assert.deepEqual(filas, [["Marca", "X"]]);
  });
});

describe("lineaDeOrigen", () => {
  test("dice el país y aclara que no es el mercado", () => {
    const t = lineaDeOrigen("KMHD35LH0GU123456");
    assert.match(t, /Corea del Sur/);
    assert.match(t, /no a qué mercado/);
  });
  test("VIN fuera de la tabla o inválido: nada (no se adivina)", () => {
    assert.equal(lineaDeOrigen("XXXXXXXXXXXXXXXXX"), "");
    assert.equal(lineaDeOrigen("123"), "");
  });
});
