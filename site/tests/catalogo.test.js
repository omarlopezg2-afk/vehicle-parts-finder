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
  normalizar, vehiculoEnCatalogo, vehiculosEnCatalogo, etiquetaDeVariante, traducirCombustible,
  piezasDeCategoria, slugsConNumeros, FRAGMENTOS_POR_SLUG,
  etiquetasDeVariantes, etiquetaDeVarianteCompleta, nombreDeMercado,
} from "../js/catalogoMap.js";
import {
  getNumerosDeCategoria, getSlugsConNumeros, getVariantesDeVehiculo, entradaDeVariante,
  matchVehicleByMakeModelYear, matchVehicleByVIN,
  _setFetchForTests,
} from "../js/dataClient.js";

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


// --------------------------------------------------------------------------------------
// T-B22: la variante. Un modelo-año puede tener dos, y el sitio tiene que saberlo.
// --------------------------------------------------------------------------------------

const INDICE_DOS_VARIANTES = {
  vehiculos: [
    { clave: "v1", etiqueta: "Toyota Corolla 2020 (1.8 gasolina)", vin: null,
      vehiculo: { make: "Toyota", model: "Corolla", year: "2020", variante: "1.8 (ZRE172)" }, categorias: [] },
    { clave: "v2", etiqueta: "Toyota Corolla 2020 (2.0 gasolina)", vin: null,
      vehiculo: { make: "Toyota", model: "Corolla", year: "2020", variante: "2.0 (MZEA12)" }, categorias: [] },
  ],
};

test("un modelo-año con dos variantes devuelve LAS DOS (no la primera)", () => {
  const vs = vehiculosEnCatalogo(INDICE_DOS_VARIANTES, { make: "Toyota", model: "Corolla", year: 2020 });
  assert.equal(vs.length, 2, "quedarse con la primera es mostrar piezas del motor equivocado");
  assert.deepEqual(vs.map((v) => v.clave), ["v1", "v2"]);
});

test("la etiqueta de variante sirve para que la persona se reconozca", () => {
  assert.equal(etiquetaDeVariante(INDICE_DOS_VARIANTES.vehiculos[0]), "1.8 (ZRE172)");
});

test("la etiqueta no queda vacía nunca: si no hay dato, lo dice", () => {
  assert.equal(etiquetaDeVariante({ vehiculo: {} }), "variante única");
  assert.equal(etiquetaDeVariante(null), "");
});

test("un vehículo que no está devuelve lista vacía, no una variante inventada", () => {
  assert.deepEqual(vehiculosEnCatalogo(INDICE_DOS_VARIANTES, { make: "Honda", model: "Civic", year: 2020 }), []);
  assert.deepEqual(vehiculosEnCatalogo(null, { make: "Toyota", model: "Corolla", year: 2020 }), []);
});


// --------------------------------------------------------------------------------------
// T-B24: el combustible en el idioma del cliente. "Petrol" es GASOLINA, y "gas" a secas no se usa.
// --------------------------------------------------------------------------------------

test("la tabla de combustibles dice lo acordado, sin anglicismos", () => {
  assert.equal(traducirCombustible("Petrol"), "Gasolina");
  assert.equal(traducirCombustible("Petrol/Liquified Petroleum Gas (LPG)"), "Gasolina / Gas (GLP)");
  assert.equal(traducirCombustible("Diesel"), "Diésel");
  assert.equal(traducirCombustible("Petrol/Ethanol"), "Gasolina / Etanol");
  assert.equal(traducirCombustible("Petrol/Electric"), "Híbrido");
});

test("nunca se dice 'gas' a secas: en RD eso es gasolina y GLP a la vez", () => {
  const conGas = traducirCombustible("Petrol/Liquified Petroleum Gas (LPG)");
  assert.ok(!/^gas$/i.test(conGas.trim()), "un label que diga solo 'gas' haría adivinar al cliente");
  assert.ok(conGas.includes("Gas (GLP)"), "cuando es gas, tiene que decir GLP");
});

test("un combustible nuevo se muestra tal cual, sin inventar traducción", () => {
  assert.equal(traducirCombustible("Petrol/CNG"), "Petrol/CNG");
  assert.equal(traducirCombustible(""), "");
  assert.equal(traducirCombustible(null), "");
});

