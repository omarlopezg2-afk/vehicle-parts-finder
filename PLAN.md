# Buscador de piezas de vehículos (multimarca) — plan

> ## Cómo retomar este proyecto en una conversación nueva
>
> **Modelo:** el proyecto se construyó con **Claude Sonnet 5** (día a día) y **Opus 5**
> (decisiones de diseño); desde el 04/10/2026 se continúa con **DeepSeek v4** por costo.
> Nada del trabajo depende del modelo — lo que sí importa es leer este archivo y `TASKS.md`
> antes de tocar código, y mantenerlos actualizados.
>
> **Lo único que hay que leer:** este archivo, entero. Es autocontenido a propósito.
>
> **Estado (04/10/2026): MVP navegable y publicado en dominio propio.** Fases 0–3 con sus
> tareas aprobadas (detalle en `TASKS.md` y `REVIEW_LOG.md`). Sitio en vivo:
> **https://partexact.com** — dominio comprado el 04/10/2026 en Cloudflare Registrar y ya
> conectado a GitHub Pages (DNS + certificado). Pendientes abiertos en una línea: llaves de
> producción de eBay (la cuenta de Developer ya fue aprobada) para activar el modo real del
> pipeline, y los 3 huecos de drill-down del backlog al final de `TASKS.md`.
>
> Si algo del plan se cambia al arrancar, **actualizar este archivo**: es la memoria del
> proyecto.

## 0. Origen de este plan (25/09/2026)

Omar trajo un plan externo (`PLAN_buscador_partes.md`) con estructura de repo, contratos de
datos, equipo de agentes A-G y flujo de git. Decisión de Omar: **tomar de ahí la mecánica de
trabajo, pero el núcleo del producto sigue siendo el que ya habíamos cerrado el 24/09.** Lo
que se adoptó y lo que no:

**Se adopta:**
- Estructura de repo (`data/`, `pipeline/`, `site/`, `.github/workflows/`, `docs/`).
- `CONTRACTS.md` / `TASKS.md` / `REVIEW_LOG.md` y el protocolo de revisión del líder.
- Equipo de agentes A-H trabajando en paralelo por carpetas propias (ver sección más abajo).
- GitHub Pages + GitHub Actions para hosting del MVP (sustituye a Hetzner/Cloudflare de la
  tabla de costos original: sigue siendo gratis y es más simple al estar ya en GitHub).
- SVG genéricos por categoría como imagen de respaldo.

**Se adopta con cambios (porque contradecía lo ya decidido o lo investigado):**
- **El núcleo NO cambia**: sigue siendo VIN → vPIC → ensamblaje → **deep link a fuente EPC
  (7zap/Partsouq/tienda oficial) para leer el número de fábrica** → ese número se busca en
  eBay Browse API para confirmar con fotos reales → enlace de afiliado. El plan externo
  asumía que el usuario ya tiene el número de parte y no mencionaba el EPC en ningún lugar;
  eso se queda como *modo alterno* ("ya sé mi número, dame equivalencias y precio"), no como
  reemplazo del flujo principal.
- **Orden de EPN cambia**: el plan externo pedía registrar a Omar en eBay Partner Network en
  Fase 0, día 1. La investigación del 24/09 (`investigacion-ebay-24sep2026.md`) encontró que
  el motivo de rechazo más citado en la práctica es "sitio no funcional/vacío" — se mueve a
  **Fase 3, cuando ya hay un sitio mínimo navegable**. La cuenta de developer de eBay sí se
  saca ya, porque no depende de tener sitio.
- **Equivalencias (cross-reference)**: el CSV propio + datos derivados de eBay es el punto de
  partida del MVP, pero se documenta como lo que es — una aproximación, no una fuente
  autorizada. El cross-reference real vive en estándares de pago (ACES/PIES), que queda en
  fase 2 si el negocio lo justifica.
- **Scraping**: limitado a precio/equivalencias de sitios pequeños que lo permitan (robots.txt
  + términos). **Nunca** diagramas EPC (derechos de fábrica) ni eBay ni tiendas grandes — esto
  ya estaba en ambos planes, se mantiene explícito para que ningún agente lo cruce por error.
- **Git**: se usa GitHub directo con ramas + Pull Requests (la alternativa simple que el plan
  externo mismo ofrece), no Gitea en el servidor casero. Reduce una pieza de infraestructura
  sin cambiar el protocolo de revisión. Se puede migrar a Gitea después si hace falta.

## Qué es

