// site/tests/catalogo.test.js
//
// T-B14: el catálogo con número de parte, en el sitio.
//
// El caso central de estas pruebas es el que reportó el usuario el 07/10/2026: buscó "Filtro de
// aceite" para su Outlander Sport y el sitio le dijo que no tenía nada — era cierto para las
// ofertas de eBay (que no tienen categoría de filtro de aceite), pero el catálogo de AUTODOC sí
// tenía 9 filtros para su motor. Estas pruebas fijan que ese hueco queda cerrado y, sobre todo,
// que cuando no hay dato NO se inventa nada.
import test from "node:test";
import assert from "node:assert/strict";

import {
  normalizar, vehiculoEnCatalogo, piezasDeCategoria, slugsConNumeros, FRAGMENTOS_POR_SLUG,
} from "../js/catalogoMap.js";
import { getNumerosDeCategoria, getSlugsConNumeros, _setFetchForTests } from "../js/dataClient.js";

const VEHICULO = { id: "vin-JA4AP4AU3LU023739", vin: "JA4AP4AU3LU023739", make: "Mitsubishi", model: "Outlander Sport", year: 2020 };

const CATALOGO = {
  generado_en: "2026-10-07T01:53:33Z",
  fuente: "AUTODOC Parts Catalog (TecDoc) vía RapidAPI",
  pais_filtro: 67,
  incompleto: false,
  consultas: 27,
  vehiculos: [
    {
      etiqueta: "Mitsubishi Outlander Sport 2020 (2.0 gasolina)",
      vin: "JA4AP4AU3LU023739",
      vehiculo: { make: "MITSUBISHI", model: "Outlander Sport", year: "2020" },
      autodoc: { manufacturerId: 77, modelId: 8631, vehicleId: 126680 },
      avisos: [],
      categorias: [
        {
          nombre: "Lubrication", ruta: "Maintenance / Lubrication", buscado: "oil filter", categoryId: 100031,
          articulos: [
            { numero: "MO-511", marca: "AMC Filter", pieza: "Oil Filter", foto: "https://x/1.webp" },
            { numero: "MO-511", marca: "KAVO PARTS", pieza: "Oil Filter", foto: "https://x/2.webp" },
            { numero: "0 986 452 041", marca: "BOSCH", pieza: "Oil Filter", foto: "https://x/3.webp" },
            { numero: "18001100", marca: "AJUSA", pieza: "Seal Ring, oil drain plug", foto: "https://x/4.webp" },
            { numero: "MO-511", marca: "AMC Filter", pieza: "Oil Filter", foto: "https://x/1.webp" },
          ],
        },
        {
          nombre: "Disc Brake", ruta: "Braking System / Disc Brake", buscado: "brake pad", categoryId: 100027,
          articulos: [
            { numero: "D2N097", marca: "ADVICS", pieza: "Brake Pad Set, disc brake", foto: "https://x/5.webp" },
            { numero: "SN678", marca: "ADVICS", pieza: "Brake Pad Set, disc brake", foto: null },
            { numero: "X1", marca: "OTRA", pieza: "Brake Caliper", foto: null },
          ],
        },
      ],
    },
    {
      etiqueta: "Toyota Corolla 2019",
      vin: "2T1BURHE6KC123456",
      vehiculo: { make: "TOYOTA", model: "Corolla", year: "2019" },
      categorias: [],
    },
  ],
};

test("normalizar quita acentos y deja minúsculas", () => {
  assert.equal(normalizar("Oil Filter"), "oil filter");
  assert.equal(normalizar("Bujía"), "bujia");
  assert.equal(normalizar("  Brake  Pad  "), "brake pad");
  assert.equal(normalizar(null), "");
});

test("encuentra el vehículo por VIN", () => {
  const v = vehiculoEnCatalogo(CATALOGO, VEHICULO);
  assert.ok(v);
  assert.equal(v.autodoc.vehicleId, 126680);
});

test("si el vehículo del sitio no trae VIN, cae a marca+modelo+año", () => {
  const v = vehiculoEnCatalogo(CATALOGO, { make: "Mitsubishi", model: "Outlander Sport", year: 2020 });
  assert.ok(v);
  assert.equal(v.vin, "JA4AP4AU3LU023739");
});