test("la etiqueta de variante traduce el combustible, no lo deja en inglés", () => {
  const e = etiquetaDeVariante({ vehiculo: { cilindrada_l: 1.6, potencia_hp: 130, combustible: "Petrol" } });
  assert.equal(e, "1.6 L · 130 HP · Gasolina");
});


// --------------------------------------------------------------------------------------
// T-B25: la cuarta capa. Ningún número sin decir de qué mercado, de qué motor y de qué
// combustible es — y con más de un motor, el sitio PREGUNTA antes de enseñar nada.
// --------------------------------------------------------------------------------------

const COROLLA_2020 = { make: "Toyota", model: "Corolla", year: 2020 };

// Dos variantes con piezas DISTINTAS (como el 1.8 híbrido y el 1.8 de gasolina del catálogo real).
const INDICE_COROLLA = {
  pais_filtro: 67,
  vehiculos: [
    {
      clave: "v141200", etiqueta: "Toyota Corolla 2020 1.8 Hybrid (ZVG10)",
      vehiculo: { make: "Toyota", model: "Corolla", year: "2020", cilindrada_l: 1.8, potencia_ps: 98,
                  combustible: "Petrol/Electric", motor: "2ZR-FXE", variante: "1.8 Hybrid (ZVG10)" },
      categorias: [{ slug: "disc-brake", nombre: "Disc Brake", buscado: "brake pad",
                     ruta: "Braking System / Disc Brake", productos: ["Brake Pad Set, disc brake"],
                     articulos: 1, archivo: "catalogo/v141200/disc-brake.json" }],
    },
    {
      clave: "v141203", etiqueta: "Toyota Corolla 2020 1.8 (ZSG10)",
      vehiculo: { make: "Toyota", model: "Corolla", year: "2020", cilindrada_l: 1.8, potencia_ps: 140,
                  combustible: "Petrol", motor: "2ZR-FE", variante: "1.8 (ZSG10)" },
      categorias: [{ slug: "disc-brake", nombre: "Disc Brake", buscado: "brake pad",
                     ruta: "Braking System / Disc Brake", productos: ["Brake Pad Set, disc brake"],
                     articulos: 1, archivo: "catalogo/v141203/disc-brake.json" },
                   { slug: "lubrication", nombre: "Lubrication", buscado: "oil filter",
                     ruta: "Maintenance / Lubrication", articulos: 1,
                     archivo: "catalogo/v141203/lubrication.json" }],
    },
  ],
};

const PASTILLAS_HIBRIDO = { nombre: "Disc Brake", articulos: [
  { numero: "HIB-1", marca: "ADVICS", pieza: "Brake Pad Set, disc brake", foto: null }] };
const PASTILLAS_GASOLINA = { nombre: "Disc Brake", articulos: [
  { numero: "GAS-1", marca: "BOSCH", pieza: "Brake Pad Set, disc brake", foto: null }] };

test("T-B25 · sin elegir motor NO se enseña ningún número (ni se baja ningún trozo)", async () => {
  const pedidas = [];
  _setFetchForTests(fetchCon({ "catalogo/index.json": INDICE_COROLLA,
                               "v141203/disc-brake.json": PASTILLAS_GASOLINA,
                               "v141200/disc-brake.json": PASTILLAS_HIBRIDO }, pedidas));

  const sinElegir = await getNumerosDeCategoria(COROLLA_2020, "pastillas-freno");
  assert.deepEqual(sinElegir, [], "con dos motores, dar un número cualquiera es darlo del motor equivocado");
  assert.equal(pedidas.length, 1, "solo el índice: ni un trozo de un motor que no sabemos");
});

test("T-B25 · al elegir el motor se dan los números de ESE motor y solo de ese", async () => {
  const pedidas = [];
  _setFetchForTests(fetchCon({ "catalogo/index.json": INDICE_COROLLA,
                               "v141203/disc-brake.json": PASTILLAS_GASOLINA,
                               "v141200/disc-brake.json": PASTILLAS_HIBRIDO }, pedidas));

  const deGasolina = await getNumerosDeCategoria(COROLLA_2020, "pastillas-freno", "v141203");
  assert.deepEqual(deGasolina.map((p) => p.numero), ["GAS-1"]);
  assert.ok(!pedidas.some((u) => u.includes("v141200")), "no debe bajar el trozo del híbrido");

  const deHibrido = await getNumerosDeCategoria(COROLLA_2020, "pastillas-freno", "v141200");
  assert.deepEqual(deHibrido.map((p) => p.numero), ["HIB-1"]);
});

