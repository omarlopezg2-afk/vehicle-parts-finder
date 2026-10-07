// Pruebas del Worker de catálogo por demanda. El doble de `fetch` imita a AUTODOC con las
// respuestas REALES anotadas en docs/piloto-tb10-autodoc.md, incluidas las dos trampas que ya nos
// mordieron una vez (MITSUBISHI (BJC) ganándole a MITSUBISHI, y "outlander i" vs "outlander iii").
import test from "node:test";
import assert from "node:assert/strict";

const worker = (await import("../src/index.js")).default;

const HOST = "https://autodoc-parts-catalog.p.rapidapi.com";

function doble(registro = [], opciones = {}) {
  return async (url, init) => {
    const u = String(url);
    registro.push(u);
    // La clave NUNCA debe salir en una URL; si sale, esta prueba lo delata.
    if (u.includes("rapidapi-key") || u.includes("RAPIDAPI")) throw new Error("clave en la URL");
    if (opciones.falla) throw new Error("sin red");
    const r = (cuerpo, estado = 200) => ({ ok: estado < 400, status: estado, json: async () => cuerpo });

    if (u.includes("/api/manufacturers/list/")) return r({ manufacturers: [
      { manufacturerId: 10, manufacturerName: "MITSUBISHI" },
      { manufacturerId: 11, manufacturerName: "MITSUBISHI (BJC)" },
      { manufacturerId: 20, manufacturerName: "TOYOTA" },
    ]});
    if (u.includes("/api/models/list/")) return r({ models: [
      { modelId: 100, modelName: "OUTLANDER", modelYearFrom: "2003", modelYearTo: "2006" },
      { modelId: 101, modelName: "OUTLANDER II", modelYearFrom: "2006", modelYearTo: "2012" },
      { modelId: 102, modelName: "OUTLANDER III", modelYearFrom: "2012", modelYearTo: "" },
      { modelId: 103, modelName: "OUTLANDER SPORT", modelYearFrom: "2010", modelYearTo: "" },
    ]});
    if (u.includes("/list-vehicles-types/")) return r({ modelTypes: [
      { vehicleId: 126680, engId: 1, typeEngineName: "2.0", capacityLt: "2.0", powerPs: "148",
        engineCodes: "4B11", fuelType: "Petrol", constructionIntervalStart: "2012-01", constructionIntervalEnd: "" },
      { vehicleId: 126681, engId: 2, typeEngineName: "2.4", capacityLt: "2.4", powerPs: "168",
        engineCodes: "4B12", fuelType: "Petrol", constructionIntervalStart: "2012-01", constructionIntervalEnd: "" },
    ]});
    if (u.includes("/api/vin/decoder-v5/")) return r({ "vin-data-2": { content: JSON.stringify({
      make: "MITSUBISHI", model: "Outlander Sport", model_year: "2020",
      "displacement_(l)": "2.0", "engine_brake_(hp)_from": "148", "fuel_type_-_primary": "Petrol" }) } });
    if (u.includes("/api/articles/list/")) return r({ articles: [
      { articleId: 501, articleNo: "D2N097", supplierName: "ADVICS", articleProductName: "Brake Pad Set, disc brake",
        s3image: "https://fsn1.your-objectstorage.com/tecdoc2025/x.webp" },
      { articleId: 502, articleNo: "SN678", supplierName: "ADVICS", articleProductName: "Brake Pad Set, disc brake" },
    ]});
    if (u.includes("/api/articles/details/")) return r({
      articleAllSpecifications: [{ criteriaName: "Fitting Position", criteriaValue: "Rear Axle" }],
      articleOemNo: [{ oemDisplayNo: "MN102628", oemBrand: "MITSUBISHI" }],
    });
    return r({}, 404);
  };
}

function envFalso(inicial = {}, cuota = "0") {
  const kv = new Map(Object.entries(inicial));
  return {
    TOPE_MES: "18000",
    RAPIDAPI_KEY: "CLAVE_DE_PRUEBA_QUE_NO_DEBE_SALIR",
    CATALOGO: { get: async (k) => (kv.has(k) ? JSON.parse(kv.get(k)) : null),
                put: async (k, v) => { kv.set(k, v); } },
    CUOTA: { get: async () => cuota, put: async (k, v) => { kv.set(k, v); } },
    _kv: kv,
  };
}