Web para: poner tu coche (VIN, o marca/modelo/año/versión) → llegar al ensamblaje correcto
→ ver el diagrama de fábrica y el número de parte OEM → encontrar esa pieza a la venta
(eBay y tiendas de repuestos). **Multimarca**: cualquier marca, no solo una.

Caso de prueba: Mitsubishi Outlander Sport 2020 (es el coche de Omar, pero no es el alcance).

**Fuera de alcance del MVP:** carrito propio, pagos, cuentas de usuario, inventario propio,
scraping masivo.

## Decisiones tomadas (24/09 y 25/09/2026)

1. **Alcance: multimarca desde el diseño.** Núcleo agnóstico de la marca.
2. **Datos: empezar enlazando** a fuentes gratuitas (7zap, Partsouq, la tienda oficial de
   cada marca). No replicamos diagramas: cero costo y cero riesgo legal. Licenciar una
   fuente multimarca queda como fase 2 si el producto lo pide.
3. **Dinero: afiliados** (eBay y tiendas de repuestos). El usuario no paga nada.
4. **Repo con estructura fija + equipo de agentes por carpeta**, revisión centralizada por
   el líder antes de fusionar a `main`.
5. **Hosting MVP: GitHub Pages + GitHub Actions** (recolección programada de datos).

## La consecuencia técnica que hay que tener clara

Los diagramas y los números **viven dentro del catálogo de cada fuente**. Si solo enlazamos,
no podemos mostrar el número de fábrica en nuestra página, porque no es nuestro. Así que la
fase 1 es un **lanzador inteligente + puente a eBay**, no una copia del catálogo:

- Núcleo agnóstico: `vehículo → categorías → ensamblaje → (deep link a la fuente)`.
- **VIN como entrada**: vPIC (NHTSA) gratis y sin clave para vehículos de mercado
  americano; búsqueda por VIN o número de chasis en la propia fuente para el resto
  (en japoneses el número de chasis es imprescindible).
- Caja "pega el número que encontraste → buscar en eBay": filtros de precio, condición y
  ubicación, con enlace de afiliado. **Modo alterno**: si el usuario ya trae su propio
  número de parte (sin pasar por el EPC), entra directo aquí.

Fase 2 (si el producto lo pide): licenciar una fuente multimarca y mostrar diagramas y
números **dentro** de la página, ya con permiso.

## Arquitectura

- **Un esquema único** (`marca, modelo, generación, año, versión, ensamblaje, pieza, número`)
  y **un adaptador por fuente**. Añadir una marca o una fuente no debe tocar el núcleo.
- Fuentes candidatas y qué aporta cada una (verificar a fondo al construir):

| Fuente | Qué da |
|---|---|
| **7zap** | 60+ marcas, diagramas explotados, búsqueda por VIN. Outlander Sport cubierto (ASX/RVR 4ª facelift 2019–2024) |
| **Partsouq** | Búsqueda por VIN **o número de chasis**, diagramas (clave en japoneses) |
| **Tienda oficial de la marca** | Diagramas y números por año/versión, URLs estables por categoría → buenos deep links (ej. `parts.mitsubishicars.com/v-2020-mitsubishi-outlander-sport--sp--2-0l-l4-gas/engine--engine-parts`) |
| Amayama, MegaZip, catcar, epc-data | Alternativas y respaldo |
| VINsearch, partslink24 | Vía de pago: 52 catálogos con un acceso / oficial por marca (fase 2) |

- **Compra**: eBay **Browse API** (`/buy/browse/v1/item_summary/search`) — cuenta de
  desarrollador gratuita, token de aplicación por client credentials grant, funciona de
  inmediato contra producción sin pasos de afiliado (verificado 24/09, ver
  `investigacion-ebay-24sep2026.md`). Busca por palabra clave, por número de parte y con
  **filtro de compatibilidad por vehículo** (`compatibility_filter`). Límite por defecto:
  5,000 llamadas/día (se sube gratis pidiéndolo).
  Afiliados: eBay Partner Network — aplicar en **Fase 3**, con sitio mínimo ya navegable.
- **vPIC (NHTSA)**: `https://vpic.nhtsa.dot.gov/api/` — probado el 24/09: sin clave,
  devuelve marca, modelo, año, versión, tracción, cilindrada y carrocería desde el VIN.

## Estructura del repositorio

