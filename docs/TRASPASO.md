# TRASPASO · PartExact — lo que necesita saber la siguiente IA

Escrito el **07/10/2026** al final de la sesión que cerró la cuarta capa del sitio (T-B25), el
combustible que faltaba (T-B24), los motores que faltaban a la flota (T-B26) y el número que estaba
descargado sin publicar (T-B27).

Este documento es **autosuficiente**: se puede trabajar con él sin haber visto la conversación donde se
hizo todo. Si algo de aquí contradice a otro documento, manda **este** y se corrige el otro (ya pasó con
el mercado: media docena de sitios decían que el catálogo era de EE.UU. y es de RD).

---

## 1. Qué es y dónde está

**El producto, en una frase:** que un dominicano cualquiera escriba su VIN (o elija marca/modelo/año) y
reciba **el número exacto de la pieza** de *su* coche, diciéndole **de qué mercado, de qué motor y de
qué combustible** es ese número — y solo si de verdad le queda.

| Pieza | Dónde |
|---|---|
| Repo (privado) | `~/Proyectos/piezas-vehiculos/repo` = `github.com/omarlopezg2-afk/vehicle-parts-finder` |
| Sitio en producción | **partexact.com** (GitHub Pages, dominio en Cloudflare) |
| Worker por demanda | **api.partexact.com** (`workers/autodoc-catalogo/`, Cloudflare Workers + KV) |
| Catálogo de origen | API **AUTODOC Parts Catalog (TecDoc) vía RapidAPI** |
| Ofertas de compra | eBay Browse API (hoy en modo mock: no hay cuenta de developer todavía) |
| Llaves | `.env` en la raíz (ignorado por git): `RAPIDAPI_KEY`, `EBAY_*`. Ver `.env.example` |
| Entorno | Python 3.14 (sin venv; `pip install -r requirements.txt` = pytest + requests) y Node 24 |
| Documentos | `AGENTS.md` (reglas), `PLAN.md` (historia), `CONTRACTS.md` (contratos de datos), `TASKS.md` (tablero), `docs/` (investigaciones y este traspaso) |
| Nota | En la máquina de Omar hay además una **skill de Hermes** (`partexact-vehicle-parts`) con el detalle procedimental acumulado. Si trabajas fuera de Hermes (Claude Code, Codex, otra IA), **este traspaso y `AGENTS.md` la sustituyen**; si necesitas algo que no esté aquí, pídesela al usuario. |

**Empujar a `main` publica.** Cada push a `main` dispara `ci.yml` (pruebas) y `deploy-site.yml` (copia
`data/build/*.json` **y** `data/build/catalogo/` a `site/data/build/` y publica en Pages). No hay
entorno de staging: `main` **es** producción.

---

## 2. Estado verificado (07/10/2026)

| Qué | Valor | Cómo se comprueba |
|---|---|---|
| Catálogo | **288 vehículos · 2.813 categorías con piezas** | `python3 -c "import json;d=json.load(open('data/build/catalogo/index.json'));print(len(d['vehiculos']), sum(len(v['categorias']) for v in d['vehiculos']))"` |
| Mercado del catálogo | **67 = República Dominicana** | `pais_filtro` del índice y del monolito; `"pais": 67` en `data/seed/catalogo/vehiculos.json` |
| Identidad de cada variante | **288/288 con combustible, cilindrada, potencia (PS) y código de motor** | `python3 pipeline/completar_variantes.py` (dice "ya estaban: 288", 0 consultas) |
| Duplicados peligrosos | 0 combustibles contradictorios por `vehicleId` (918 revisados) | el mismo script, línea "cache: … 0 con combustible contradictorio" |
| Pruebas | **212 pipeline + 118 sitio + 10 Worker, en verde** | los tres comandos de la sección 6 |
| Cuota RapidAPI | **~6.200 de 20.000** este mes | panel de RapidAPI (el campo `consultas` del monolito es el **acumulado del catálogo**, no el del mes: 13.693) |
| Tope del Worker | 2.000 consultas/mes propias (`TOPE_MES` en `wrangler.toml`) | `/salud` del Worker |
| Verificado en navegador | local (8765) **y** partexact.com | la tabla de la sección 5 |
| Pendiente de producto | el sitio **no está para un cliente**: falta elegir mercado, avisos legales y los números originales en pantalla | sección 4 |

