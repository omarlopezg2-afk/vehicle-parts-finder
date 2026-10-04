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
| T-H1 | H. QA-Legal | Revisión de términos eBay + aviso de afiliados/privacidad | `docs/legal.md` | — | pendiente (aplazada a Fase 3) | Documento explícito: qué permite guardar eBay (datos/imágenes), aviso de afiliados visible redactado, política de privacidad borrador |
| T-A2 | A. Datos-Vehículos | Drill-down sin VIN: `get_all_makes()`, `get_models_for_make_year()` | `pipeline/fetch_vehicles.py` | T-A1 | **aprobada** (PR #9, merge 04/10) | Marcas/modelos reales de vPIC (filtro car+mpv), mismo patrón defensivo que `fetch_vehicle`, tests contra API real |
| T-E2 | E. Frontend | Integrar drill-down al frontend (wizard marca→año→modelo) | `site/js/vehiclePicker.js`, `site/js/vpicClient.js` | T-A2, CONTRACTS.md | **aprobada** (PR #10, merge 04/10) | Llega al mismo árbol de categorías que el flujo VIN; `vpicClient.js` aislado de `dataClient.js`; CORS verificado en vivo |

### Fase 2.5 — Mejoras de UX inspiradas en factorymitsubishiparts.com (04/10/2026)

Omar compartió un sitio de referencia (factorymitsubishiparts.com, construido sobre
RevolutionParts — **no es fuente de datos a integrar**, es solo inspiración de interfaz).
4 ideas aprobadas + 1 corrección de layout:

| ID | Agente | Tarea | Dueño de | Depende de | Estado | Criterios de aceptación |
|---|---|---|---|---|---|---|
| T-E3 | E. Frontend | **Layout: VIN y drill-down visibles a la vez** (no detrás de un botón) | `site/index.html`, `site/js/app.js`, `site/css/styles.css` | T-E1, T-E2 | pendiente | Ambos caminos (campo VIN/número + selector marca/año/modelo) visibles en la misma pantalla sin clic adicional; responsive (en móvil pueden apilarse, pero ninguno queda oculto tras un toggle) |
| T-E4 | E. Frontend | **"Mi vehículo" persistente** (localStorage) | `site/js/dataClient.js` o módulo nuevo `site/js/vehicleSession.js` | T-E1, T-E2 | pendiente | Una vez resuelto el vehículo (por VIN o drill-down), se recuerda en toda la sesión del navegador sin volver a pedirlo; opción visible de "cambiar vehículo" |
| T-E5 | E. Frontend | **Categorías destacadas en el home** | `site/index.html`, `site/js/app.js` | T-F1 (ya aprobada) | pendiente | Grid de categorías con los SVG existentes, visible sin necesidad de resolver vehículo primero |
| T-E6 | E. Frontend | **Tabla de fitment visible en la ficha de parte** | `site/js/partCard.js` | CONTRACTS.md | pendiente | Si `fitment_ids[]` tiene elementos, se muestra una tabla año/marca/modelo (resuelta vía `getVehicles()`), no solo el conteo |
| T-D2 | D. Pipeline-Build | Soporte de `other_names[]` en build + búsqueda | `pipeline/build_index.py`, `pipeline/validate.py`, `data/seed/` | CONTRACTS.md (campo agregado 04/10) | pendiente | `other_names` opcional en el esquema; `validate.py` no exige el campo pero lo valida si existe (debe ser array de strings); al menos 1 parte de `data/seed/` con sinónimos de ejemplo |

Nota de dependencia: T-E6 depende solo del campo `fitment_ids` que ya existe en el
contrato (no de T-D2); T-D2 es necesaria para que `other_names` llegue con datos reales a
`dataClient.js`, pero `searchPart()` puede implementarse ya contra el campo del contrato
aunque esté vacío en el build actual.

## Reglas
- Cada agente solo edita las carpetas de su columna "Dueño de".
- Si necesitas tocar algo fuera de tu carpeta, pide al líder.
- Entrega = Pull Request con descripción (qué hiciste / cómo probarlo / supuestos y
  problemas conocidos) + mover la fila de este tablero a "en revisión".
- El líder revisa con la checklist de PLAN.md y anota el resultado en REVIEW_LOG.md.