const llamar = (qs, env) => worker.fetch(new Request(`https://w.dev/vehiculo?${qs}`), env);

test("un VIN resuelve el vehículo exacto y sus piezas con especificaciones", async () => {
  const registro = [];
  globalThis.fetch = doble(registro);
  const env = envFalso();
  const res = await llamar("vin=JA4AP4AU3LU023739&categorias=100027", env);
  const cuerpo = await res.json();

  assert.equal(res.status, 200);
  assert.equal(cuerpo.vehiculo.variante, "2.0", "debe elegir la variante de 2.0, no la de 2.4");
  assert.equal(cuerpo.vehiculo.motor, "4B11");
  assert.equal(cuerpo.piezas[0].articulos[0].numero, "D2N097");
  assert.equal(cuerpo.piezas[0].articulos[0].especificaciones["Fitting Position"], "Rear Axle");
  assert.equal(cuerpo.piezas[0].articulos[0].originales[0].numero, "MN102628");
});

test("MITSUBISHI le gana a MITSUBISHI (BJC): la marca, no la empresa conjunta", async () => {
  const env = envFalso();
  globalThis.fetch = doble([]);
  const cuerpo = await (await llamar("make=Mitsubishi&model=Outlander Sport&year=2020", env)).json();
  assert.equal(cuerpo.make, "MITSUBISHI");
});

test("un modelo con generaciones elige la de su época, no la primera", async () => {
  const env = envFalso();
  globalThis.fetch = doble([]);
  // 2020: "OUTLANDER III" (2012-) y no "OUTLANDER" (2003-2006), que es la que empataba antes.
  const cuerpo = await (await llamar("make=Mitsubishi&model=Outlander&year=2020", env)).json();
  assert.equal(cuerpo.model, "OUTLANDER III");
});

test("sin saber el motor NO se elige: se devuelve la lista y se pide que el visitante elija", async () => {
  const registro = [];
  globalThis.fetch = doble(registro);
  const cuerpo = await (await llamar("make=Mitsubishi&model=Outlander&year=2020&categorias=100027", envFalso())).json();
  assert.equal(cuerpo.vehiculo, null, "dos motores y ningún dato: no se elige la primera");
  assert.equal(cuerpo.requiereMotor, true);
  assert.deepEqual(cuerpo.variantes.map((v) => v.vehicleId), [126680, 126681]);
  assert.deepEqual(cuerpo.piezas, [], "sin motor no se pide ni se da ninguna pieza");
  assert.ok(!registro.some((u) => u.includes("/api/articles/")), "ni una consulta de piezas");
});

test("con el vehicleId que el visitante eligió se resuelve esa variante y sus piezas", async () => {
  globalThis.fetch = doble([]);
  const cuerpo = await (await llamar(
    "make=Mitsubishi&model=Outlander&year=2020&vehicleId=126681&categorias=100027", envFalso())).json();
  assert.equal(cuerpo.vehiculo.vehicleId, 126681);
  assert.equal(cuerpo.vehiculo.motor, "4B12");
  assert.equal(cuerpo.requiereMotor, false);
  assert.equal(cuerpo.piezas[0].articulos[0].numero, "D2N097");
});

test("un vehicleId que no es de ese modelo se rechaza, no se usa", async () => {
  globalThis.fetch = doble([]);
  const res = await llamar("make=Mitsubishi&model=Outlander&year=2020&vehicleId=999999", envFalso());
  assert.equal(res.status, 404);
  assert.match((await res.json()).error, /no es de/);
});

test("si el modelo no existe en el filtro pedido se prueba el otro y se dice cuál se usó", async () => {
  // Antes esto lanzaba ReferenceError (paisAlterno sin definir) y respondía 429.
  const registro = [];
  const base = doble(registro);
  globalThis.fetch = async (url, init) => {
    const u = String(url);
    if (u.includes("/api/models/list/") && u.includes("country-filter-id/127")) {
      return { ok: true, status: 200, json: async () => ({ models: [] }) };
    }
    return base(url, init);
  };
  const res = await llamar("make=Mitsubishi&model=Outlander&year=2020&pais=127", envFalso());
  const cuerpo = await res.json();
  assert.equal(res.status, 200);
  assert.equal(cuerpo.filtroPais, 261);
});

