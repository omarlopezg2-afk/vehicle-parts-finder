/**
 * Prueba local del Worker (sin desplegar nada, sin red).
 *   node infra/ebay-notifications/test-worker.mjs
 *
 * Comprueba el contrato que eBay valida al guardar el endpoint:
 *  - GET ?challenge_code=... -> 200, content-type application/json y
 *    challengeResponse = sha256(challengeCode + verificationToken + endpointUrl)
 *  - El hash se contrasta contra una implementación independiente (node:crypto)
 *    para no validar el código con el mismo código.
 *  - GET sin challenge_code -> 400; POST -> 204; otro método -> 405;
 *    sin variables de entorno -> 500 (falla fuerte, no devuelve un hash falso).
 */

import { createHash } from "node:crypto";
import worker, { computeChallengeResponse } from "./worker.js";

const TOKEN = "token_de_prueba_de_32_caracteres_ok";
const ENDPOINT = "https://ebay-notifications.ejemplo.workers.dev/";

let fallos = 0;

function comprobar(nombre, condicion, detalle = "") {
  if (condicion) {
    console.log(`  ok   ${nombre}`);
  } else {
    fallos += 1;
    console.log(`  FALLA ${nombre} ${detalle}`);
  }
}

// 1) El hash coincide con una implementación independiente.
const challengeCode = "challenge-de-prueba-123";
const esperado = createHash("sha256").update(challengeCode + TOKEN + ENDPOINT).digest("hex");
const obtenido = await computeChallengeResponse(challengeCode, TOKEN, ENDPOINT);
comprobar("hash sha256 correcto", obtenido === esperado, `esperado=${esperado} obtenido=${obtenido}`);

// 2) El handler GET responde el contrato de eBay.
const env = { EBAY_VERIFICATION_TOKEN: TOKEN, EBAY_ENDPOINT_URL: ENDPOINT };
const respuesta = await worker.fetch(
  new Request(`https://ejemplo.workers.dev/?challenge_code=${challengeCode}`),
  env,
);
const cuerpo = await respuesta.json();
comprobar("GET devuelve 200", respuesta.status === 200, `status=${respuesta.status}`);
comprobar(
  "GET devuelve content-type application/json",
  (respuesta.headers.get("content-type") || "").includes("application/json"),
);
comprobar("GET devuelve challengeResponse válido", cuerpo.challengeResponse === esperado);

// 3) Casos límite.
const sinCodigo = await worker.fetch(new Request("https://ejemplo.workers.dev/"), env);
comprobar("GET sin challenge_code -> 400", sinCodigo.status === 400, `status=${sinCodigo.status}`);

const post = await worker.fetch(new Request("https://ejemplo.workers.dev/", { method: "POST" }), env);
comprobar("POST -> 204", post.status === 204, `status=${post.status}`);

const put = await worker.fetch(new Request("https://ejemplo.workers.dev/", { method: "PUT" }), env);
comprobar("PUT -> 405", put.status === 405, `status=${put.status}`);

const sinEnv = await worker.fetch(new Request("https://ejemplo.workers.dev/?challenge_code=x"), {});
comprobar("sin variables de entorno -> 500", sinEnv.status === 500, `status=${sinEnv.status}`);

console.log(fallos === 0 ? "\nTODO OK" : `\n${fallos} FALLOS`);
process.exit(fallos === 0 ? 0 : 1);
