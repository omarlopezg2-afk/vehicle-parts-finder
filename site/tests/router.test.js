// site/tests/router.test.js
//
// Tests del router por hash (T-E5). Son funciones puras, así que se prueban sin
// navegador: lo que se fija aquí es que la ida y vuelta URL <-> estado no se
// rompa, incluidos los casos feos (espacios, paréntesis, acentos, barras).

import { test, describe } from "node:test";
import assert from "node:assert/strict";
import { estadoDesdeHash, hashDesdeEstado } from "../js/router.js";

describe("router.js — lectura del hash", () => {
  test("hash vacío es la vista de inicio", () => {
    assert.deepEqual(estadoDesdeHash(""), { vista: "inicio" });
    assert.deepEqual(estadoDesdeHash("#"), { vista: "inicio" });
    assert.deepEqual(estadoDesdeHash("#/"), { vista: "inicio" });
  });

  test("lee una búsqueda por número de parte", () => {
    assert.deepEqual(estadoDesdeHash("#/numero/0446502070"), {
      vista: "numero",
      numero: "0446502070",
    });
  });

  test("lee una categoría del catálogo completo", () => {
    assert.deepEqual(estadoDesdeHash("#/categoria/frenos"), {
      vista: "categoria",
      categoria: "frenos",
    });
  });

  test("lee el árbol de un vehículo", () => {
    assert.deepEqual(estadoDesdeHash("#/vehiculo/Mitsubishi/Outlander Sport/2020"), {
      vista: "vehiculo",
      make: "Mitsubishi",
      model: "Outlander Sport",
      year: "2020",
    });
  });

  test("lee una categoría dentro de un vehículo", () => {
    assert.deepEqual(
      estadoDesdeHash("#/vehiculo/Mitsubishi/Outlander Sport/2020/pastillas-freno"),
      {
        vista: "vehiculo",
        make: "Mitsubishi",
        model: "Outlander Sport",
        year: "2020",
        categoria: "pastillas-freno",
      }
    );
  });

  test("lee un VIN", () => {
    assert.deepEqual(estadoDesdeHash("#/vin/JA4AP3AW9LZ012345"), {
      vista: "vin",
      vin: "JA4AP3AW9LZ012345",
    });
  });

  test("una ruta desconocida cae a inicio en vez de romper", () => {
    assert.deepEqual(estadoDesdeHash("#/lo-que-sea/1/2"), { vista: "inicio" });
    assert.deepEqual(estadoDesdeHash("#basura"), { vista: "inicio" });
  });

  test("una ruta incompleta cae a inicio (sin vehículo a medias)", () => {
    assert.deepEqual(estadoDesdeHash("#/vehiculo/Mitsubishi"), { vista: "inicio" });
    assert.deepEqual(estadoDesdeHash("#/numero"), { vista: "inicio" });
  });

  test("un porcentaje mal formado no lanza excepción", () => {
    assert.doesNotThrow(() => estadoDesdeHash("#/numero/100%"));
  });
});

describe("router.js — escritura del hash", () => {
  test("inicio se escribe como #/", () => {
    assert.equal(hashDesdeEstado({ vista: "inicio" }), "#/");
  });

  test("los espacios y paréntesis de una marca real van codificados", () => {
    // Caso real del catálogo: "Sprinter (Dodge Or Freightliner)".
    const hash = hashDesdeEstado({
      vista: "vehiculo",
      make: "Sprinter (Dodge Or Freightliner)",
      model: "3500",
      year: "2005",
    });
    assert.equal(
      hash,
      "#/vehiculo/Sprinter%20(Dodge%20Or%20Freightliner)/3500/2005"
    );
    assert.deepEqual(estadoDesdeHash(hash), {
      vista: "vehiculo",
      make: "Sprinter (Dodge Or Freightliner)",
      model: "3500",
      year: "2005",
    });
  });

  test("un estado incompleto no produce una URL a medias", () => {
    assert.equal(hashDesdeEstado({ vista: "vehiculo", make: "Toyota" }), "#/");
    assert.equal(hashDesdeEstado({ vista: "numero" }), "#/");
  });
});

describe("router.js — ida y vuelta (lo que garantiza que atrás funcione)", () => {
  const casos = [
    { vista: "inicio" },
    { vista: "numero", numero: "04152YZZA1" },
    { vista: "numero", numero: "MR297182" },
    { vista: "categoria", categoria: "clips-y-sujeciones" },
    { vista: "vehiculo", make: "Mitsubishi", model: "Outlander Sport", year: "2020" },
    {
      vista: "vehiculo",
      make: "Mitsubishi",
      model: "Outlander Sport",
      year: "2020",
      categoria: "pastillas-freno",
    },
    { vista: "vin", vin: "JA4AP3AW9LZ012345" },
    { vista: "vehiculo", make: "Sprinter (Dodge Or Freightliner)", model: "3500", year: "2005" },
  ];

  for (const estado of casos) {
    test(`estado -> hash -> estado se mantiene: ${JSON.stringify(estado)}`, () => {
      const hash = hashDesdeEstado(estado);
      assert.deepEqual(estadoDesdeHash(hash), estado);
      // Y escribirlo dos veces debe dar lo mismo (URLs estables, comparables).
      assert.equal(hashDesdeEstado(estadoDesdeHash(hash)), hash);
    });
  }
});
