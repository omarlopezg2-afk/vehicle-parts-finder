# Tablero de tareas

Estados: `pendiente → en curso → en revisión → aprobada / cambios pedidos`

| ID | Agente | Tarea | Dueño de | Depende de | Estado | Criterios de aceptación |
|---|---|---|---|---|---|---|
| T-A1 | A. Datos-Vehículos | Cliente vPIC: resolver VIN → marca/modelo/año/versión/motor | `pipeline/fetch_vehicles.py` | CONTRACTS.md | **aprobada** (PR #2, merge 03/10) | Dado un VIN válido devuelve el objeto `vehicles.json`; VIN inválido no rompe el pipeline (error controlado); tiene al menos 3 tests con VINs reales (incluido el Mitsubishi Outlander Sport 2020 de Omar) |
| T-B1 | B. Datos-Partes (eBay) | Cliente OAuth client-credentials + búsqueda Browse API por número de parte | `pipeline/fetch_ebay.py` | CONTRACTS.md | **aprobada** (PR #4, merge 03/10) | Modo mock funciona sin llaves (fixture JSON); modo real obtiene token y hace 1 búsqueda real si hay `EBAY_CLIENT_ID`/`EBAY_CLIENT_SECRET` en `.env`; maneja 401/429 sin tumbar el pipeline |
| T-B2 | B. Datos-Partes (eBay) | Normalización de número de parte | `pipeline/normalize.py` | T-B1 | **aprobada** (PR #4, merge 03/10) | `part_number_norm` sigue la regla de CONTRACTS.md; tests con números con guiones/puntos/espacios |
| T-C1 | C. EPC-Puente | Deep links por ensamblaje: 7zap, Partsouq, tienda oficial (Mitsubishi primero) | `pipeline/fetch_epc_links.py` | CONTRACTS.md | **aprobada** (PR #5, merge 03/10) | Para el Outlander Sport 2020 produce al menos 1 `epc_link.url` válido (comprobado a mano, URL abre y muestra el ensamblaje); documenta cómo se construyó la URL por fuente |
| T-D1 | D. Pipeline-Build | Build que une A+B+C en `data/build/*.json` | `pipeline/build_index.py`, `pipeline/validate.py`, `data/seed/` | T-A1, T-B1, T-C1 (o sus mocks) | **aprobada** (PR #6, merge 03/10) | Corre con datos mock de A/B/C y produce los 4 JSON válidos contra el esquema de CONTRACTS.md; `validate.py` sin errores |
| T-E1 | E. Frontend | Buscador + árbol vehículo→ensamblaje + ficha de parte + caja "pega tu número" | `site/` (excepto `assets/categories/`) | CONTRACTS.md (trabaja primero con `data/seed/`) | **aprobada** (PR #7, merge 03/10) | Funciona en móvil y teclado; textos en español; usa solo `dataClient.js` para leer datos; muestra `epc_link` cuando existe |
| T-F1 | F. Diseño-Assets | 12-15 SVG genéricos por categoría + imagen "sin foto" | `site/assets/categories/`, `categories.json` | CONTRACTS.md | **aprobada** (PR #3, merge 03/10) | SVG con estilo consistente, listado: filtro de aceite, filtro de aire, pastillas, discos, bujía, amortiguador, batería, correa, bomba de agua, alternador, faro, limpiaparabrisas + genérico |
| T-G1 | G. DevOps-CI | `ci.yml` (tests + validate en cada push/PR) | `.github/workflows/ci.yml` | — | **aprobada** (PR #1, merge 03/10) | Corre en cada PR, falla si `validate.py` o los tests fallan |
| T-G2 | G. DevOps-CI | `build-data.yml` (recolección programada) + `deploy-site.yml` (Pages) | `.github/workflows/` | T-D1 (al menos en mock) | **aprobada** (PR #8, merge 03/10) | `build-data.yml` corre semanal y en manual dispatch; `deploy-site.yml` publica `site/` en Pages tras cada merge a `main` |
| T-H1 | H. QA-Legal | Revisión de términos eBay + aviso de afiliados/privacidad | `docs/legal.md` | — | **parcial — aprobada** (commit directo del líder, 04/10) | Documento explícito: qué permite guardar eBay (datos/imágenes), aviso de afiliados visible redactado, política de privacidad borrador. Política de privacidad YA publicada en el footer del sitio (verificada contra lo que el código realmente recolecta: solo localStorage, sin cookies ni analítica). Falta solo lo que depende de cuentas reales: activar el aviso de afiliados con campaign ID y relectura final de términos de eBay ya con cuenta activa (Fase 3) |
| T-A2 | A. Datos-Vehículos | Drill-down sin VIN: `get_all_makes()`, `get_models_for_make_year()` | `pipeline/fetch_vehicles.py` | T-A1 | **aprobada** (PR #9, merge 04/10) | Marcas/modelos reales de vPIC (filtro car+mpv), mismo patrón defensivo que `fetch_vehicle`, tests contra API real |
| T-E2 | E. Frontend | Integrar drill-down al frontend (wizard marca→año→modelo) | `site/js/vehiclePicker.js`, `site/js/vpicClient.js` | T-A2, CONTRACTS.md | **aprobada** (PR #10, merge 04/10) | Llega al mismo árbol de categorías que el flujo VIN; `vpicClient.js` aislado de `dataClient.js`; CORS verificado en vivo |

### Fase 2.5 — Mejoras de UX inspiradas en factorymitsubishiparts.com (04/10/2026)

Omar compartió un sitio de referencia (factorymitsubishiparts.com, construido sobre
RevolutionParts — **no es fuente de datos a integrar**, es solo inspiración de interfaz).
4 ideas aprobadas + 1 corrección de layout:

| ID | Agente | Tarea | Dueño de | Depende de | Estado | Criterios de aceptación |
|---|---|---|---|---|---|---|
| T-E3 | E. Frontend | **Layout: VIN y drill-down visibles a la vez** (no detrás de un botón) | `site/index.html`, `site/js/app.js`, `site/css/styles.css` | T-E1, T-E2 | **aprobada** (PR #12, merge 04/10) | Ambos caminos (campo VIN/número + selector marca/año/modelo) visibles en la misma pantalla sin clic adicional; responsive (en móvil pueden apilarse, pero ninguno queda oculto tras un toggle) |
| T-E4 | E. Frontend | **"Mi vehículo" persistente** (localStorage) | `site/js/dataClient.js` o módulo nuevo `site/js/vehicleSession.js` | T-E1, T-E2 | **aprobada** (PR #12, merge 04/10) | Una vez resuelto el vehículo (por VIN o drill-down), se recuerda en toda la sesión del navegador sin volver a pedirlo; opción visible de "cambiar vehículo" |
| T-E5 | E. Frontend | **Categorías destacadas en el home** | `site/index.html`, `site/js/app.js` | T-F1 (ya aprobada) | **aprobada** (PR #12, merge 04/10) | Grid de categorías con los SVG existentes, visible sin necesidad de resolver vehículo primero |
| T-E6 | E. Frontend | **Tabla de fitment visible en la ficha de parte** | `site/js/partCard.js` | CONTRACTS.md | **aprobada** (PR #12, merge 04/10) | Si `fitment_ids[]` tiene elementos, se muestra una tabla año/marca/modelo (resuelta vía `getVehicles()`), no solo el conteo |
| T-D2 | D. Pipeline-Build | Soporte de `other_names[]` en build + búsqueda | `pipeline/build_index.py`, `pipeline/validate.py`, `data/seed/` | CONTRACTS.md (campo agregado 04/10) | **aprobada** (PR #11, merge 04/10) | `other_names` opcional en el esquema; `validate.py` no exige el campo pero lo valida si existe (debe ser array de strings); al menos 1 parte de `data/seed/` con sinónimos de ejemplo |

Nota de dependencia: T-E6 depende solo del campo `fitment_ids` que ya existe en el
contrato (no de T-D2); T-D2 es necesaria para que `other_names` llegue con datos reales a
`dataClient.js`, pero `searchPart()` puede implementarse ya contra el campo del contrato
aunque esté vacío en el build actual.

### Ronda 3 — marcas, trim, categorías jerárquicas (04/10/2026)

Las 3 del backlog de abajo, ahora activas. `CONTRACTS.md` ya tiene `group_slug`/
`group_name_es` en `categories.json` (congelado por el líder antes de lanzar esta ronda).

| ID | Agente | Tarea | Dueño de | Depende de | Estado | Criterios de aceptación |
|---|---|---|---|---|---|---|
| T-A3 | A. Datos-Vehículos | Filtrar marcas industriales del drill-down (Python + JS) | `pipeline/fetch_vehicles.py`, `site/js/vpicClient.js` | T-A2, T-E2 | **aprobada** (PR #14, merge 04/10) | `FREIGHTLINER` y fabricantes de camiones/buses pesados equivalentes ya no aparecen en `get_all_makes()`/`getAllMakes()`; Mitsubishi, Toyota, Honda, Ford, etc. siguen presentes; criterio de exclusión documentado (lista explícita o heurística) y con tests que prueben al menos 3 exclusiones y 3 inclusiones reales contra la API |
| T-C2 | C. EPC-Puente | Investigar si 7zap/Partsouq exponen Trim/submodelo por generación | `pipeline/fetch_epc_links.py` (solo si hay hallazgo que justifique código; si no, el entregable es el hallazgo documentado) | — | **cerrada — ver hallazgo abajo** (04/10, sin código) | Responde con evidencia (no opinión) si alguna fuente gratuita da trims tipo BE/ES/GT/SE/SP para Mitsubishi Outlander Sport 2020; si existe, expone una función que lo devuelva; si NO existe en ninguna fuente gratuita verificada, lo dice explícitamente en el PR en vez de inventar, y la tarea se cierra como "no viable con fuentes gratuitas" sin bloquear nada más |
| T-F2 | F. Diseño-Assets | Categorías jerárquicas: agrupar los 13 slugs existentes en grupos + `categories.json` con `group_slug`/`group_name_es` | `data/build/categories.json` | CONTRACTS.md (jerarquía agregada 04/10) | **aprobada** (PR #13, merge 04/10) | Los 13 slugs actuales quedan agrupados en 6-9 grupos tipo industria (Frenos, Motor, Eléctrico, Suspensión y dirección, Refrigeración, Mantenimiento...); `categories.json` válido contra el nuevo esquema; no hace falta SVG nuevos en esta tarea (son los mismos 13 iconos, solo se agrupan) |
| T-B7 | B. Datos-Partes | **[PILOTO HECHO 05/10] Descubrimiento de piezas por compatibilidad** (el catálogo de 28 no crece solo) | `pipeline/` (módulo nuevo), `data/seed/` o estado en `docs/` | T-B6 (aprobada) | **propuesta** | Hoy el pipeline es una CONSULTA sobre una lista de 28 números que escribió una persona: nada descubre piezas, y ninguna de las 28 tiene fitment (`fitment_ids` vacío en las 28) con 1 solo vehículo en el catálogo. La Browse API ya trae el mecanismo que falta, gratis y en la misma API: `compatibility_filter` = `q` + una categoría con fitment + `Year Make Model` devuelve los anuncios CON su grado de compatibilidad (`compatibilityMatch`) para ese vehículo, así que una consulta por (vehículo × categoría) da las ofertas Y el fitment. Cuota: ~5.000 llamadas/día (hoy gastamos ~30), o sea que el límite no es la API. Criterio de aceptación del PILOTO (medir antes de escalar, Fase 5): 3 vehículos × 5 categorías (~15 llamadas) y reportar (a) cuántas piezas nuevas por consulta, (b) qué fracción trae número de parte utilizable, (c) si `compatibilityMatch` permite afirmar el fitment con honestidad, y (d) el costo de mantenerlo fresco. Solo después se decide escalar |
| T-E9 | E. Frontend | **Implementar la dirección visual B (marketplace de confianza)** en el sitio real | `site/index.html`, `site/css/styles.css`, `site/js/app.js`, `site/js/confianza.js` (nuevo), `site/js/router.js`, `site/js/partCard.js` | T-E7 (aprobada), decisión del usuario 05/10 | **aprobada** (05/10) | El sitio (que era oscuro) pasa a lienzo claro con la paleta B: promesa como titular, un solo buscador dominante con ejemplos clicables, banda de confianza con cifras **calculadas** del catálogo real (28 / 1.194 / 34 / 0 cookies, ver `confianza.js`), tarjetas de categoría y ofertas ordenadas por precio con el más barato destacado. Verificado con navegador real en escritorio y móvil 390px (sin scroll horizontal). Hallazgos del propio trabajo: (a) tras buscar, los resultados quedaban ~1.400 px abajo y el visitante no veía cambio alguno → la portada ahora se recoge (`data-vista` en el body) y el primer resultado queda en y≈333; (b) `site/data/build/*.json` estaba versionado y **desactualizado** (2 piezas frente a 28) → sacado de git, es artefacto del deploy; (c) la primera oferta iba destacada en verde sin estar ordenada, o sea el destacado mentía → se ordena por precio |
| T-E7 | E. Frontend | `categoryTree.js` agrupado por `group_slug` | `site/js/categoryTree.js` | T-F2 | **aprobada** (PR #15, merge 04/10) | El árbol de categorías (tanto en el home T-E5 como dentro del flujo vehículo→categoría) muestra primero el grupo y despliega los slugs hoja al expandir, en vez de una lista plana de 13; responsive y navegable por teclado igual que el resto |

### T-C2 — hallazgo final (04/10/2026, investigación cerrada sin código)

**Conclusión: el nivel de Trim/Submodelo (BE/ES/GT/SE/SP) NO está disponible de forma
gratuita y confiable en ninguna de las dos fuentes EPC del proyecto**, para este vehículo
específico (Mitsubishi Outlander Sport 2020 / GA4W / North America):

- **7zap — confirmado que NO existe en la navegación pública.** Se recorrió la jerarquía
  completa (generación → las 8 categorías de pieza) sin encontrar ningún selector de
  "modification"/trim intermedio. El JSON embebido del sitio sí tiene las claves i18n
  "Trim Code"/"Trim Color" y una función `choose_modification`, pero viven detrás del flujo
  premium "Add to Garage por VIN" (ya confirmado bloqueado con 401/404 en el intento
  anterior) — son infraestructura de la plantilla del sitio, sin datos poblados para este
  vehículo en el catálogo gratuito.
- **Partsouq — ni confirmado ni descartado, bloqueado por Cloudflare.** El acceso directo
  (incluso con curl + headers de navegador real, que en una sesión anterior sí había
  funcionado) devolvió 403/challenge en todas las rutas probadas hoy. Vía resultados ya
  indexados (búsqueda web, no navegación directa) sí se confirma que el **esquema** de
  Partsouq incluye trim real para la familia Mitsubishi North America (ej. Outlander
  hermano del Sport: "SE(4WD,7SEATER)", "ES(2WD,7SEATER)"), y un TSB oficial de NHTSA
  confirma que Mitsubishi sí usa BE/ES/SE/LE/GT como trims reales del Outlander Sport —
  pero no se encontró el registro específico de GA4W/Outlander Sport poblado con el trim
  real, por el bloqueo de acceso.

**Decisión del líder**: no se construye nada para esto ahora. Si en el futuro se quiere
reintentar, el camino más prometedor es Partsouq (su esquema sí tiene el dato), con otra
técnica anti-Cloudflare o otra IP — no vale la pena insistir con 7zap, ahí sí está
confirmado que no está disponible gratis. El wizard de drill-down se queda en 3 niveles
(marca→año→modelo) sin Trim por ahora.

Depende de orden: T-F2 (el dato) antes de T-E7 (la UI que lo consume). T-A3 y T-C2 son
independientes entre sí y de las otras dos — pueden ir todas en paralelo salvo esa
dependencia F2→E7.

## Reglas
- Cada agente solo edita las carpetas de su columna "Dueño de".
- Si necesitas tocar algo fuera de tu carpeta, pide al líder.
- Entrega = Pull Request con descripción (qué hiciste / cómo probarlo / supuestos y
  problemas conocidos) + mover la fila de este tablero a "en revisión".
- El líder revisa con la checklist de PLAN.md y anota el resultado en REVIEW_LOG.md.

### Fase 4 — dominio propio y publicación (04/10/2026)

Cierra el pendiente que quedó abierto al cerrar el nombre de marca: comprar el dominio y
publicar el sitio en él.

| ID | Agente | Tarea | Dueño de | Depende de | Estado | Criterios de aceptación |
|---|---|---|---|---|---|---|
| T-H2 | Líder (con Omar) | Comprar `partexact.com` | Cuenta Cloudflare de Omar (no es código de repo) | T-E7, T-H1 | **aprobada** (04/10) | Dominio registrado a nombre de Omar en Cloudflare Registrar (la misma cuenta que ya tenía `wifimonitor.app`), 10,46 USD/año con renovación automática. Verificado en WHOIS real, no solo en la pantalla de confirmación: `Creation Date: 2026-10-04`, `Registry Expiry Date: 2027-10-04`, registrador Cloudflare |
| T-H3 | Líder | Conectar el dominio a GitHub Pages (DNS + certificado) | DNS de `partexact.com` en Cloudflare + ajustes de Pages por API | T-H2 | **aprobada** (04/10) | 4 registros A en el ápice (185.199.108–111.153) + CNAME `www` → `omarlopezg2-afk.github.io`, **todos en modo DNS only** (sin proxy de Cloudflare: con el proxy naranja activo GitHub no puede emitir su propio certificado); `pages.cname = partexact.com` puesto por API; sitio servido con el título de marca correcto (`PartExact — Encuentra la pieza exacta de tu vehículo`) |
| T-H4 | Líder (con Omar) | Correo del dominio: Email Routing + DMARC | Zona `partexact.com` en Cloudflare | T-H2 | **aprobada** (04/10) | Cloudflare Email Routing activado (3 MX `route*.mx.cloudflare.net`, SPF `include:_spf.mx.cloudflare.net`, DKIM en `cf2024-1._domainkey`) y DMARC Management con `p=none` + reportes; alias `soporte@`, `hola@` y `support@partexact.com` reenviando a la dirección verificada de Omar. Verificado por DNS público (`dig`) **y con una prueba real de punta a punta**: Omar envió un correo desde Gmail a `soporte@partexact.com` y el Activity log de Email Routing lo registra como **Forwarded** |

**Aprendizaje operativo para no rehacer el trabajo la próxima vez**: cuando GitHub Pages
es el origen y el DNS vive en Cloudflare, los registros del sitio **deben** quedar en DNS
only. Si en el futuro se quiere el proxy de Cloudflare por performance/anti-bot, hay que
cambiar el modo SSL a *Full (strict)* y aceptar que el certificado lo emite Cloudflare, no
GitHub — son dos configuraciones excluyentes, no acumulables.

Pendiente de Omar (no bloquea nada del sitio, sí bloquea Fase 3 de monetización):
cuenta eBay Developer ✅ **aprobada** (correo recibido 04/10) — falta crear el keyset de
**Production** y darme Client ID + Client Secret para activar el modo real de
`fetch_ebay.py` (GitHub Secrets + `.env` local, nunca en el repo). Advance Auto Parts vía
Impact.com, sigue pendiente para Fase 3.

### Fase 3 — eBay en producción (04/10/2026)

Camino completo documentado en `docs/ebay-produccion.md`. Resumen del hallazgo que cambia
el plan: **el keyset de Production no se activa solo** — eBay exige antes suscribirse a las
notificaciones de borrado de cuenta o acogerse a una exención, y la exención ("no se
persisten datos de eBay") sería falsa en nuestro caso porque sí persistimos resúmenes de
anuncios en `data/build/parts.json`. Se va por la suscripción, que cuesta un Worker gratis.

| ID | Agente | Tarea | Dueño de | Depende de | Estado | Criterios de aceptación |
|---|---|---|---|---|---|---|
| T-B2 | Líder | Endpoint de notificaciones de eBay (reto de verificación + acuse) | `infra/ebay-notifications/` | T-B1 | **desplegado y verificado** (04/10) | Hash `sha256(challenge_code + verification_token + endpoint_url)` en el orden exacto que exige eBay, `content-type: application/json`, 400 sin `challenge_code`, 204 ante el POST de borrado, 405 en otros métodos y 500 (falla fuerte) si faltan variables en vez de devolver un hash falso. 8/8 comprobaciones en local y en CI. **Desplegado** con Wrangler en el subdominio propio `ebay.partexact.com` (registro proxeado creado por Wrangler; el ápice sigue en DNS only y el sitio no se tocó) y comprobado contra el endpoint real: el hash que devuelve coincide carácter por carácter con el calculado en local, y los casos límite responden 400/204/405 |
| T-B3 | Omar (sesión de eBay) | Crear el keyset de Production y registrar el endpoint de notificaciones | Portal de eBay + deploy del Worker | T-B2 | **aprobada** (04/10) | Keyset de Production creado (App ID / Dev ID / Cert ID; contacto legal = Omar, tipo Individual) y endpoint registrado en *Alerts & Notifications*: URL `https://ebay.partexact.com/` + token de verificación, con la exención apagada a propósito. eBay disparó el reto y nuestro endpoint respondió 200 (visto en vivo con `wrangler tail`), el keyset pasó de *Non Compliant* a activo y el token de OAuth funciona |
| T-B4 | Omar + líder | Cargar las llaves y correr el pipeline real | `.env` local + GitHub Secrets | T-B3 | **aprobada** (04/10) | Llaves cargadas con `scripts/seed-secrets.sh` (sin exponerlas) y **token real obtenido** de `api.ebay.com` + búsqueda real del Browse API (3.846 resultados para `04152YZZA1`). `build-data.yml` regeneró `data/build/*.json` **con ofertas reales** (103 ofertas de eBay en 3 partes, precios y URLs reales) y el sitio en `partexact.com` ya las sirve. El Cert ID nunca apareció en el repo, en un chat ni en un log |
| T-B5 | B. Datos-Partes (eBay) | Enlaces de afiliado: usar el campaign ID de eBay Partner Network | `pipeline/fetch_ebay.py`, `pipeline/tests/` | T-B4 | **aprobada** (04/10, PR #16) — activación pendiente del ID real de EPN | Con `EBAY_CAMPAIGN_ID` en el entorno, la búsqueda manda el header `X-EBAY-C-ENDUSERCTX: affiliateCampaignId=<id>` (+ `affiliateReferenceId=<ref>` si existe `EBAY_REFERENCE_ID`) y `offer.url` usa **`itemAffiliateWebUrl`** (que es lo que eBay exige para pagar comisión: *"you must use the URL returned in the itemAffiliateWebUrl field"*), con caída a `itemWebUrl` si no viene. Sin la variable, el comportamiento actual **no cambia** (enlaces normales) — verificado con una búsqueda real sin la variable. 9 pruebas nuevas en `pipeline/tests/test_fetch_ebay.py` (header presente con valor correcto, ausente sin la variable, reference id en el header, URL afiliada preferida sobre la normal, caída correcta cuando no viene o viene vacía) — 105/105 en verde. Verificado también con una búsqueda **real** y un campaign id de prueba inventado (`5338800000`, nunca usar en producción): eBay sí devolvió `itemAffiliateWebUrl` con `campid`/`customid`/`mkevt` etc. (detalle en `docs/ebay-produccion.md`). Falta solo el ID real de la cuenta EPN de Omar |
| T-H2 | H. QA-Legal + E. Frontend | Aviso de afiliados visible en el footer | `site/index.html`, `docs/legal.md` | T-B5 **y** un campaign ID real activo | **pendiente, bloqueada por el ID** | El texto ya está redactado y aprobado en `docs/legal.md` §4. Se inserta en el footer (visible en todas las páginas) **solo cuando los enlaces lleven el campaign ID de verdad**: un aviso de afiliados sin enlaces de afiliado es tan incorrecto como lo contrario. Cierra el checklist de T-H1 |
| T-O1 | Omar + líder | **Aclarar el rechazo de eBay Partner Network** | Nada del repo (correo a `epnhelp@ebay.com`) | — | **enviada** (04/10 17:40) | Comprobación (1) **resuelta: no existe cuenta EPN** — solo el perfil de la solicitud declinada (lo verificó Omar en el panel; mi inferencia de "cuenta duplicada" quedó descartada y documentada). Queda (2): comprobar que la cuenta de eBay usada está "in good standing" (el acuerdo lo exige en todo momento). **Investigación de fuentes primarias hecha**: ver `docs/epn-investigacion.md` — el rechazo es discrecional y sin apelación de derecho; no hay lista pública de países soportados; el límite declarado es la capacidad de pago (y el peso dominicano no está entre las monedas de pago); y **todo método promocional no expresamente permitido exige aprobación previa por escrito**. Correo a `epnhelp@ebay.com` **enviado el 04/10 a las 17:40** (texto íntegro en `docs/carta-epn.md`): ya no pregunta "por qué me rechazaron" sino **qué modelo declarar y qué aprobación previa hace falta** |
| T-O2 | Líder (investigación) | **Plan B de monetización** si EPN queda cerrado | `docs/` | T-O1 | **pendiente, bloqueada por T-O1** | Investigar con fuentes oficiales qué redes de afiliados aceptan **publicadores en República Dominicana** — empezando por Impact.com (la red de Advance Auto Parts ya planificada) y sin dar por hecho que acepta. Si ninguna acepta, decirlo con la evidencia y replantear la Fase 3 completa (el sitio puede seguir vivo y útil sin comisión) |
| T-O3 | Líder | **Pedir la aprobación previa por escrito del método promocional real (Buy API Program / método restringido)** | `docs/epn-investigacion.md`, correo a EPN | T-O1 | **enviado** (04/10 17:40, en el mismo correo que T-O1) | Redactar la descripción **exacta** del método real — una herramienta que consulta la Browse API y muestra anuncios de eBay al usuario, con el enlace usando la URL afiliada (`itemAffiliateWebUrl`) — y pedir la aprobación previa que exige EXHIBIT A para todo método no expresamente permitido; si corresponde, vía *Buy API Program* (definición 8 del acuerdo). Va en **el mismo envío** que T-O1: una sola carta con las tres preguntas (qué modelo declarar, qué aprobación previa hace falta, y si RD está soportado para pagos). Criterio de aceptación: la carta describe el método sin ambigüedad y **en ningún punto** dice "contenido/reviews" |

**Regla de llaves (no negociable)**: el Cert ID es un secreto — va en `.env` (ignorado por
git) y en GitHub Secrets, cargado desde el archivo con `scripts/seed-secrets.sh` (lee el
`.env` y usa la entrada estándar de `gh secret set`, para que el valor no pase por la línea
de comandos, que es visible para otros procesos del sistema). El repo es **público**.

## Backlog — próxima ronda (04/10/2026, pedido explícito de Omar, no lanzar todavía)

Omar probó el drill-down y encontró 3 huecos reales, verificados contra vPIC antes de
anotarlos (no son solo opinión):

1. **Filtro de marcas sucio.** `get_all_makes()`/`getAllMakes()` usan `GetMakesForVehicleType`
   con tipos `car`+`mpv`, pero eso TODAVÍA mezcla fabricantes industriales (confirmado:
   `FREIGHTLINER` aparece en ambos tipos junto a Toyota/BMW). Hace falta una lista de
   exclusión explícita o un criterio más fino — no hay endpoint de vPIC que lo resuelva solo.

2. **Falta el nivel de Trim/Submodelo.** Omar mandó una imagen de factorymitsubishiparts.com
   mostrando, para su Outlander Sport 2020: trims BE, ES, GT, SE, SP — un 4º nivel después
   de marca→modelo→año que hoy no existe en nuestro wizard. **Verificado que vPIC NO lo
   resuelve de forma confiable**: no hay endpoint para listar trims por marca+modelo+año
   (solo aparece a veces decodificando un VIN específico — probé el propio VIN de Omar y
   el campo `Trim` vino vacío, mientras que otro VIN de prueba sí lo trajo). Esos BE/ES/GT/
   SE/SP salen de la base de datos propia de RevolutionParts/el dealer, no de una fuente
   gratuita equivalente. Investigar antes de prometerlo: ¿lo tiene 7zap o Partsouq en su
   propia navegación por generación? Si no, puede quedar fuera de alcance del MVP o
   resolverse solo cuando el usuario ya trae VIN completo (ahí si vPIC a veces lo da).

3. **Categorías del catálogo, más granulares.** Hoy son 13 slugs planos (filtro-aceite,
   pastillas-freno...). Omar sugirió mirar factorymitsubishiparts.com (ya revisado, son
   ~20 categorías de reemplazo + accesorios) y RockAuto (taxonomía estándar de la industria:
   sistema → subsistema → pieza, ej. "Frenos y buje de rueda" → "Pastilla de freno" — esto
   es terminología genérica del sector, no contenido propietario de RockAuto, así que se
   puede adoptar la estructura sin copiar nada). Evaluar pasar de 13 slugs planos a una
   jerarquía de 2 niveles; implica tocar `categories.json`, los SVG (T-F1, puede necesitar
   más iconos) y `categoryTree.js`.

Omar pidió arrancar con esto el 04/10/2026 (fin de la sesión de eBay): estas 3 pasan a
**Ronda 4, en curso**. Se conserva la nota original arriba porque documenta la investigación
de vPIC ya hecha y no hay que repetirla.

### Verificación del líder antes de repartir (04/10/2026)

- **Punto 1, parcialmente hecho**: T-A3 ya está fusionada y `_MARCAS_INDUSTRIALES_EXCLUIDAS`
  (comparación por **nombre exacto**) sí saca a FREIGHTLINER, BLUE BIRD y ORION BUS. Pero el
  problema no está cerrado: consultando `get_all_makes()` en vivo hoy devuelve **244 marcas**
  y el filtro por nombre todavía deja pasar una cola de fabricantes de buses/limusinas/
  carrocerías (ej. `Autocar Ltd`, `Execucoach Inc`, `Londoncoach Inc`, `Daytona Coach
  Builders`, `Creative Coachworks`). Ojo al verificar: varias candidatas son **falsos
  positivos** de una búsqueda por substring (ej. `Sprinter (Dodge Or Freightliner)` es una
  van de pasajeros legítima; `Morgan` y `Sterling Motor Car` son autos). La comparación debe
  ser por igualdad exacta, nunca `'X' in nombre`.
- **Punto 3, bug real encontrado**: la parte `MR297182` del seed usa la categoría
  `clip-parachoques`, que **no existe** en `categories.json`. Hoy el sitio sirve una parte que
  no aparece en ninguna categoría. No lo detecta `validate.py` porque valida la forma de cada
  archivo por separado y no la integridad referencial entre ellos.

### Ronda 4 — tablero

| ID | Agente | Tarea | Dueño de | Depende de | Estado | Criterios de aceptación |
|---|---|---|---|---|---|---|
| T-A4 | A. Datos-Vehículos | Criterio de marcas **basado en datos**, no en una lista corta a mano | `pipeline/fetch_vehicles.py`, `pipeline/tests/`, `data/build/vehicles.json` | T-A3 | **aprobada** (04/10, PR #20, revisada y corregida por el líder) | Un criterio verificable contra vPIC (p. ej. "la marca tiene ≥1 modelo bajo `vehicletype=car`/`mpv` en un año reciente") con caché local y **fallback offline** para no romper el pipeline sin red; la lista resultante se documenta con su conteo. Pruebas que fijan: **excluidas** por nombre exacto `Autocar Ltd`, `Execucoach Inc`, `Londoncoach Inc`, `Daytona Coach Builders`, `Creative Coachworks`; **presentes** `Toyota`, `Mitsubishi`, `Honda`, `BMW`, `Byd`, `Sprinter (Dodge Or Freightliner)`, `Morgan`, `Sterling Motor Car`. Si el criterio descarta alguna de las que hay que mantener, se ajusta el criterio, no la lista de pruebas |
| T-A5 | E. Frontend (o A) | **Llevar el criterio de fabricante-cascarón al navegador** (`site/js/vpicClient.js`) | `site/js/vpicClient.js`, `site/tests/` | T-A4 | **pendiente** | Hoy el filtro vive **solo** en `pipeline/fetch_vehicles.py`: el desplegable del sitio sigue pidiendo la lista de marcas a vPIC desde el navegador y **no aplica el criterio**, así que los fabricantes-cascarón pueden reaparecer en el selector del usuario. Criterio de aceptación: el navegador descarta exactamente las mismas marcas que el pipeline (probado con las 5 que deben salir y las 8 que deben quedarse) y **sin duplicar la lógica en dos lenguajes**: el criterio o la lista resultante se extrae a un dato compartido que ambos consuman |
| T-E8 | E. Frontend | **El botón "atrás" del navegador pierde el estado** (lo reportó alguien probando el sitio) | `site/js/router.js` (nuevo), `site/js/app.js`, `site/tests/` | — | **aprobada** (05/10, PR directo del líder). NOTA: los commits lo llaman `T-E5` porque ese id ya estaba tomado arriba por "Categorías destacadas"; aquí queda como T-E8 para que no se repita | Síntoma: el visitante busca una pieza, pulsa **atrás** y vuelve **al inicio del sitio** en vez de a la vista anterior. Causa medida, no supuesta: `site/js/*.js` **no usa en ningún punto** `pushState`/`replaceState`/`location.hash`/`popstate` (verificado con grep), así que ninguna vista deja entrada en el historial y atrás sale de la página. Arreglo: router por hash con un estado canónico por vista (`#/numero/<n>`, `#/categoria/<slug>`, `#/vehiculo/<marca>/<modelo>/<año>`, `#/vin/<vin>`), `navigate()` en cada flujo, y restauración al cargar y en `hashchange`. Beneficio extra: los enlaces pasan a ser **compartibles** (una pieza concreta tendrá URL propia, que para un buscador de piezas vale mucho). Criterio de aceptación: pruebas de ida y vuelta URL↔estado en `site/tests/router.test.js`, **y** verificación con navegador real: buscar → atrás → **debe verse la vista anterior**; y recargar una URL de pieza debe mostrar esa pieza |
| T-B8 | B. Datos-Partes | **Catálogo por fitment (vehículo × categoría)**, sin perseguir números de parte | `pipeline/` (módulo nuevo), `data/build/` | T-B7 (piloto hecho: `docs/piloto-tb7.md`) | **terminada** (05-06/10, commit `649c810`, 93 ofertas EXACT verificadas) | El piloto de T-B7 midió que `compatibility_filter` con una categoría del árbol de eBay Motors (**100**) devuelve los anuncios que le quedan EXACTO a un vehículo concreto (50/50 en limpiaparabrisas, 48/50 en filtros de aire), con foto, precio y condición — gratis. Y midió que **el número de parte NO es alcanzable** con nuestras llaves (`mpn` ausente; la API de catálogo responde 403). Criterio: construir el catálogo emparejando vehículos × categorías de Motors, deduplicar y ordenar la oferta, y mostrar en el sitio "esto le queda exacto a tu carro" con el diagrama oficial (`epc_link`) para el número. **No prometer el número exacto**: no se puede cumplir |
| T-B6 | B. Datos-Partes | **Traer y guardar la foto de la oferta** (hoy no se guarda ninguna) | `pipeline/fetch_ebay.py`, `CONTRACTS.md`, `data/build/` | T-B4 | **aprobada** (05/10) | Verificado el 05/10/2026 mirando `data/build/parts.json`: las ofertas traen `store`, `url`, `price`, `currency`, `condition` y `updated_at`, pero **ninguna imagen**, y `part.image` es `{url: null, source: "generic"}`. La Browse API devuelve la imagen del anuncio, así que hoy se está descartando. Es la causa de que el sitio no pueda mostrar ni una foto de pieza. Criterio de aceptación: `fetch_ebay.py` pide y guarda la URL de la imagen de cada oferta (campo nuevo en el contrato, documentado en `CONTRACTS.md`), `validate.py` lo comprueba si está presente, y el build real trae fotos en una fracción alta de las ofertas. **Ojo con el peso**: no se descargan las imágenes, solo su URL; y hay que decidir si se usa la de eBay directamente (más simple, más rápido, depende de su CDN) o se copia a nuestro hosting (más control, más costo) |
| T-C3 | C. EPC-Puente | **Investigación**: ¿existe el nivel Trim/Submodelo en alguna fuente gratuita? | `docs/trim-investigacion.md` | — | **aprobada** (04/10, PR #18) — decisión: fuera del MVP | Hallazgo (evidencia en vivo, 04/10/2026): vPIC no tiene endpoint de listado de trims por marca+modelo+año; con VIN real, **0 de 10** VIN de Outlander Sport 2020 trajeron `Trim` poblado; 7zap llega solo a generación/sistema (nunca a trim); Partsouq por VIN resuelve por plataforma GA2W y variantes de mercado (P&G/MMNA), no trims de marketing — confirma y refuerza con más muestra lo ya investigado, sin encontrar camino público nuevo. **Decisión: dejar el trim fuera del MVP**; añadirlo solo cuando el usuario trae un VIN completo y `Trim` viene poblado para ESE VIN (dato opcional, no 4º paso obligatorio del asistente). Informe completo en `docs/trim-investigacion.md` |
| T-D5 | D. Pipeline-Build | Seed de **≥24 partes reales** + integridad referencial en la validación | `data/seed/`, `pipeline/validate.py`, `pipeline/build_index.py` | Taxonomía congelada (`docs/taxonomia-categorias.md`) | **aprobada** (04/10, PR #19, integrada por el líder) | Al menos 24 partes en `data/seed/` (hoy hay 3) repartidas de forma que **≥20 de las 33 categorías** tengan al menos una parte; cada parte con `part_number` real y **verificada contra el Browse API real** (existe al menos 1 oferta), con la evidencia anotada en el PR; `MR297182` migrada a `clips-y-sujeciones`; `validate.py` detecta y falla si `parts.json.category` no está en `categories.json` o si un `fitment_ids` no existe en `vehicles.json` (con prueba que lo demuestre, no solo el código) |
| T-F3 | F. Diseño-Assets | Implementar la taxonomía: `categories.json` + SVG faltantes | `site/assets/categories/`, `pipeline/` (solo la parte de categorías), `categories.json` | Taxonomía congelada (`docs/taxonomia-categorias.md`) | **aprobada** (04/10, PR #17) | `data/build/categories.json` reescrito con las 33 categorías de producto del documento (8 grupos) + el marcador `generico-sin-foto` (grupo `otros`, no cuenta como producto) = 34 entradas, las 5 claves (`slug`,`name_es`,`svg`,`group_slug`,`group_name_es`) iguales al documento; `site/data/build/categories.json` sincronizado. Se crearon los 21 SVG nuevos en `site/assets/categories/` (mismo viewBox `0 0 64 64`, `stroke="currentColor"`, `stroke-width="2.5"`, sin color de marca, que los 13 existentes) — total 34 SVG. Prueba nueva `pipeline/tests/test_categories_taxonomy.py` (9 casos) verifica las dos direcciones pedidas: todo `svg` de `categories.json` existe en disco (y es XML válido con ese viewBox), y todo slug de producto está en la lista congelada del documento con sus 5 campos coincidentes; se comprobó a mano que se pone en rojo quitando `radiador.svg` y vuelve a verde al restaurarlo. `pipeline/build_index.py` no se tocó (sigue sin regenerar categorías, solo valida/lee). `python -m pytest pipeline/ -q`: 107 passed. `node --test site/tests/*.test.js`: 52 passed (no se tocó `categoryTree.js` ni su test, usan datos de ejemplo inline). Supuesto documentado: `clip-parachoques` (usado por `MR297182` en el seed) no existe en esta taxonomía; el agente D migra ese seed a `clips-y-sujeciones`, que ya está creado aquí con su SVG. Si al cerrar la ronda alguna de las 33 categorías queda sin parte real en el seed (depende de T-D5, en paralelo), es aceptable por diseño — ver `docs/taxonomia-categorias.md`. |

### Ronda 5 — lo que abrió la revisión de la placa (06/10/2026)

| ID | Tema | Tarea | Dueño de | Depende de | Estado | Criterios de aceptación |
|---|---|---|---|---|---|---|
| T-B9 | Placa / chasis | **"Leer el vehículo por VIN": VIN -> vPIC -> atributos -> fitment de eBay** | `pipeline/` (decodificador + integración), `site/js/` (entrada nueva) | Nada: el VIN del usuario ya validó la cadena | **investigada y lista para construir** — la revisión del 06/10 cerró la duda | Hallazgo verificado (06/10): **no existe** servicio público placa -> chasis en RD (la consulta oficial de la DGII exige cédula/RNC + placa y no devuelve el chasis; no hay API ni datos abiertos). Pero la DGII **sí publica** el chasis por el **QR del marbete** (*"marca y modelo... color, año de fabricación, número de placa y chasis"*, brochure oficial y ficha CA3238) y por el de la **placa provisional electrónica** (ficha CA4946), y declara ese dato fidedigno *"siempre y cuando provenga del dominio https://dgii.gov.do/"*. Criterio: comprobar con el marbete del usuario qué abre ese QR; si es una URL/código que resuelve a la ficha, el sitio acepta ese enlace (o ese código) y obtiene el chasis **con el usuario delante y sin tecleo**, y a partir de ahí busca las piezas. Si no resuelve a nada usable, se cierra la tarea y se queda la matrícula (que siempre trae el VIN) como entrada manual. **No** se scrapea el portal de la DGII ni se usan los "consulta la placa sin cédula": datos del propietario y Ley 172-13 |
| T-B10 | Catálogo / número | **Decidir y probar la API de catálogo de AUTODOC (RapidAPI)** | `.env` (`RAPIDAPI_KEY` ya reservada), `pipeline/` | Decisión del usuario | **propuesta — espera decisión** | Medido (06/10): plan gratis de **100 consultas** y **29 USD/mes por 20.000**; da vehículo -> piezas numeradas, **referencias cruzadas OEM/aftermarket**, diagramas y fotos, y su documentación declara que es para herramientas de consulta y comparación. Traducido: armar el catálogo de un vehículo son **9 consultas** y el catálogo dominicano estimado (300 vehículos) son **2.700**, o sea **cabe 7 veces** en el plan de 29 USD; las búsquedas de los usuarios **no gastan consultas** porque el catálogo se arma una vez al mes. Criterio: con la clave en `.env`, una prueba de 6-10 consultas con un vehículo del mercado **estadounidense** (el único cabo suelto: AUTODOC es europeo) que demuestre si devuelve o no el número de parte. Si devuelve, T-B11 y buena parte del resto del catálogo dejan de hacer falta |

**Orden**: T-B9 y T-B10 son independientes entre sí y de la Ronda 4. T-B10 puede cambiar el alcance de T-B11 (que se escribe **después** de saber si la API responde), y por eso no se abre todavía.

**Orden de integración**: T-A4 y T-C3 son independientes. T-D5 y T-F3 comparten la taxonomía
congelada, así que van en paralelo **contra el documento**, y el líder los integra juntos y
corre el build completo antes de cerrar (productor de datos + catálogo de categorías: si se
fusionan por separado y sin probarlos juntos, una parte puede quedar apuntando a una categoría
que existe en un PR y no en el otro).
