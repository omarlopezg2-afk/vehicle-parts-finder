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

No lanzar estas 3 hasta que Omar lo pida — quedan aquí documentadas para no perder el
contexto ni repetir la investigación de vPIC que ya se hizo hoy.