test("un VIN que da cilindrada y potencia elige su motor sin preguntar", async () => {
  globalThis.fetch = doble([]);
  const cuerpo = await (await llamar("vin=JA4AP4AU3LU023739", envFalso())).json();
  assert.equal(cuerpo.requiereMotor, false);
  assert.equal(cuerpo.vehiculo.vehicleId, 126680);
});

test("con la cuota agotada NO se consulta nada y se dice claro", async () => {
  const registro = [];
  globalThis.fetch = doble(registro);
  const env = envFalso({}, "18000");
  const res = await llamar("make=Mitsubishi&model=Outlander Sport&year=2020", env);
  const cuerpo = await res.json();

  assert.equal(res.status, 503);
  assert.equal(cuerpo.error, "cuota de este mes agotada");
  assert.equal(registro.length, 0, "no se puede gastar una sola consulta con la cuota agotada");
});

test("lo ya catalogado se sirve de caché, con cero consultas", async () => {
  const registro = [];
  globalThis.fetch = doble(registro);
  const env = envFalso({
    "cat:67:JA4AP4AU3LU023739": JSON.stringify({
      vehiculo: { make: "MITSUBISHI", variante: "2.0" },
      piezas: [{ categoryId: 100027, articulos: [{ numero: "D2N097" }] }],
    }),
  });
  const res = await llamar("vin=JA4AP4AU3LU023739&categorias=100027", env);
  const cuerpo = await res.json();

  assert.equal(cuerpo.fuente, "cache");
  assert.equal(cuerpo.piezas[0].articulos[0].numero, "D2N097");
  assert.equal(registro.length, 0, "la caché es gratis: cero consultas");
});

test("el mercado por defecto es el del catálogo: República Dominicana (67)", async () => {
  // T-B25: el catálogo se armó con el filtro 67 (semilla "pais": 67, monolito "pais_filtro": 67).
  // Con el defecto en EE.UU. (261), el Worker buscaba en un mercado donde los vehículo-tipos y hasta
  // los nombres comerciales son otros: decía "no encontramos el modelo" de coches que sí tenemos.
  const registro = [];
  globalThis.fetch = doble(registro);
  await llamar("make=Toyota&model=Corolla&year=2019", envFalso());
  assert.ok(registro.some((u) => u.includes("country-filter-id/67")),
    `el defecto tiene que ser 67; se pidió: ${registro.join(" | ")}`);
  // Si el modelo no está en el 67 se prueba el otro filtro (la salida de emergencia de construir()),
  // pero lo PRIMERO que se pide es siempre el 67.
  const primera = registro.find((u) => u.includes("/api/models/list/"));
  assert.ok(primera && primera.includes("country-filter-id/67"),
    `el primer filtro pedido debe ser 67; fue: ${primera}`);
});

test("si el sitio dice el mercado (?pais=), se respeta", async () => {
  const registro = [];
  globalThis.fetch = doble(registro);
  await llamar("make=Toyota&model=Corolla&year=2019&pais=261", envFalso());
  assert.ok(registro.some((u) => u.includes("country-filter-id/261")));
});

test("la clave de AUTODOC no aparece nunca en la respuesta", async () => {
  globalThis.fetch = doble([]);
  const env = envFalso();
  const texto = await (await llamar("make=Toyota&model=Corolla&year=2019", env)).text();
  assert.ok(!texto.includes("CLAVE_DE_PRUEBA_QUE_NO_DEBE_SALIR"));
});

test("sin VIN y sin marca+modelo+año se responde 400, sin gastar", async () => {
  const registro = [];
  globalThis.fetch = doble(registro);
  const res = await llamar("make=Toyota", envFalso());
  assert.equal(res.status, 400);
  assert.equal(registro.length, 0);
});

test("/salud responde sin tocar nada", async () => {
  globalThis.fetch = doble([]);
  const res = await worker.fetch(new Request("https://w.dev/salud"), envFalso());
  assert.equal((await res.json()).ok, true);
});