---

## 3. Cómo está montado (mapa del sistema)

```
API TecDoc (RapidAPI)
   │  pipeline/fetch_autodoc.py         (GASTA cuota: resuelve fabricante→modelo→variante y baja
   │                                     categorías, artículos, especificaciones y números OEM)
   ▼
data/build/catalogo.json                 ← MONOLITO: todo, 400 MB, fuera de git, es el caché de trabajo
   │  pipeline/partir_catalogo.py        (0 consultas: reordena lo ya bajado)
   ▼
data/build/catalogo/index.json (~840 KB) + catalogo/<clave>/<slug>.json (~20 KB c/u)
   │  deploy-site.yml → site/data/build/
   ▼
site/ (estático)  ── site/js/dataClient.js es el ÚNICO que hace fetch a data/build/*
   │
   └── Worker api.partexact.com (workers/autodoc-catalogo): para lo que NO está precalculado,
       resuelve un coche por demanda con caché KV y tope mensual. El sitio AÚN NO lo llama (T-B21).
```

**Dónde tocar cada cosa:**

| Quiero… | Archivo |
|---|---|
| Añadir/rellenar datos del catálogo | `pipeline/completar_variantes.py` (identidad de variante) y `pipeline/agregar_variantes.py` (motores que faltan) |
| Cambiar qué se publica del monolito | `pipeline/partir_catalogo.py` (`articulos_utiles`, `vehiculo_completo`) |
| Cambiar cómo se llama un motor/mercado/combustible en pantalla | `site/js/catalogoMap.js` (`etiquetaDeVariante`, `traducirCombustible`, `nombreDeMercado`) |
| Cambiar lo que el sitio pide y muestra | `site/js/dataClient.js` (fetch) y `site/js/app.js` (pintado) |
| Añadir una ruta con estado en la URL | `site/js/router.js` (el estado vive en la URL, también la variante elegida) |
| Tocar la resolución por demanda | `workers/autodoc-catalogo/src/index.js` |

**Contrato que no se salta:** ningún archivo de `site/` hace `fetch` directo a `data/build/*.json`; todo
pasa por `site/js/dataClient.js` (ver `CONTRACTS.md`, "Regla de escalado").

---

## 4. LO QUE HAY QUE HACER (por orden, con coste y criterio de aceptación)

### 4.1 · El ORIGEN del carro (país de fabricación, chasis japonés, motor) — lo siguiente

**CORREGIDO el 07/10/2026 tras medirlo y hablarlo con el usuario.** La versión anterior de esta sección
planteaba un selector de mercado que se resolvía con `?pais=` del Worker. **Eso no funciona:** el
Corolla 2016 y el Honda N-BOX 2016 dieron **exactamente la misma variante** con `pais=67`, `127` y `261`
(18 consultas gastadas en la prueba). El filtro de país de TecDoc no separa mercados. Y el usuario aclaró
que **nunca se pretendió sacar el mercado de la API**: el país sale **del propio VIN**.

**Por qué importa (dicho por el usuario):** en RD entran muchos carros de **Corea** y de **Japón**. Los
japoneses de mercado interno traen la **guía a la derecha** y aquí se les hace el **cambio a la
izquierda**. vPIC (NHTSA) **no decodifica** chasis japoneses/coreanos.

**Qué sabemos y qué NO sabemos (no mezclar):**
| Dato | De dónde sale | Qué dice |
|---|---|---|
| País de **fabricación** | 2 primeros caracteres del VIN (`site/js/vinOrigen.js`, sin red) | Dónde se hizo. **No** el mercado de venta: un `JT…` puede ser guía izquierda |
| **Guía a la derecha** | **Solo** un chasis japonés de mercado interno (`NZE141-1234567`, `chasisJapones()`) | Es JDM: dirección a revisar con el taller. El VIN `J…` de 17 caracteres **no** lo dice |
| **Motor** | La pregunta "¿Cuál es tu carro exactamente?" (variante `vehicleId`) | Es lo que decide el número de parte |
| **Gas adaptado** | No hay dato en ningún lado | Ver abajo |