test("T-B25 · una clave que no existe no devuelve la primera variante", () => {
  assert.equal(entradaDeVariante(INDICE_COROLLA, COROLLA_2020, "v999"), null);
  assert.equal(entradaDeVariante(INDICE_COROLLA, COROLLA_2020, "v141200").clave, "v141200");
  assert.equal(entradaDeVariante(INDICE_COROLLA, COROLLA_2020), null, "sin clave y con dos, no elige");
  assert.equal(entradaDeVariante(INDICE, VEHICULO).clave, "v126680", "con una sola, no hay que preguntar");
});

test("T-B25 · el aviso de categorías con piezas une las variantes (no se esconde nada)", async () => {
  _setFetchForTests(fetchCon({ "catalogo/index.json": INDICE_COROLLA }));
  const slugs = await getSlugsConNumeros(COROLLA_2020);
  assert.ok(slugs.includes("filtro-aceite"), "el filtro solo lo tiene la variante de gasolina");
  assert.ok(slugs.includes("pastillas-freno"));
});

test("T-B25 · la etiqueta dice mercado, motor y combustible juntos", async () => {
  _setFetchForTests(fetchCon({ "catalogo/index.json": INDICE_COROLLA }));
  const variantes = await getVariantesDeVehiculo(COROLLA_2020);
  assert.equal(variantes.length, 2);
  assert.equal(variantes[1].clave, "v141203");
  assert.equal(variantes[1].mercado, "República Dominicana");
  assert.equal(
    variantes[1].detalle,
    "Mercado: República Dominicana · Motor: 1.8 L · 140 PS · Gasolina · 2ZR-FE · Combustible: Gasolina"
  );
  assert.equal(
    variantes[0].detalle,
    "Mercado: República Dominicana · Motor: 1.8 L · 98 PS · Híbrido · 2ZR-FXE · Combustible: Híbrido"
  );
  for (const v of variantes) {
    assert.ok(/Mercado: /.test(v.detalle) && /Motor: /.test(v.detalle) && /Combustible: /.test(v.detalle),
      "los tres datos son obligatorios: es la regla que no se rompe");
  }
});

test("T-B25 · si al catálogo le falta el combustible, se dice — no se calla", () => {
  const sinDato = { vehiculo: { make: "Toyota", model: "Corolla", year: "2020", variante: "1.8" } };
  const linea = etiquetaDeVarianteCompleta(sinDato, 67);
  assert.equal(linea, "Mercado: República Dominicana · Motor: 1.8 · Combustible: sin confirmar en el catálogo");
  assert.ok(!/gas\b(?!olina)/i.test(linea), "nunca 'gas' a secas");
});

test("T-B25 · el mercado se dice con su nombre; uno desconocido, con su número", () => {
  assert.equal(nombreDeMercado(67), "República Dominicana");
  assert.equal(nombreDeMercado(261), "Estados Unidos");
  assert.equal(nombreDeMercado(999), "Mercado 999", "mejor el número que un nombre inventado");
  assert.equal(nombreDeMercado(null), "");
  assert.equal(nombreDeMercado(undefined), "");
});

test("T-B25 · el mercado del catálogo es el 67: la etiqueta no dice EE.UU. si no lo es", () => {
  // El catálogo se armó con el filtro de país 67 (República Dominicana). Etiquetarlo como EE.UU.
  // sería mentir en cada número — pasó justo eso en la documentación hasta hoy (T-B25).
  assert.equal(INDICE_COROLLA.pais_filtro, 67);
  const e = INDICE_COROLLA.vehiculos[0];
  assert.ok(etiquetaDeVarianteCompleta(e, INDICE_COROLLA.pais_filtro).startsWith("Mercado: República Dominicana"));
});

