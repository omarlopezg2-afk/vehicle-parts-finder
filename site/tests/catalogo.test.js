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
            { numero: "D2N097", marca: "ADVICS", pieza: "Brake Pad Set, disc brake", foto: "https://x/5.webp",
              especificaciones: { "Fitting Position": "Rear Axle", "Thickness [mm]": "15,3" },
              oem: [{ numero: "MN102628", marca: "MITSUBISHI" }, { numero: "4253.90", marca: null }] },
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

test("las especificaciones y los números originales llegan al sitio", () => {
  // T-B16: sin esto, la ficha enseña una marca y un número; con esto, enseña "Trasera · 15,3 mm"
  // y el número original del fabricante, que es lo que distingue una pieza de otra.
  const pastillas = piezasDeCategoria(CATALOGO, VEHICULO, "pastillas-freno");
  const d2 = pastillas.find((p) => p.numero === "D2N097");
  assert.equal(d2.especificaciones["Fitting Position"], "Rear Axle");
  assert.equal(d2.originales[0].numero, "MN102628");

  // y una pieza sin detalle no inventa nada: van vacíos, no undefined
  const sn = pastillas.find((p) => p.numero === "SN678");
  assert.equal(sn.especificaciones, null);
  assert.deepEqual(sn.originales, []);
});

test("los discos no se llevan las pastillas (regresión del 07/10/2026)", () => {
  // "disc brake" aparece dentro de "Brake Pad Set, disc brake", así que con ese fragmento la
  // página de discos mostraba pastillas. Se cazó verificando en el navegador, no en las pruebas.
  const discos = piezasDeCategoria(CATALOGO, VEHICULO, "discos-freno");
  assert.ok(
    !discos.some((p) => /brake pad/i.test(p.pieza)),
    "una pastilla de freno no puede salir en la categoría de discos"
  );
  assert.ok(discos.every((p) => /brake disc/i.test(p.pieza)));
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
// dataClient: el único módulo que lee data/build (T-B19: catálogo partido)
// --------------------------------------------------------------------------------------

// El índice tal como lo escribe pipeline/partir_catalogo.py: pequeñito, sin piezas dentro.
const INDICE = {
  fuente: "AUTODOC Parts Catalog (TecDoc) vía RapidAPI",
  vehiculos: [{
    clave: "v126680",
    etiqueta: "Mitsubishi Outlander Sport 2020 (2.0 gasolina)",
    vin: "JA4AP4AU3LU023739",
    vehiculo: { make: "MITSUBISHI", model: "Outlander Sport", year: "2020" },
    autodoc: { manufacturerId: 77, modelId: 8631, vehicleId: 126680 },
    originales: { archivo: "catalogo/v126680/originales.json", productos: 3 },
    categorias: [
      { slug: "lubrication", nombre: "Lubrication", buscado: "oil filter",
        ruta: "Maintenance / Lubrication", articulos: 3, archivo: "catalogo/v126680/lubrication.json" },
      { slug: "disc-brake", nombre: "Disc Brake", buscado: "brake pad",
        ruta: "Braking System / Disc Brake", articulos: 2,
        productos: ["Brake Disc", "Brake Pad Set, disc brake"],
        archivo: "catalogo/v126680/disc-brake.json" },
    ],
  }],
};

const TROZO_LUBRICACION = { nombre: "Lubrication", articulos: [
  { numero: "MO-511", marca: "AMC Filter", pieza: "Oil Filter", foto: "https://x/1.webp",
    especificaciones: { "Outer Diameter [mm]": "71" }, oem: [{ numero: "1230A105", marca: "MITSUBISHI" }] },
  { numero: "18001100", marca: "AJUSA", pieza: "Seal Ring, oil drain plug", foto: null },
  { numero: "MO-511", marca: "AMC Filter", pieza: "Oil Filter", foto: "https://x/1.webp" },
]};

const TROZO_FRENOS = { nombre: "Disc Brake", articulos: [
  { numero: "D2N097", marca: "ADVICS", pieza: "Brake Pad Set, disc brake", foto: "https://x/5.webp",
    especificaciones: { "Fitting Position": "Rear Axle" }, oem: [{ numero: "MN102628", marca: "MITSUBISHI" }] },
  { numero: "BDS1486", marca: "BENDIX Braking", pieza: "Brake Disc", foto: null },
]};

function fetchCon(mapa, registro) {
  return async (url) => {
    const u = String(url);
    if (registro) registro.push(u);
    for (const [trozo, cuerpo] of Object.entries(mapa)) {
      if (u.includes(trozo)) return { ok: true, status: 200, json: async () => cuerpo };
    }
    return { ok: false, status: 404, json: async () => ({}) };
  };
}

test("getNumerosDeCategoria baja SOLO el trozo que necesita", async () => {
  const pedidas = [];
  _setFetchForTests(fetchCon({ "catalogo/index.json": INDICE, "v126680/lubrication.json": TROZO_LUBRICACION,
                              "v126680/disc-brake.json": TROZO_FRENOS }, pedidas));

  const piezas = await getNumerosDeCategoria(VEHICULO, "filtro-aceite");

  assert.deepEqual(piezas.map((p) => p.numero), ["MO-511"], "el sello del tapón no es un filtro");
  assert.equal(piezas[0].especificaciones["Outer Diameter [mm]"], "71");
  assert.equal(piezas[0].originales[0].numero, "1230A105");
  assert.equal(pedidas.length, 2, "índice + un trozo: ni uno más");
  assert.ok(!pedidas.some((u) => u.includes("disc-brake")), "no debe bajar la categoría de frenos");
});

test("getSlugsConNumeros se resuelve con el índice, sin bajar trozos", async () => {
  const pedidas = [];
  _setFetchForTests(fetchCon({ "catalogo/index.json": INDICE }, pedidas));

  const slugs = await getSlugsConNumeros(VEHICULO);

  assert.ok(slugs.includes("filtro-aceite"));
  assert.ok(slugs.includes("pastillas-freno"));
  assert.ok(slugs.includes("discos-freno"));
  assert.ok(!slugs.includes("bateria"));
  assert.equal(pedidas.length, 1, "solo el índice");
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

test("un trozo que no baja no tumba la página", async () => {
  _setFetchForTests(async (url) => {
    const u = String(url);
    if (u.includes("index.json")) return { ok: true, status: 200, json: async () => INDICE };
    throw new Error("sin red");
  });
  assert.deepEqual(await getNumerosDeCategoria(VEHICULO, "filtro-aceite"), []);
});