**Gas (regla del usuario, 07/10/2026):** un carro que sale de fábrica a gasolina y se le **adapta** gas
conserva su motor y **todo su sistema de gasolina**; el kit **agrega** inyección de gas, tanque,
medidores y una computadora. Por tanto **los números de la versión a gasolina siguen siendo los suyos y
NO se avisa nada en ninguna categoría** (la regla anterior, "el taller confirma las piezas de motor", era
excesiva y se retira). Si el modelo tiene **versión de gas de fábrica** en el catálogo (Kia Rio IV 1.25
LPG, Hyundai Elantra 1.6 LPI) y el visitante la elige, se da **esa** variante con su número. Los
repuestos del kit en sí no están en el catálogo y no se prometen.

**Hecho:** `site/js/vinOrigen.js` + `site/tests/vinOrigen.test.js` (9 pruebas), "Fabricado en" en la ficha
por VIN, mensaje para VIN que vPIC no decodifica y aviso de dirección para chasis japonés (en `app.js`).

**Worker, HECHO el 07/10/2026 (15 pruebas en verde; AÚN SIN DESPLEGAR: falta `npx wrangler deploy`, que
lo hace Omar con su login de Cloudflare):** ya no elige la primera variante (devuelve `variantes` y
`requiereMotor`; sin motor conocido no pide ni da piezas), acepta `&vehicleId=` para la variante que
elige el visitante, arregló el `paisAlterno` y dice en `filtroPais` con qué filtro se resolvió. El sitio
todavía no lo llama (T-B21), así que nada de esto cambia producción hasta entonces.

**Falta:**
1. ~~Arreglar el Worker~~ (hecho, ver arriba). Lo que se corrigió:
   - `construir()` usa `paisAlterno` sin recibirlo: si el modelo no existe en el mercado pedido lanza un
     error de variable no definida en vez de probar el otro mercado.
   - Devuelve **una sola** variante (`elegirVariante`) y, sin motor, elige la primera (el 1.3 del
     Corolla, no el 1.8 que se ve en RD): debe devolver **la lista** y dejar que el sitio pregunte.
   - Quitar `?pais=` como si filtrara, o decir en la respuesta qué mercado se usó realmente.
2. **T-B21 — el sitio llama al Worker: HECHO el 07/10/2026 pero APAGADO** (`WORKER.activo = false` en
   `site/js/dataClient.js`). Qué hay: el Worker cachea la lista de motores en KV (clave `var:`), así
   que un modelo-año o VIN se paga **una vez** (~3-4 consultas) y elegir motor cuesta 0;
   `consultarWorker()` es el único cliente; `app.js` (`intentarConWorker`) lo usa **solo** cuando el carro
   no está en el catálogo, pregunta "¿Cuál es tu carro exactamente?" y, elegido el motor, muestra el
   carro con motor y combustible. **Por qué apagado:** todavía NO hay piezas por demanda. Encenderlo hoy
   gastaría cupo en identificar carros sin dar ningún número (regla 5: prometer solo lo que se cumple).
   **Lo que falta para encenderlo (siguiente trabajo):**
   - Piezas por demanda en el Worker: el árbol de categorías por vehículo
     (`/api/category/type-id/1/products-groups-variant-1/{vehicleId}/lang-id/4`, 1 consulta) para sacar
     el `categoryId` del término buscado (`FRAGMENTOS_POR_SLUG`), luego artículos + detalle (hasta ~4).
     Orden de magnitud: **~6-10 consultas por (carro, categoría)**; con el tope de 2.000/mes son
     ~200-300 búsquedas nuevas al mes. Eso es una decisión de cupo del usuario.
   - La variante elegida en el Worker aún no vive en la URL (`router.js`): recargar pierde el motor.
   - La UI de `intentarConWorker` no tiene prueba automática (los tests del sitio son de funciones
     puras): verificar en navegador con `_setWorkerParaTests` o poniendo `activo: true` en local.
3. Verificar en navegador con un VIN japonés, uno coreano y un chasis `NZE141-…` (sección 5).

**Aceptación:** un VIN `KMH…` muestra "Fabricado en Corea del Sur" y pregunta el motor; un chasis
`NZE141-…` explica que es JDM y avisa solo de la dirección; ningún carro "con gas" cambia números.

### 4.2 · Pintar los NÚMEROS ORIGINALES del vehículo (es el número que el cliente pide en la tienda)