```
/
├── PLAN.md                  # memoria del proyecto (este documento, copia en el repo)
├── TASKS.md                 # tablero de tareas (lo mantiene el líder)
├── CONTRACTS.md             # contratos entre agentes (esquemas, nombres de archivos)
├── REVIEW_LOG.md            # registro de revisiones del líder
├── data/
│   ├── raw/                 # respuestas crudas de APIs (no se sirven al sitio)
│   ├── seed/                # CSV propios (equivalencias, partes de ejemplo)
│   └── build/               # JSON finales que consume el sitio (generados)
├── pipeline/                # scripts Python de recolección y construcción
│   ├── fetch_vehicles.py    # vPIC
│   ├── fetch_ebay.py        # eBay Browse API (modo mock + modo real)
│   ├── fetch_epc_links.py   # deep links por ensamblaje (7zap/Partsouq/tienda oficial)
│   ├── normalize.py         # limpieza y normalización de números de parte
│   ├── build_index.py       # genera data/build/*.json
│   ├── validate.py          # valida contra los esquemas
│   └── tests/
├── site/                    # frontend estático
│   ├── index.html, css/, js/
│   ├── assets/categories/   # SVG genéricos por categoría
│   └── tests/
├── .github/workflows/
│   ├── build-data.yml       # recolección programada (semanal)
│   ├── deploy-site.yml      # publica en GitHub Pages
│   └── ci.yml               # tests + validación en cada cambio
└── docs/                    # legal, fuentes, decisiones
```

## Contratos de datos (resumen — el detalle vivo está en `CONTRACTS.md` del repo)

**`data/build/parts.json`** — por parte, incluye:
`id, part_number, part_number_norm, type (OEM|AFTERMARKET), brand, name, category,
epc_link { source: 7zap|partsouq|oem-store|null, url: string|null }` ← **el campo que
preserva el núcleo original** (deep link a la fuente del diagrama/número de fábrica),
`image { url, source: ebay|generic, credit }, equivalents[], fitment_ids[], offers[]
{ store, url (link afiliado), price, currency, updated_at }, updated_at`.

**`data/build/vehicles.json`** — `{ id, make, model, year, trim|null, engine|null }`
(desde vPIC por VIN).

**`data/build/search_index.json`** — índice liviano para búsqueda en el navegador.
**`data/build/categories.json`** — `{ slug, name_es, svg }`.

**Regla de escalado**: el frontend lee datos solo vía `site/js/dataClient.js`
(`searchPart(q)`, `getPart(id)`, `getVehicles()`). Migrar a Supabase después (si el
catálogo pasa de ~100 mil partes) solo toca ese módulo.

## Equipo de agentes

### Líder (coordinador y revisor)
Congela contratos, crea el esqueleto, asigna tareas con criterios de aceptación medibles,
revisa cada entrega con la checklist (sección siguiente), anota el resultado en
`REVIEW_LOG.md`, resuelve conflictos, no escribe código de producción salvo para integrar.

### Agentes trabajadores (dueños de sus carpetas, nadie edita carpetas ajenas)

| Agente | Dueño de | Responsabilidad |
|---|---|---|
| **A. Datos-Vehículos** | `pipeline/fetch_vehicles.py`, `data/build/vehicles.json` | vPIC, catálogo marca/modelo/año/versión, tests |
| **B. Datos-Partes (eBay)** | `pipeline/fetch_ebay.py`, `pipeline/normalize.py` | OAuth client-credentials + Browse API, búsqueda por número, imagen/precio/condición, modo mock sin llaves |
| **C. EPC-Puente** *(nuevo, no estaba en el plan externo)* | `pipeline/fetch_epc_links.py` | Construir los deep links por ensamblaje hacia 7zap/Partsouq/tienda oficial — es el paso que el plan externo se saltaba |
| **D. Pipeline-Build** | `pipeline/build_index.py`, `pipeline/validate.py`, `data/seed/` | Unir fuentes, generar `data/build/*.json`, validar contra contratos |
| **E. Frontend** | `site/` (excepto `assets/categories/`) | Buscador, árbol vehículo→ensamblaje, ficha de parte con el enlace EPC y la caja "pega tu número", filtros, botón de compra, responsive |
| **F. Diseño-Assets** | `site/assets/categories/`, `categories.json` | ~12–15 SVG genéricos por categoría + imagen "sin foto" |
| **G. DevOps-CI** | `.github/workflows/`, `docs/` | Workflows de build programado, tests, deploy a Pages, secretos |
| **H. QA-Legal** | `docs/legal.md`, tests de aceptación | Términos de eBay, aviso de afiliados, privacidad, atribución de diagramas (solo enlace, nunca copia) |

A, B, C, F, G arrancan en paralelo (no dependen entre sí). D depende de contratos + salida/mocks
de A, B, C. E depende de contratos y trabaja primero con datos de ejemplo.

## Fases

