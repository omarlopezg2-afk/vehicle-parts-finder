/**
 * Endpoint de notificaciones de eBay — Marketplace Account Deletion/Closure.
 *
 * POR QUÉ EXISTE ESTE ARCHIVO:
 * eBay no activa el keyset de **Production** hasta que la aplicación esté
 * suscrita a las notificaciones de borrado/cierre de cuenta (o se acoja a una
 * exención). Sin esto, el App ID / Cert ID de producción existen en el panel
 * pero cualquier llamada real falla. Ver docs/ebay-produccion.md.
 *
 * QUÉ HACE:
 *  - GET  ?challenge_code=...  → responde { "challengeResponse": "<sha256>" }
 *    con el hash de challengeCode + verificationToken + endpointURL, que es la
 *    prueba de que controlamos esta URL. eBay lo llama al guardar el endpoint.
 *  - POST                      → acuse inmediato (204) de una notificación real
 *    de borrado de cuenta.
 *
 * QUÉ NO HACE, A PROPÓSITO:
 * No guarda ni procesa datos de usuarios de eBay. Este proyecto nunca recibe
 * ni almacena datos personales de usuarios de eBay (no usa tokens de usuario,
 * no guarda usuarios, solo resúmenes públicos de anuncios), así que no hay nada
 * que borrar cuando llega una notificación: se acusa recibo y se registra.
 * La verificación de firma del POST (cabecera x-ebay-signature) sería el
 * siguiente paso si algún día guardáramos datos de usuarios; hoy sería
 * ceremonia sin efecto, y por eso está documentada como pendiente y no
 * implementada en falso.
 */

/**
 * Hash que eBay espera como respuesta al reto.
 * El orden de la concatenación es obligatorio y el endpoointURL debe ser
 * EXACTAMENTE el configurado en el portal (mismos query params si los hay).
 */
export async function computeChallengeResponse(challengeCode, verificationToken, endpointUrl) {
  const data = `${challengeCode}${verificationToken}${endpointUrl}`;
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(data));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "GET") {
      const challengeCode = url.searchParams.get("challenge_code");
      if (!challengeCode) {
        return new Response(JSON.stringify({ error: "falta el parámetro challenge_code" }), {
          status: 400,
          headers: { "content-type": "application/json" },
        });
      }
      if (!env.EBAY_VERIFICATION_TOKEN || !env.EBAY_ENDPOINT_URL) {
        // Fallar fuerte en vez de devolver un hash con datos vacíos: si el hash
        // no cuadra, eBay marca el endpoint como no verificado y el keyset de
        // producción sigue bloqueado sin decir exactamente por qué.
        return new Response(
          JSON.stringify({ error: "faltan EBAY_VERIFICATION_TOKEN o EBAY_ENDPOINT_URL" }),
          { status: 500, headers: { "content-type": "application/json" } },
        );
      }
      const challengeResponse = await computeChallengeResponse(
        challengeCode,
        env.EBAY_VERIFICATION_TOKEN,
        env.EBAY_ENDPOINT_URL,
      );
      return new Response(JSON.stringify({ challengeResponse }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }

    if (request.method === "POST") {
      // Acuse inmediato: eBay reintenta si no se responde 2xx con rapidez.
      // No hay datos de usuario que borrar (ver cabecera del archivo).
      return new Response(null, { status: 204 });
    }

    return new Response("Method not allowed", { status: 405 });
  },
};