test("un vehículo que no está en el catálogo devuelve null (no se inventa)", () => {
  assert.equal(vehiculoEnCatalogo(CATALOGO, { vin: "AAAAAAAAAAAAAAAAA" }), null);
  assert.equal(vehiculoEnCatalogo(CATALOGO, { make: "Honda", model: "CR-V", year: 2018 }), null);
  assert.equal(vehiculoEnCatalogo(null, VEHICULO), null);
});

test("EL CASO DEL USUARIO: filtro de aceite tiene números aunque eBay no tuviera ofertas", () => {
  const piezas = piezasDeCategoria(CATALOGO, VEHICULO, "filtro-aceite");
  const numeros = piezas.map((p) => p.numero);
  // Ordenado por marca y luego número (así se lee mejor en pantalla): AMC Filter, BOSCH, KAVO PARTS
  assert.deepEqual(numeros, ["MO-511", "0 986 452 041", "MO-511"], "MO-511 de dos marcas distintas es legítimo");
  assert.ok(piezas.every((p) => p.pieza.toLowerCase().includes("oil filter")));
  assert.ok(!numeros.includes("18001100"), "la junta del tapón NO es un filtro de aceite");
});

test("no duplica la misma pieza repetida con la misma marca", () => {
  const piezas = piezasDeCategoria(CATALOGO, VEHICULO, "filtro-aceite");
  const amc = piezas.filter((p) => p.numero === "MO-511" && p.marca === "AMC Filter");
  assert.equal(amc.length, 1, "la misma pieza dos veces en el origen no debe salir dos veces");
});

test("cada categoría del sitio sólo trae lo suyo", () => {
  const pastillas = piezasDeCategoria(CATALOGO, VEHICULO, "pastillas-freno");
  assert.deepEqual(pastillas.map((p) => p.numero), ["D2N097", "SN678"]);
  assert.ok(!pastillas.some((p) => p.numero === "X1"), "un caliper no es una pastilla de freno");
  const caliper = piezasDeCategoria(CATALOGO, VEHICULO, "caliper");
  assert.deepEqual(caliper.map((p) => p.numero), ["X1"]);
});

test("una categoría sin fragmentos (batería) devuelve vacío, no cualquier cosa", () => {
  assert.equal(FRAGMENTOS_POR_SLUG["bateria"], undefined);
  assert.deepEqual(piezasDeCategoria(CATALOGO, VEHICULO, "bateria"), []);
  assert.deepEqual(piezasDeCategoria(CATALOGO, VEHICULO, "inventada"), []);
});

test("un vehículo sin catálogo devuelve vacío", () => {
  assert.deepEqual(piezasDeCategoria(CATALOGO, { vin: "AAAAAAAAAAAAAAAAA" }, "filtro-aceite"), []);
});

test("slugsConNumeros lista sólo las categorías con piezas reales", () => {
  const slugs = slugsConNumeros(CATALOGO, VEHICULO);
  assert.ok(slugs.includes("filtro-aceite"));
  assert.ok(slugs.includes("pastillas-freno"));
  assert.ok(slugs.includes("caliper"));
  assert.ok(!slugs.includes("bateria"));
});

// --------------------------------------------------------------------------------------
// dataClient: el único módulo que lee data/build
// --------------------------------------------------------------------------------------

test("getNumerosDeCategoria lee el catálogo servido y devuelve las piezas", async () => {
  _setFetchForTests(async (url) => {
    if (String(url).includes("catalogo.json")) {
      return { ok: true, status: 200, json: async () => CATALOGO };
    }
    return { ok: false, status: 404, json: async () => ({}) };
  });
  const piezas = await getNumerosDeCategoria(VEHICULO, "filtro-aceite");
  assert.equal(piezas.length, 3);
  assert.equal(piezas[0].numero, "MO-511");
});

test("si el catálogo no está, devuelve vacío y NO tira de ninguna fixture", async () => {
  let pidioFixture = false;
  _setFetchForTests(async (url) => {
    if (String(url).includes("fixture")) pidioFixture = true;
    return { ok: false, status: 404, json: async () => ({}) };
  });
  assert.deepEqual(await getNumerosDeCategoria(VEHICULO, "filtro-aceite"), []);
  assert.deepEqual(await getSlugsConNumeros(VEHICULO), []);
  assert.equal(pidioFixture, false, "un catálogo de mentira mostraría números inventados a un cliente real");
});

test("si el fetch revienta, devuelve vacío sin lanzar", async () => {
  _setFetchForTests(async () => {
    throw new Error("sin red");
  });
  assert.deepEqual(await getNumerosDeCategoria(VEHICULO, "pastillas-freno"), []);
});