**Fase 0 — Fundación (Líder + Omar).** Esqueleto del repo, `CONTRACTS.md`, `TASKS.md`,
`REVIEW_LOG.md`, 20-30 partes de ejemplo en `data/seed/`. Omar: cuenta eBay Developers
(gratis, ~1 día de aprobación, no depende de tener sitio) y guardar llaves como GitHub
Secrets. **EPN se aplaza a Fase 3.**

**Fase 1 — Construcción en paralelo (A, B, C, F, G).** Cada pieza funciona aislada y pasa
sus tests.

**Fase 2 — Integración (D, luego Líder).** Build que une vehículos + partes + EPC links +
equivalencias. Frontend conectado a los JSON reales. `build-data.yml` programado activo.

**Fase 3 — Afiliados, calidad y legal (H, Líder).** Con el sitio ya navegable: **aplicar a
eBay Partner Network** (orden invertido respecto al plan externo, por la evidencia del
24/09), revisión de términos, aviso de afiliados/privacidad, accesibilidad, prueba con
catálogo grande simulado (decide si hace falta Supabase).

**Monetización multi-tienda (decidido 03/10/2026, investigación con fuentes oficiales):**
ninguna cadena grande (AutoZone, O'Reilly Auto Parts, Advance Auto Parts, RockAuto) tiene
API pública de precio/stock — solo eBay la tiene. De las 4, **solo Advance Auto Parts** se
agrega a Fase 3: tiene programa de afiliados oficial confirmado y corre en **Impact.com**,
la misma plataforma que eBay EPN, así que es un "brand" más dentro de la misma cuenta
(aplicar primero al Marketplace de Impact, luego al programa específico de Advance). Es
solo un enlace de salida con comisión por venta (hasta 10%, cookie 30 días) — **no** permite
mostrar precio/stock propio en la ficha de producto, igual que eBay sin la API Browse.
Descartados: AutoZone (programa real pero en red distinta — Pepperjam/Ascend —, no vale el
costo de gestionar una segunda cuenta solo por un link sin precio); O'Reilly Auto Parts (no
tiene programa de afiliados de venta, solo un "Ambassador Program" de influencers sin
comisión — *no confundir con O'Reilly Media, la editorial de libros técnicos, que sí tiene
afiliados pero es una empresa totalmente distinta*); RockAuto (sin programa oficial
verificable — su propio newsletter dice explícitamente "We don't sell parts on any
marketplace or affiliate sites"; los sitios que lo listan como afiliado son agregadores de
cupones de terceros sin relación confirmada).

**Fase 4 — Lanzamiento y mejoras.** Dominio propio ✅ hecho (`partexact.com`, 04/10/2026,
en vivo), analítica respetuosa de privacidad. Backlog: más fuentes, proveedor de pago para
equivalencias (ACES/PIES), Supabase, búsqueda multi-idioma.

## Protocolo de coordinación y revisión

Tablero `TASKS.md`: ID, dueño, dependencias, criterios de aceptación, estado
(`pendiente → en curso → en revisión → aprobada / cambios pedidos`).

Reglas: cada agente solo edita sus carpetas; pide al líder si necesita tocar otra; entrega
con qué hizo / cómo probarlo / supuestos; ningún cambio de contrato sin aprobación del
líder; conflictos de archivo los resuelve y reasigna el líder; cada entrega se revisa antes
de que otro agente dependa de ella.

**Checklist de revisión**: cumple criterios de aceptación · datos validan contra el
esquema · tests pasan · sin llaves/secretos en el repo · respeta términos de las APIs y de
las fuentes EPC (solo enlace, nunca copia de diagramas) · maneja errores y límites de tasa ·
código legible y documentado · frontend funciona en móvil/teclado, textos en español ·
links de compra llevan parámetro de afiliado + aviso visible.

**Definición de "hecho" del MVP**: buscar por VIN+categoría o por número de parte directo
devuelve la pieza (o el deep link EPC si falta el número), equivalencias, imagen, al menos
un link de compra con tracking de afiliado. La recolección corre sola por GitHub Actions.
Hay SVG genéricos y aviso legal/afiliados visible. CI en verde, todas las tareas de Fases
1-3 aprobadas.

## Git y repositorio