test("T-B25 · dos variantes con la misma etiqueta se distinguen (si no, no se pueden elegir)", () => {
  const iguales = [
    { clave: "v1", vehiculo: { cilindrada_l: 1.8, combustible: "Petrol", variante: "1.8 (ZSG10)" } },
    { clave: "v2", vehiculo: { cilindrada_l: 1.8, combustible: "Petrol", variante: "1.8 (ZRE172)" } },
  ];
  const etiquetas = etiquetasDeVariantes(iguales);
  assert.notEqual(etiquetas[0].etiqueta, etiquetas[1].etiqueta);
  assert.ok(etiquetas[0].etiqueta.includes("ZSG10"));
  assert.ok(etiquetas[1].etiqueta.includes("ZRE172"));

  const distintas = [
    { clave: "v1", vehiculo: { cilindrada_l: 1.8, combustible: "Petrol" } },
    { clave: "v2", vehiculo: { cilindrada_l: 2.0, combustible: "Diesel" } },
  ];
  assert.deepEqual(etiquetasDeVariantes(distintas), [
    { clave: "v1", etiqueta: "1.8 L · Gasolina" },
    { clave: "v2", etiqueta: "2.0 L · Diésel" },
  ]);
  assert.deepEqual(etiquetasDeVariantes([]), []);
});

test("T-B25 · la potencia de TecDoc se dice en PS y la de la NHTSA en HP", () => {
  assert.equal(etiquetaDeVariante({ vehiculo: { potencia_ps: 140, combustible: "Petrol" } }), "140 PS · Gasolina");
  const conAmbas = { vehiculo: { potencia_ps: 140, potencia_hp: 138, combustible: "Petrol" } };
  assert.ok(etiquetaDeVariante(conAmbas).includes("140 PS"));
  assert.ok(etiquetaDeVariante(conAmbas).includes("138 HP"));
});

test("T-B25 · 'Gasoline' (la palabra del VIN) también es gasolina, no un anglicismo", () => {
  assert.equal(traducirCombustible("Gasoline"), "Gasolina");
  assert.equal(traducirCombustible("Gasoline"), traducirCombustible("Petrol"));
});

test("T-B25 · un vehículo que solo está en el catálogo de números AHORA se puede abrir", async () => {
  // Medido antes de este cambio: de los 250 vehículos con número, 249 decían "todavía no tenemos
  // piezas registradas". El catálogo estaba publicado y era inalcanzable desde la página.
  _setFetchForTests(fetchCon({ "vehicles.json": [], "catalogo/index.json": INDICE_COROLLA }));

  const v = await matchVehicleByMakeModelYear("Toyota", "Corolla", 2020);
  assert.ok(v, "el catálogo de números tiene que abrir la puerta");
  assert.equal(v.make, "Toyota");
  assert.equal(v.model, "Corolla");
  assert.equal(v.year, 2020);
  assert.equal(v.id, null, "no es un vehículo de ofertas: el id va a null, no inventado");
  assert.equal(v.variantes, 2);
  assert.equal(v.origen, "catalogo");

  assert.equal(await matchVehicleByMakeModelYear("Honda", "Civic", 2020), null, "lo que no está, no está");
});

test("T-B25 · un VIN del catálogo entra directo a sus números", async () => {
  const indiceConVin = {
    pais_filtro: 67,
    vehiculos: [{ clave: "v126680", vin: "JA4AP4AU3LU023739", etiqueta: "Mitsubishi Outlander Sport 2020",
                  vehiculo: { make: "MITSUBISHI", model: "Outlander Sport", year: "2020", combustible: "Gasoline" },
                  categorias: [] }],
  };
  _setFetchForTests(fetchCon({ "vehicles.json": [], "catalogo/index.json": indiceConVin }));

  const v = await matchVehicleByVIN("JA4AP4AU3LU023739");
  assert.ok(v);
  assert.equal(v.make, "MITSUBISHI");
  assert.equal(v.year, 2020);
  assert.equal(v.vin, "JA4AP4AU3LU023739");
  assert.equal(await matchVehicleByVIN("2T1BURHE6KC123456"), null);
});

test("T-B25 · el vehículo de ofertas sigue mandando cuando existe", async () => {
  const conOfertas = [{ id: "vin-JA4AP4AU3LU023739", make: "Mitsubishi", model: "Outlander Sport", year: 2020 }];
  _setFetchForTests(fetchCon({ "vehicles.json": conOfertas, "catalogo/index.json": INDICE_COROLLA }));

  const v = await matchVehicleByMakeModelYear("Mitsubishi", "Outlander Sport", 2020);
  assert.equal(v.id, "vin-JA4AP4AU3LU023739", "el de vehicles.json trae las ofertas de eBay");
  assert.equal(v.variantes, undefined);
});