Hoy `originales.json` (100-190 números del fabricante **por coche**) viaja al sitio y **ninguna pantalla
lo lee**: `getOriginalesDelVehiculo()` existe en `site/js/dataClient.js:266` y **nadie lo llama**.

- Forma del archivo: `{originales: [{buscado: "brake pad", numeros: [{numero, pieza, equivalentes: []}]}, …]}`.
- El `buscado` de cada bloque usa los **mismos términos** que el sitio ya usa para emparejar categorías
  (`FRAGMENTOS_POR_SLUG` en `catalogoMap.js`: "brake pad", "oil filter", "spark plug").
- Dónde pintarlos: en el bloque de la categoría, ya con el motor elegido, como "Números originales de
  TOYOTA para este motor". Es pesado (hasta ~1,9 MB por coche): **se baja solo al abrir esa categoría**,
  nunca en la portada.
- **Por qué el motor importa aquí:** un número original del motor equivocado es exactamente el fallo que
  se quiere evitar; por eso este bloque va **después** de elegir variante, nunca antes.

**Aceptación:** en `…/2016/pastillas-freno/v109621` (Corolla 1.8) se ven los originales de Toyota de
ese motor (`04465-02570`, `04465-06150`…) y no los del 1.3 ni los del diésel.

### 4.3 · Ronda 2 de motores (el criterio actual es bueno pero no perfecto)

El 07/10/2026 se añadieron **43 variantes** con el criterio acordado con el usuario (***la gasolina de
más potencia de cada modelo-año***), porque la flota se había armado cogiendo *los dos primeros motores
que devolvía la API, sin criterio* y **79 modelo-año no tenían el motor que se ve en RD** (el Corolla
2016/2017 sin el 1.8, el Hilux/Fortuner con solo diésel y sin el 4.0 V6, el Accent sin el 1.6 GDI).

Lo que queda mal y hay que afinar: en **tres modelos** esa "gasolina de más potencia" es una serie de
escaparate que en RD casi no se ve (`Lancer EVO X` 402 PS, `Grand Cherokee 6.2` 717 PS, `Yaris GR 4WD`
272 PS), y ahí **el motor común puede seguir faltando**. El criterio tiene que salir de **lo que entró
de verdad al parque** (registro de la DGII; hay investigación en `docs/`), no de los caballos.

- Herramienta: `python3 pipeline/agregar_variantes.py --listar` (plan y coste, **0 consultas**). El
  criterio vive en `candidatos(..., criterio=...)` y hoy solo acepta `"alta"`: hay que añadir el nuevo.
- Coste de cada variante nueva: **~48 consultas** (guía: 1.635 para 43, ya con la caché de
  especificaciones puesta). **No se gasta sin decirlo y sin el OK del usuario.**

### 4.4 · Verificar SIEMPRE en navegador (y contra partexact.com tras el deploy)

Ver la sección 5. Un cambio de datos o de pintado **no está terminado** hasta que se ve en el navegador
con un coche real, en local y en producción.

### 4.5 · Mantenimiento

- Cuando entren vehículos nuevos al catálogo: `python3 pipeline/completar_variantes.py` para que no
  nazcan **sin combustible** (con la caché puesta cuesta 0 consultas).
- `build-data.yml` corre los **lunes 06:00 UTC** y regenera `data/build/*.json` (eBay, hoy en mock). **No
  gasta RapidAPI** porque el secret `RAPIDAPI_KEY` no está en GitHub Actions: si alguien lo añade como
  secret, ese job empezaría a re-descargar el catálogo y a gastar cuota. Ojo con eso.
- Si el push es rechazado porque el CI commiteó datos a `main`, resolver con
  `git merge origin/main -X ours` (los datos del workflow no deben pisar el trabajo local).

---

## 5. Cómo se verifica que un número le queda (la verificación del producto)

```bash
# 1) partido + copia local + servidor (el workflow hace esta copia en CI; en local, a mano)
cd ~/Proyectos/piezas-vehiculos/repo
cp -r data/build/catalogo/. site/data/build/catalogo/
(cd site && python3 -m http.server 8765)     # servidor de vista previa en el puerto 8765

# 2) Chrome headless. CLAVE: --user-data-dir propio por corrida; sin él la SEGUNDA corrida sale con el
#    DOM vacío (sin ningún error) y se puede creer que el código está roto.
google-chrome --headless=new --disable-gpu --no-sandbox --user-data-dir=/tmp/pv/x \
  --virtual-time-budget=14000 --dump-dom "http://localhost:8765/#/vehiculo/Toyota/Corolla/2016/pastillas-freno"
```