GitHub directo (sin Gitea): rama `agent/<letra>-<tarea>` por agente, nadie commitea directo
a `main`, Pull Request con qué hizo/cómo probarlo/supuestos, **solo el líder fusiona**
después de la checklist, resultado anotado en `REVIEW_LOG.md`. Llaves de eBay: GitHub
Secrets (Actions) + `.env` local ignorado por git para pruebas. Nunca en el repo.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Términos de eBay limitan guardar datos o imágenes | Revisar antes de Fase 2 (agente H); si no se permiten, guardar solo números y links |
| Datos de compatibilidad incompletos | Mostrar "compatibilidad no verificada", no inventar |
| Cobertura de vPIC centrada en EE. UU. | Aclarar en el sitio; otras fuentes en backlog |
| Límites de tasa de las APIs | Caché en `data/raw/`, reintentos, ejecución programada |
| Catálogo crece y el sitio estático se vuelve lento | Fragmentar índice o migrar a Supabase (solo cambia `dataClient.js`) |
| Llaves expuestas | Solo GitHub Secrets; el líder revisa que no aparezcan en commits |
| Fuentes EPC bloquean o cambian URLs | Adaptadores aislados, más de una fuente por marca |
| EPN rechaza por sitio no funcional | Por eso se aplica en Fase 3, no en Fase 0 (evidencia del 24/09) |
| Aviso legal/afiliados faltante | Criterio de aceptación en Fase 3 |

## Recursos y costos (verificado 24/09, ajustado 25/09, nombre decidido 04/10)

| Partida | Costo |
|---|---|
| Desarrollar y probar | **0** |
| Hosting MVP (GitHub Pages + Actions) | **0** |
| Dominio propio: **partexact.com** (comprado 04/10/2026, Cloudflare Registrar) | **10,46 USD/año** con renovación automática — ya pagado |
| Cuenta de desarrollador de eBay | 0 |
| vPIC (NHTSA) | 0 |
| eBay Partner Network (Fase 3) | 0 |
| **Fase 2: licencia de datos EPC** | la partida cara — pedir precio si se llega ahí |

El techo de escalado llegaría por cuotas de llamadas de eBay (se suben pidiéndolo), no por
servidor ni GPU.

## Nombre y marca (decidido 04/10/2026)

**PartExact** — dominio `partexact.com` (verificado libre el 04/10/2026, pendiente de
comprar; también libres `.net`, `.io`, y los equivalentes en español `partexacto.com` /
`parteexacto.com` si se quiere asegurar una landing hispana más adelante).

Por qué: corto, fácil de decir y teclear sin errores, comunica el diferenciador real del
producto sin necesitar explicación — "exacto por tu VIN", frente a la compatibilidad
"probable" por año/modelo genérico que dan RockAuto/PartsGeek/AutoZone. Bonus notado por
Omar: la unión "Part" + "Exact" se lee naturalmente como "parte exacta" en español,
atractivo para el mercado hispanohablante sin tener que traducir el nombre.

Restricción verificada antes de proponer candidatos: ningún nombre puede usar "eBay" ni
sugerir asociación oficial con ninguna marca de auto (Mitsubishi, Toyota, etc.) — ambas
cosas violarían los términos de marca de eBay Partner Network y de los propios
fabricantes. El nombre elegido no toca ninguna de las dos.

**Dominio: comprado y funcionando (04/10/2026).** `partexact.com` y `www.partexact.com`
resuelven a GitHub Pages: 4 registros A en el ápice (185.199.108–111.153) + CNAME `www` →
`omarlopezg2-afk.github.io`, todos en modo *DNS only* (sin proxy de Cloudflare) para que
GitHub pueda emitir su propio certificado TLS. El sitio se sirve en `https://partexact.com`.
Registrador: Cloudflare Registrar (la misma cuenta que ya tenía `wifimonitor.app`), 10,46
USD/año con renovación automática. Orden de compra: `ea1d18dd-15b0-44cc-93f0-81c0ca732c22`.

**Correo del dominio: activo (04/10/2026).** Con Cloudflare Email Routing (gratis) —
`soporte@`, `hola@` y `support@partexact.com` reenvían a la dirección verificada de Omar;
no hay buzón propio. Además SPF, DKIM y DMARC (`p=none`, monitoreo) están publicados, así
que nadie puede falsificar la marca por correo. Esto es lo que se le da a una tienda o a
un programa de afiliados cuando piden contacto del proyecto, en vez de un Gmail suelto.

Pendiente: el logo (trabajo de diseño, no bloquea nada técnico) y renombrar el repo de
GitHub si se quiere que coincida (`vehicle-parts-finder` → `partexact`, opcional, no
urgente — cambiar el nombre del repo NO rompe el sitio porque GitHub Pages redirige el
`*.github.io` viejo, pero el CNAME de `www` sí habría que actualizarlo).

## Historial de documentos
- `investigacion-ebay-24sep2026.md` — verificación de cuenta developer, EPN y evidencia real.
- `PLAN_buscador_partes.md` (en Descargas) — plan externo que se fusionó aquí el 25/09.
