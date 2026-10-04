# Endpoint de notificaciones de eBay (Marketplace Account Deletion)

Este Worker existe por un requisito de eBay, no por gusto: **sin suscribirse a las
notificaciones de borrado/cierre de cuenta (o acogerse a la exención), eBay no activa el
keyset de Production** — el App ID y el Cert ID aparecen en el panel, pero la primera
llamada real falla. Ver `docs/ebay-produccion.md` para el camino completo.

Qué hace, en dos líneas:

- `GET /?challenge_code=...` → `{"challengeResponse": "<sha256>"}`, donde el hash es
  `sha256(challenge_code + verification_token + endpoint_url)`, en ese orden exacto. Es la
  prueba de que controlamos la URL; eBay la llama al guardar el endpoint en el portal.
- `POST` → acuse inmediato con `204`. Este proyecto no guarda datos personales de usuarios
  de eBay, así que no hay nada que borrar; la notificación se acusa y se registra.

## Probar en local (sin desplegar nada)

```bash
node infra/ebay-notifications/test-worker.mjs
```

Verifica el contrato completo (hash contrastado contra una implementación independiente,
códigos 200/204/400/405/500). Este test corre también en CI.

## Desplegar

Dos caminos; el segundo no necesita instalar nada.

### A) Panel de Cloudflare (sin CLI)

1. **Compute → Workers & Pages → Create → Worker**, nombre `ebay-notifications`.
2. Pegar el contenido de `worker.js` y **Deploy**.
3. En `Settings → Variables and Secrets`, agregar:
   - `EBAY_ENDPOINT_URL` (texto): la URL pública exacta del Worker, con barra final si así
     se registra en eBay — `https://ebay-notifications.<subdominio>.workers.dev/`.
   - `EBAY_VERIFICATION_TOKEN` (**secret**): 32–80 caracteres, solo letras, números, guion
     y guion bajo.
4. Anotar la URL final. Tiene que ser **idéntica** a la que se guarde en el portal de eBay:
   el hash del reto la incluye carácter por carácter (incluidos query params si los hay).

### B) Wrangler

```bash
cd infra/ebay-notifications
npx wrangler login                       # abre el navegador
# poner la URL real en wrangler.toml ([vars] EBAY_ENDPOINT_URL)
npx wrangler deploy
npx wrangler secret put EBAY_VERIFICATION_TOKEN
```

### Probar el endpoint ya desplegado

```bash
# debe devolver {"challengeResponse":"<hex>"} con content-type application/json
curl -s "https://<endpoint>/?challenge_code=123"
```

## Registrar el endpoint en eBay

En el portal de desarrolladores: **Application Keys → Notifications** (junto al App ID) →
*Marketplace Account Deletion* → correo de alertas → **Notification Endpoint URL** →
**Verification token** (el mismo del Worker) → *Save*. eBay dispara el reto en ese momento:
si el hash cuadra, el endpoint queda verificado y el keyset de producción se activa.

Errores clásicos de esta validación: URL guardada distinta a la que hash-ea el código,
orden de concatenación equivocado, `content-type` que no sea `application/json`, o un token
fuera del rango de 32–80 caracteres.

## Pendiente, documentado y no implementado en falso

La notificación `POST` **no verifica la firma** `x-ebay-signature` (clave pública de eBay vía
`getPublicKey`). Es una omisión deliberada: hoy no hay datos de usuario que proteger, y
fingir una verificación que no se usa sería peor que no tenerla. Si algún día el proyecto
guarda datos de usuarios de eBay, este es el primer punto a tocar.