| Caso | URL | Qué tiene que salir |
|---|---|---|
| Sin motor elegido | `#/vehiculo/Toyota/Corolla/2016/pastillas-freno` | La pregunta **"¿Cuál es tu carro exactamente?"** con los 3 motores y **cero** `class="numero-ficha"` |
| El 1.8 | `…/pastillas-freno/v109621` | `Mercado: República Dominicana · Motor: 1.8 L · 151 PS · Gasolina · 2ZR-FE · Combustible: Gasolina` + 3 pastillas (`13.0465-5690.2`, `DB1786 HD/UP`) |
| El 1.3 | `…/pastillas-freno/v52438` | `Motor: 1.3 L · 99 PS · Gasolina · 1NR-FE` y **números distintos** de los del 1.8 |
| Una sola variante | `#/vehiculo/Mitsubishi/Outlander%20Sport/2020/pastillas-freno` | Sin pregunta y sin botón "No es mi motor"; rótulo `2.0 L · 148 HP · Gasolina · MIVEC` |

Contar con expresiones regulares sobre el DOM (`class="numero"`, `class="numero-ficha"`,
`class="variante-opcion"`, `class="pregunta-variante"`) es lo más rápido y lo que se usó en esta sesión.
Para ver el aspecto real, `--screenshot=/tmp/x.png --window-size=1100,860` y mirar la imagen.

---

## 6. Comandos (pruebas, datos, sitio, Worker)

```bash
cd ~/Proyectos/piezas-vehiculos/repo

# pruebas: las tres suites. Hoy 212 + 138 + 21 en verde.
python3 -m pytest pipeline/tests/ -q
(cd site && node --test tests/*.test.js)
(cd workers/autodoc-catalogo && npm test)

# datos (GASTAN cuota salvo lo marcado): primero en seco SIEMPRE
python3 pipeline/completar_variantes.py --dry-run          # 0 consultas: qué identidad falta y qué costaría
python3 pipeline/completar_variantes.py                    # ~1 por pareja marca+modelo (caché: 0)
python3 pipeline/agregar_variantes.py --listar             # 0 consultas: el plan de motores y su coste
python3 pipeline/agregar_variantes.py --ejecutar --lote 8  # por tandas: cada tanda escribe el catálogo
python3 pipeline/partir_catalogo.py                        # 0 consultas
python3 pipeline/validate.py                               # 0 consultas: valida contra CONTRACTS.md

# descarga completa del catálogo (MUY caro: fue 12.058 consultas; solo con OK explícito)
set -a && . ./.env && set +a
python3 pipeline/fetch_autodoc.py --max-consultas 18000

# Worker
cd workers/autodoc-catalogo && npx wrangler deploy
```

---

## 7. Trampas que ya costaron tiempo (síntoma → causa → arreglo)

1. **El sitio decía "no tenemos piezas" aunque el número estuviera guardado.** El pipeline detallaba los
   N primeros artículos de cada categoría y a veces no son el producto de la categoría (pedida por
   "brake pad", los 3 detallados eran discos). Medido: **307 vehículo-categoría**. Arreglado publicando
   además **hasta 3 de los que coinciden con el término buscado** (`partir_catalogo.articulos_utiles`),
   con tope: sin él, un filtro publicaba 64 marcas y volvía el "volcado de marcas" que el usuario
   rechazó. Quedan 191 casos limpios (la API devolvió piezas que no se llaman como el término pedido).
2. **El combustible no estaba guardado en 248 de 250 variantes.** `expandir_flota` recibía `fuelType` en
   la respuesta que **ya pagaba** (para filtrar por año) y no lo guardaba; y **no se puede derivar del
   nombre del motor** (219 de 250 nombres no traen señal). Arreglado en el pipeline + recuperado con
   `completar_variantes.py` (49 consultas, con caché).
3. **Media docena de documentos decían que el catálogo era de EE.UU. (261).** Es de **RD (67)**
   (`pais_filtro`). Un número etiquetado con el mercado equivocado es una mentira en cada página. Antes
   de etiquetar, **leer el artefacto**.
