// site/tests/workerClient.test.js
//
// T-B21: el cliente del Worker (api.partexact.com). Sin red: se inyecta un fetch falso.
import { test, describe, beforeEach } from "node:test";
import assert from "node:assert/strict";
import {
  consultarWorker, workerActivo, _setFetchForTests, _setWorkerParaTests,
} from "../js/dataClient.js";

const URL_WORKER = "https://worker.prueba/vehiculo";

function respuesta(cuerpo, status = 200) {
  return { ok: status < 400, status, json: async () => cuerpo };
}

const DOS_MOTORES = {
  fuente: "autodoc", make: "MITSUBISHI", model: "OUTLANDER III", year: "2020", filtroPais: 67,
  vehiculo: null, requiereMotor: true, consultas: 3, piezas: [],
  variantes: [
    { vehicleId: 126680, variante: "2.0", motor: "4B11", cilindradaLt: "2.0000", potenciaPs: "148.0000", combustible: "Petrol" },
    { vehicleId: 126681, variante: "2.4", motor: "4B12", cilindradaLt: "2.4000", potenciaPs: "168.0000", combustible: "Petrol" },
  ],
};

describe("consultarWorker", () => {
  let llamadas;
  beforeEach(() => {
    llamadas = [];
    _setWorkerParaTests({ url: URL_WORKER, activo: true });
    _setFetchForTests(async (url) => {
      llamadas.push(String(url));
      return respuesta(DOS_MOTORES);
    });
  });

  test("viene APAGADO por defecto en producción (no gasta cupo hasta que haya piezas por demanda)", async () => {
    // Se comprueba contra el valor real del módulo, recargándolo limpio.
    const limpio = await import(`../js/dataClient.js?otra=${Date.now()}`);
    assert.equal(limpio.workerActivo(), false);
  });

  test("apagado: devuelve null y no toca la red", async () => {
    _setWorkerParaTests({ activo: false });
    assert.equal(workerActivo(), false);
    assert.equal(await consultarWorker({ make: "Mitsubishi", model: "Outlander", year: 2020 }), null);
    assert.equal(llamadas.length, 0);
  });

  test("marca+modelo+año: pide al Worker y devuelve la lista con etiquetas de motor/combustible", async () => {
    const r = await consultarWorker({ make: "Mitsubishi", model: "Outlander", year: 2020 });
    assert.equal(llamadas.length, 1);
    assert.ok(llamadas[0].startsWith(`${URL_WORKER}?`));
    assert.ok(llamadas[0].includes("make=Mitsubishi") && llamadas[0].includes("year=2020"));
    assert.equal(r.ok, true);
    assert.equal(r.requiereMotor, true, "con dos motores y sin dato, hay que preguntar");
    assert.equal(r.vehiculo, null);
    assert.deepEqual(r.variantes.map((v) => v.vehicleId), [126680, 126681]);
    assert.equal(r.variantes[0].etiqueta, "2.0 L · 148 PS · Gasolina · 4B11");
    assert.equal(r.variantes[1].etiqueta, "2.4 L · 168 PS · Gasolina · 4B12");
    assert.equal(r.variantes[0].combustible, "Gasolina");
  });

  test("con vehicleId la respuesta trae la elegida y ya no hay que preguntar", async () => {
    _setFetchForTests(async (url) => {
      llamadas.push(String(url));
      return respuesta({ ...DOS_MOTORES, requiereMotor: false,
        vehiculo: { ...DOS_MOTORES.variantes[1], make: "MITSUBISHI", model: "OUTLANDER III", year: "2020" } });
    });
    const r = await consultarWorker({ make: "Mitsubishi", model: "Outlander", year: 2020, vehicleId: 126681 });
    assert.ok(llamadas[0].includes("vehicleId=126681"));
    assert.equal(r.requiereMotor, false);
    assert.equal(r.vehiculo.vehicleId, 126681);
    assert.equal(r.vehiculo.etiqueta, "2.4 L · 168 PS · Gasolina · 4B12");
  });

  test("por VIN manda solo el VIN, en mayúsculas", async () => {
    await consultarWorker({ vin: " ja4ap4au3lu023739 " });
    assert.ok(llamadas[0].includes("vin=JA4AP4AU3LU023739"));
    assert.ok(!llamadas[0].includes("make="));
  });

  test("sin VIN y sin marca+modelo+año completos: null, sin red", async () => {
    assert.equal(await consultarWorker({ make: "Toyota" }), null);
    assert.equal(llamadas.length, 0);
  });

  test("cuota agotada (503) se distingue de un error común", async () => {
    _setFetchForTests(async () => respuesta({ error: "cuota de este mes agotada" }, 503));
    const r = await consultarWorker({ make: "Toyota", model: "Corolla", year: 2019 });
    assert.equal(r.ok, false);
    assert.equal(r.cuotaAgotada, true);
  });

  test("un 404 del Worker es ok:false (no se inventa un carro)", async () => {
    _setFetchForTests(async () => respuesta({ error: 'no encontramos el modelo "X" de 2020' }, 404));
    const r = await consultarWorker({ make: "Toyota", model: "X", year: 2020 });
    assert.equal(r.ok, false);
    assert.equal(r.cuotaAgotada, false);
    assert.match(r.error, /no encontramos/);
  });

  test("si el Worker no contesta (red caída) devuelve null y nunca lanza", async () => {
    _setFetchForTests(async () => { throw new Error("sin red"); });
    assert.equal(await consultarWorker({ make: "Toyota", model: "Corolla", year: 2019 }), null);
  });

  test("una variante sin combustible queda sin combustible: no se supone gasolina", async () => {
    _setFetchForTests(async () => respuesta({
      ...DOS_MOTORES,
      variantes: [{ vehicleId: 1, variante: "1.0", motor: "X", cilindradaLt: "1.0", potenciaPs: "70", combustible: null }],
      vehiculo: { vehicleId: 1 }, requiereMotor: false,
    }));
    const r = await consultarWorker({ make: "A", model: "B", year: 2020, vehicleId: 1 });
    assert.equal(r.variantes[0].combustible, "");
    assert.ok(!r.variantes[0].etiqueta.includes("Gasolina"));
  });

  test("dos motores con la misma etiqueta se distinguen por el nombre de la variante", async () => {
    _setFetchForTests(async () => respuesta({
      ...DOS_MOTORES,
      variantes: [
        { vehicleId: 1, variante: "1.8 Hybrid A", motor: "2ZR", cilindradaLt: "1.8", potenciaPs: "122", combustible: "Petrol/Electric" },
        { vehicleId: 2, variante: "1.8 Hybrid B", motor: "2ZR", cilindradaLt: "1.8", potenciaPs: "122", combustible: "Petrol/Electric" },
      ],
    }));
    const r = await consultarWorker({ make: "Toyota", model: "Prius", year: 2018 });
    assert.notEqual(r.variantes[0].etiqueta, r.variantes[1].etiqueta);
    assert.ok(r.variantes[0].etiqueta.includes("Híbrido"));
  });
});
