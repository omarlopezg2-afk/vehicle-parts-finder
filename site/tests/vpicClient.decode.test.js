// site/tests/vpicClient.decode.test.js
//
// Pruebas herméticas (sin red) de decodeVIN: el flujo VIN del sitio depende de
// este módulo para identificar vehículos que NO están en nuestro catálogo, así
// que se fija el contrato con la respuesta real de vPIC y los casos que no deben
// romper la página.
import test from "node:test";
import assert from "node:assert/strict";
import { decodeVIN } from "../js/vpicClient.js";

// Respuesta real de vPIC para un Mitsubishi Outlander Sport 2020 (recortada a los
// campos que usamos), verificada contra el servicio el 06/10/2026.
const RESPUESTA_REAL = {
  Results: [
    {
      ErrorCode: "0",
      ErrorText: "0 - VIN decoded clean. Check Digit (9th position) is correct",
      Make: "MITSUBISHI",
      Model: "Outlander Sport",
      ModelYear: "2020",
      Trim: "SE",
      BodyClass: "Sport Utility Vehicle (SUV)/Multi-Purpose Vehicle (MPV)",
      DriveType: "4x2",
      EngineCylinders: "4",
      DisplacementL: "2",
      EngineHP: "148",
      FuelTypePrimary: "Gasoline",
      TransmissionStyle: "Continuously Variable Transmission (CVT)",
      PlantCountry: "JAPAN",
    },
  ],
};

function fetchFalso(respuesta, { ok = true, status = 200, lanza = null } = {}) {
  const llamadas = [];
  const impl = async (url) => {
    llamadas.push(url);
    if (lanza) throw lanza;
    return { ok, status, json: async () => respuesta };
  };
  impl.llamadas = llamadas;
  return impl;
}

const VIN = "JA4AP4AU3LU023739";

test("decodeVIN devuelve el vehículo normalizado y en Title Case", async () => {
  const impl = fetchFalso(RESPUESTA_REAL);
  const d = await decodeVIN(VIN, { fetchImpl: impl });

  assert.equal(d.vin, VIN);
  assert.equal(d.valido, true);
  assert.equal(d.make, "Mitsubishi");
  assert.equal(d.model, "Outlander Sport");
  assert.equal(d.year, "2020");
  assert.equal(d.trim, "SE");
  assert.equal(d.driveType, "4x2");
  assert.equal(d.engineCylinders, "4");
  assert.equal(d.displacementL, "2");
  assert.equal(d.engineHP, "148");
  assert.equal(d.fuelType, "Gasoline");
  assert.equal(d.transmission, "Continuously Variable Transmission (CVT)");
  assert.equal(d.plantCountry, "JAPAN");
});

test("decodeVIN consulta decodevinvalues con el VIN en mayúsculas", async () => {
  const impl = fetchFalso(RESPUESTA_REAL);
  await decodeVIN("ja4ap4au3lu023739", { fetchImpl: impl });

  assert.equal(impl.llamadas.length, 1);
  assert.match(impl.llamadas[0], /decodevinvalues\/JA4AP4AU3LU023739\?format=json$/);
});

test("decodeVIN marca valido=false cuando vPIC reporta un error", async () => {
  const impl = fetchFalso({
    Results: [{ ErrorCode: "1", ErrorText: "1 - Check digit invalid", Make: "MITSUBISHI" }],
  });
  const d = await decodeVIN(VIN, { fetchImpl: impl });

  assert.equal(d.valido, false);
  assert.match(d.errorText, /Check digit invalid/);
});

test("decodeVIN devuelve null si el VIN no tiene 17 caracteres (sin llamar a la red)", async () => {
  const impl = fetchFalso(RESPUESTA_REAL);

  assert.equal(await decodeVIN("12345", { fetchImpl: impl }), null);
  assert.equal(await decodeVIN("", { fetchImpl: impl }), null);
  assert.equal(await decodeVIN(null, { fetchImpl: impl }), null);
  assert.equal(impl.llamadas.length, 0);
});

test("decodeVIN devuelve null si la red o el servicio fallan, sin lanzar", async () => {
  const sinResultados = fetchFalso({ Results: [] });
  assert.equal(await decodeVIN(VIN, { fetchImpl: sinResultados }), null);

  const httpError = fetchFalso(null, { ok: false, status: 500 });
  assert.equal(await decodeVIN(VIN, { fetchImpl: httpError }), null);

  const redCaida = fetchFalso(null, { lanza: new Error("fallo de red") });
  assert.equal(await decodeVIN(VIN, { fetchImpl: redCaida }), null);
});