4. **249 de los 250 vehículos eran inalcanzables desde la página.** El flujo resolvía el vehículo solo
   contra `data/build/vehicles.json` (1 vehículo). Arreglado: `matchVehicleByMakeModelYear()` y
   `matchVehicleByVIN()` buscan también en el índice (`id: null`, sin ofertas de eBay, pero con el
   número). **Si una capa nueva "no se ve", comprobar primero si el flujo llega hasta ella.**
5. **`fetch_autodoc.fusionar` fusiona por VIN *o* ETIQUETA**, y la etiqueta manda sobre el `vehicleId`:
   al añadir una variante cuyo nombre coincide con una entrada existente, **la vieja se sustituye**. Con
   las 43 nuevas pasó 5 veces; se comprobó que las nuevas traían más piezas (308 vs 42, 142 vs 41) y no
   se perdió nada, pero hay que mirarlo antes de dar por hecho que una operación "solo suma".
6. **`vehiculosEnCatalogo` devolvía la primera variante** y el sitio pintaba números de un motor sin
   decir cuál (123 de 127 modelo-año tienen más de uno). Ahora `entradaDeVariante()` no elige por ti:
   con varias variantes y sin clave devuelve `null` y **el sitio pregunta**.
7. **`traducirCombustible()` no conocía "Gasoline"** (la palabra del VIN/NHTSA): mostraba inglés al
   cliente. La tabla acordada es: Petrol/Gasoline → Gasolina · Petrol+LPG → "Gasolina / Gas (GLP)" ·
   Diesel → Diésel · Petrol/Ethanol → "Gasolina / Etanol" · Petrol/Electric → Híbrido. **Nunca "gas" a
   secas.**
8. **PS ≠ HP.** TecDoc da la potencia en PS y la NHTSA en HP (un PS ≈ 0,986 HP). El catálogo guarda
   `potencia_ps` y la ficha del VIN `potencia_hp`; cada una se pinta con su unidad. La cilindrada,
   siempre con decimal ("2.0 L", no "2 L").
9. **Chrome headless: sin `--user-data-dir` propio, la segunda corrida sale vacía** (y sin error). Ver
   sección 5.
10. **`cp data/build/*.json` NO copia subcarpetas.** Si se añade un artefacto nuevo, hay que copiarlo
    explícitamente en `deploy-site.yml`; si no, el sitio carga pero **sin datos** (fallo silencioso). El
    catálogo partido ya se copia.
11. **El monolito (`data/build/catalogo.json`, ~400 MB) no va a git** (`.gitignore`). El respaldo
    `data/build/*.respaldo` tampoco. Y **nunca** borrar el monolito como "limpieza": recuperarlo cuesta
    la cuota entera.
12. **El catálogo no tiene fixture, a propósito** (`dataClient.js`): si falta el archivo real, devuelve
    vacío. Un catálogo de mentira enseñaría números inventados a un cliente. Vale para todo
    identificador que el visitante vaya a usar para comprar: **jamás se simula.**
13. **La clave de RapidAPI nunca se imprime** (ni en logs, ni en un mensaje de commit, ni en una URL). El
    doble de `fetch` de las pruebas del Worker falla si aparece, a propósito.
14. **El estado vive en la URL.** La variante elegida se escribe (`…/<slug>/<variante>`) para que
    recargar o compartir un enlace no pierda de qué motor es el número. Si se añade estado nuevo, se
    añade a `router.js` (con prueba de ida y vuelta).
15. **Los tests del sitio son de funciones puras** (Node, sin DOM): lo visual se verifica en navegador,
    y eso no es opcional.

---

## 8. Qué NO hacer

- **No inventar ni rellenar**: ningún número, marca, mercado, combustible ni "probablemente sirve". Sin
  dato, no se muestra.
- **No gastar cuota sin decirlo y sin OK.** Primero `--dry-run` / `--listar`, luego el coste dicho en
  voz alta, luego se ejecuta.
- **No re-descargar lo que ya está**: la caché (`data/raw/autodoc_variantes/`, `data/raw/vpic_cache/`) y
  el monolito existen para no volver a pagar. Los `articleId` de TecDoc no cambian nunca.
- **No tocar `data/build/catalogo.json` a mano** ni borrarlo: es el caché maestro (y está fuera de git:
  si se pierde, se paga otra vez).
- **No cambiar un texto de promesa** (landing, ficha, sitio, vídeo) para que diga algo que el producto
  aún no cumple: si no se cumple, se quita de la promesa y queda como pendiente.
- **No prometer el selector de mercado hasta que exista** (hoy el sitio solo *dice* el mercado).
- **No publicar el sitio como listo para un cliente** mientras falten el mercado elegible, los
  originales en pantalla y el aviso legal.

---

## 9. Presupuesto: cómo no gastar de más

- **RapidAPI: 20.000 consultas/mes.** Van ~13.750 → quedan **~6.200**. El número exacto, en el panel.
- El catálogo acumula `consultas` en el monolito (13.693) — **es el total histórico, no el del mes**.
- **Caché que baja el coste a 0**: `data/raw/autodoc_variantes/` (listas de variantes por modelo),
  `data/raw/vpic_cache/` (VIN de NHTSA) y el propio monolito (caché de especificaciones por `articleId`).
- **Lo caro, por unidad:** un vehículo completo ~48 consultas (categorías + especificaciones + OEM);
  rellenar la identidad de una variante = 1 consulta por pareja fabricante+modelo; partir el catálogo y
  validar = 0.
- **`--lote N`** en `agregar_variantes.py`: cada tanda escribe el catálogo, así que una corrida cortada
  no pierde lo ya bajado.
- **El Worker tiene su propio tope** (`TOPE_MES = 2000`) y responde `/salud` sin gastar nada.

---

## 10. Primeros 60 minutos recomendados

1. `cat AGENTS.md docs/TRASPASO.md` y `TASKS.md` (T-B22 → T-B27). *(Lo que estás leyendo.)*
2. `git log --oneline -8` y `git status` para ver dónde quedó el árbol.
3. Las tres suites de pruebas (sección 6): 212 + 138 + 21 en verde antes de tocar nada.
4. `python3 pipeline/completar_variantes.py` (0 consultas) → tiene que decir "ya estaban: 288" y
   "0 con combustible contradictorio".
5. Vista previa + los cuatro casos de la tabla de la sección 5 en el navegador. Si el caso "sin motor
   elegido" pinta números, algo se rompió en T-B22.
6. `curl -s https://partexact.com/data/build/catalogo/index.json | head -c 300` para ver el índice
   desplegado (288 vehículos, `pais_filtro: 67`).
7. Preguntarle al usuario qué quiere priorizar: **(a)** el mercado/Worker (4.1), **(b)** los originales
   en pantalla (4.2) o **(c)** la ronda 2 de motores (4.3). Los tres están listos para empezar; (a) y
   (b) no gastan cuota para desarrollarse y (c) sí.

---

## 11. Glosario mínimo (para no perderse en el código)

| Término | Qué es |
|---|---|
| **Monolito** | `data/build/catalogo.json`: todo lo descargado de la API, ~400 MB, fuera de git |
| **Catálogo partido** | `data/build/catalogo/index.json` + un archivo por vehículo-categoría (lo que sirve el sitio) |
| **Variante / `vehicleId`** | El coche concreto con su motor (la unidad del catálogo, no el "modelo-año") |
| **`clave`** | El nombre de carpeta del vehículo: `v<vehicleId>` (estable, es lo que lleva la URL) |
| **`buscado`** | El término con el que se pidió una categoría ("brake pad", "oil filter"): la señal fiable para emparejar con los slugs del sitio |
| **`pais_filtro` / mercado** | El filtro de país con el que se resolvieron los `vehicleId` (67 = RD) |
| **Original / OEM** | El número del fabricante del coche (Toyota, Hyundai…): el que el cliente pide en la tienda |
| **Equivalentes** | Los números de otras marcas que sirven para la misma pieza |
| **`slug`** | La categoría tal como la llama el sitio ("pastillas-freno", "filtro-aceite") |
| **T-Bxx** | Identificador de tarea en `TASKS.md` (el tablero del proyecto) |
| **Worker** | `workers/autodoc-catalogo`: resuelve por demanda contra la API, con caché KV y tope mensual |
| **vPIC** | Base pública de la NHTSA (EE.UU.) para decodificar VIN. **No decodifica chasis japonés ni coreano** |
