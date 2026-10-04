# T-C3 — Investigación: ¿existe el nivel Trim/Submodelo en alguna fuente gratuita?

**Fecha de las pruebas:** 04/10/2026. **Caso de prueba:** Mitsubishi Outlander Sport 2020,
mercado USA, trims de marketing conocidos BE / ES / SE / SP / GT (plataforma/chasis **GA2W**).
VIN real de Omar: `JA4AP4AU3LU023739`.

> Regla del proyecto respetada en este documento: de 7zap y Partsouq **solo se registra qué
> endpoint/URL se consultó y qué TIPO de dato devolvió**. No se incluyen capturas, diagramas ni
> transcripciones de contenido propietario de esos catálogos.

## Resumen ejecutivo

**No existe hoy una fuente gratuita y fiable que devuelva el trim de marketing (BE/ES/SE/SP/GT)
de un Outlander Sport 2020**, ni por combinación marca+modelo+año, ni para la mayoría de VIN
reales probados, ni navegando los catálogos EPC públicos. La única señal parcial viene de vPIC
decodificando un VIN concreto (campo `Trim`), pero en el 100% de los VIN reales de este modelo
probados (10 de 10) ese campo llegó **vacío**. Recomendación: **dejarlo fuera del MVP** (ver
sección final).

## a) vPIC sin VIN — ¿lista trims por marca+modelo+año?

Probado en vivo contra `https://vpic.nhtsa.dot.gov/api/vehicles/...`:

| Endpoint probado | URL exacta | Qué devolvió |
|---|---|---|
| `GetModelsForMakeYear` | `.../GetModelsForMakeYear/make/mitsubishi/modelyear/2020?format=json` | Lista de **modelos** (Outlander, Outlander Sport, RVR, Mirage...). Ningún campo de trim/submodelo. |
| `GetModelsForMakeIdYear` (con `vehicletype`) | `.../GetModelsForMakeIdYear/makeId/481/modelyear/2020/vehicletype/car?format=json` | Igual: solo `Make_ID`/`Model_ID`/`Model_Name`/`VehicleTypeId`. Sin trim. |
| `GetVehicleVariableList` | `.../GetVehicleVariableList?format=json` | Catálogo completo de variables vPIC. Confirma que existen variables `Trim` (id 38), `Trim2` (id 109), `Series` (id 34), `Series2` (id 110) — pero son **campos de salida de la decodificación de un VIN**, no parámetros de un endpoint de listado. |
| `GetVehicleVariableValuesList/trim` (o `/38`) | `.../GetVehicleVariableValuesList/trim?format=json` | `Count:0` — vPIC no mantiene un diccionario cerrado de valores de Trim (a diferencia de variables categóricas como `Body Class`); el campo es texto libre que depende de lo que el fabricante haya reportado para ESE VIN. |

**Conclusión (a):** confirma lo ya investigado — vPIC **no tiene ningún endpoint** para listar
trims/submodelos a partir de marca+modelo+año. No hay camino público no probado antes: se
revisaron variables, variable-values-list y las dos variantes de "modelos por marca+año", y
ninguna expone trim sin un VIN.

## b) vPIC con VIN — proporción de VIN reales con `Trim` poblado

Se buscaron VIN reales de Outlander Sport 2020 en listados públicos de venta (Cars.com) y se
decodificaron con `DecodeVinValues/<VIN>?format=json`.

VIN probados (10, todos Outlander Sport 2020 confirmado por `ModelYear`+`Model` en la propia
respuesta de vPIC):

`JA4AP4AU3LU023739` (VIN real de Omar), `JA4AP3AU4LU017796`, `JA4AP3AU3LU005624`,
`JA4AP4AU7LU000965`, `JA4AP3AU5LU004006`, `JA4AP4AU0LU024413`, `JA4AR3AUXLU010300`,
`JA4AP4AUXLU028355`, `JA4AR3AU9LU023393`.

(9 listados en el cuerpo de la prueba + el VIN de Omar hacen el conteo; el lote de verificación
ejecutado en vivo fue de 9 VIN de terceros + el VIN de Omar = 10 en total.)

**Resultado: 0 de 10** tuvieron el campo `Trim` poblado (`Trim: ''` en los 10 casos). `Trim2` y
`Series` también vacíos en todos. Esto es consistente con, y **refuerza con más muestra**, el
hallazgo previo de que con el VIN de Omar vino vacío: aquí se ve que **no es un caso aislado de
su VIN**, sino el comportamiento general de vPIC para este modelo/año — Mitsubishi
(fabricante) simplemente no reporta el trim de marketing en el campo que vPIC expone para
Outlander Sport. (El hallazgo anterior de que "con otro VIN de prueba sí trajo valor" se
reprodujo también aquí: un VIN de ejemplo de BMW en la documentación de NHTSA (patrón
`5UXWX7C5*BA`, 2011 X3) sí devuelve `Trim: xDrive35i` — confirma que el campo **existe y
funciona para otros fabricantes/modelos**, pero Mitsubishi Outlander Sport no lo rellena.)

**Proporción final: 0/10 VIN reales de Outlander Sport 2020 con `Trim` poblado en vPIC.**

## c) 7zap — ¿la navegación pública por generación llega a nivel de trim?

Acceso: **sí fue posible** (HTTP 200, sin bloqueo Cloudflare detectado desde este entorno) via
`curl` normal y `web_extract`. Esto se distingue explícitamente de un "no lo pude comprobar".

| URL exacta consultada | Qué TIPO de dato devolvió |
|---|---|
| `https://7zap.com/en/catalog/cars/mitsubishi/` | Índice de generaciones de modelos Mitsubishi (nombre de generación + rango de años). Para Outlander Sport aparecen generaciones por **año/facelift** (ej. "1st Facelift 2013-2016"), nunca por trim comercial. |
| `https://7zap.com/en/catalog/cars/mitsubishi/asx-outlander-sport-rvr-4th-facelift-parts-catalog/` (generación 2019–2024, la que cubre el 2020) | Página de **categorías de sistema** (Motor, Transmisión/Tracción, Chasis, Carrocería, Interior, Eléctrico, Accesorios, Mantenimiento) — es decir, la navegación de 7zap discrimina por **sistema de la pieza**, no por trim. El bloque "Cambiar parámetros" pide parámetros de vehículo (motor/transmisión/mercado), no un selector de trim de marketing. |
| `https://7zap.com/en/vin-decoder/mitsubishi/` | Página de marketing/documentación del decodificador de VIN (no un endpoint de datos): describe que un VIN decodificado puede devolver "manufacturer and vehicle attributes" variables por mercado, pero el propio texto advierte "field availability varies by market, model year, source data, and catalog coverage" y que las imágenes de ejemplo del flujo son de OTRA marca ("temporary images... copied from another brand page... do not show or prove data for a Mitsubishi vehicle"). No expone trims BE/ES/SE/SP/GT en ningún lugar del HTML. |
| Script embebido en esa misma página | Referencia interna a `https://vpic.nhtsa.dot.gov/api/vehicles/GetWMIsForManufacturer/Mitsubishi...` — confirma que **7zap también se apoya en vPIC** para parte de su propio decodificador, el mismo origen de datos ya evaluado en (a)/(b), sin agregar un dato de trim propio. |

**Conclusión (c): confirmado que el límite ya reportado SIGUE vigente.** La navegación pública
de 7zap llega a nivel de **generación/plataforma** (equivalente a lo que vPIC llama
`Model`+rango de años), nunca a nivel de trim de marketing. No se encontró parámetro de URL
alternativo (probado `?region=...&series=...`, redirige con 301 a la versión canónica sin
exponer un selector de trim) ni un endpoint de VIN que devuelva BE/ES/SE/SP/GT. El propio
decodificador de VIN de 7zap no promete ese dato y, de hecho, usa vPIC como una de sus fuentes.

## d) Partsouq — con el enlace por VIN que genera el proyecto

URL exacta usada (la misma que construye el proyecto): `https://partsouq.com/en/search/all?q=JA4AP4AU3LU023739`

- **Acceso directo por `curl`/automatización simple: bloqueado.** Respuesta `HTTP 403` con
  cabecera `cf-mitigated: challenge` y `server: cloudflare` — es un reto de Cloudflare, no un
  403 de la aplicación. Esto se distingue explícitamente: **"no lo pude comprobar" por bloqueo
  del WAF**, no evidencia de que el dato no exista.
- **Vía herramienta de extracción de contenido (bypassa el reto de Cloudflare en este caso):**
  sí se obtuvo contenido real. Qué TIPO de dato devolvió:
  - La página de búsqueda por VIN (`/en/search/all?q=<VIN>`) devuelve una **tabla de 3
    coincidencias de catálogo** (Brand/Model/Model Code/Details), cada una con un enlace
    `partcatalog/groups/?...&carId=...`. Las 3 coincidencias para el VIN de Omar son variantes
    de catalogación del mismo chasis/plataforma: `ASX(G.EXP):EXC 16 MODEL YEAR`,
    `OUTLANDER SPORT(P&G)`, `OUTLANDER SPORT(MMNA)` — todas con **Type: GA2W** y la misma
    clasificación `XTXHL2M`. Es decir, Partsouq distingue variantes de **mercado/catalogación
    interna** (P&G vs. MMNA = distintas entidades de distribución de Mitsubishi), no trims de
    marketing.
  - Al entrar al enlace de detalle (`partcatalog/groups/?catalogId=mitsubishi&carId=...&q=<VIN>&criteria=...`)
    el TIPO de dato devuelto es un **índice de grupos de diagramas por sistema** (Motor,
    Transmisión, Chasis, etc. — igual que 7zap), con el VIN confirmado en cabecera
    ("Year: 2020, Model: Airtrek / Outlander, Model code: GA2W"). Ningún grupo ni cabecera
    menciona BE/ES/SE/SP/GT.

**Conclusión (d): se reconfirma con evidencia fresca que Partsouq resuelve por plataforma
compartida (chasis GA2W) y lista variantes de mercado, no trims de marketing**, exactamente
como ya se había determinado antes. No se encontró un parámetro de URL alternativo, un filtro
oculto, ni un camino de "buscador por VIN del catálogo" que devuelva el trim — el propio
buscador por VIN es el camino que ya se probó y el que confirma el límite.

## Síntesis de los 4 caminos

| Fuente | ¿Accesible hoy? | ¿Expone trim marketing (BE/ES/SE/SP/GT)? |
|---|---|---|
| vPIC sin VIN | Sí | No — no existe ningún endpoint para ello |
| vPIC con VIN | Sí | No en la práctica — 0/10 VIN reales de este modelo con `Trim` poblado |
| 7zap navegación por generación | Sí (sin bloqueo detectado) | No — llega a generación/sistema, no a trim |
| Partsouq por VIN | Parcial (bloqueado por Cloudflare vía `curl` directo; accesible vía extracción) | No — resuelve por plataforma/chasis (GA2W) y variantes de mercado, no trim |

## Recomendación

**DEJARLO FUERA DEL MVP.**

**Motivo (una frase):** ninguna de las cuatro fuentes gratuitas probadas en vivo —ni vPIC sin
VIN, ni vPIC con VIN real (0/10), ni la navegación pública de 7zap, ni Partsouq por VIN—
devuelve el trim de marketing BE/ES/SE/SP/GT para el Outlander Sport 2020, así que prometer ese
nivel en el asistente sería mostrar un dato que PartExact no puede respaldar con una fuente
verificable, violando la premisa de "solo promete lo que cumple".

**Coste estimado si se implementara igual** (para que el líder decida con número en mano, no
solo con la recomendación): requeriría licenciar o scrapear una base de datos de trims tipo
RevolutionParts/dealer (que es donde Omar vio BE/ES/GT/SE/SP), lo cual implica: (1) evaluar
términos de uso de esas plataformas antes de cualquier scraping (hoy fuera de alcance porque la
regla del proyecto limita scraping a "sitios pequeños que lo autoricen"), o (2) una suscripción
de pago a 7zap Premium/Partsouq (ninguno de los dos expone trim ni siquiera en el plan pagado
según lo visto en la página de precios de 7zap, que solo añade "full part numbers" y límite de
diagramas, no un campo de trim) — es decir, **ni pagando queda claro que el dato aparezca**, lo
que hace el coste alto y el retorno incierto. Estimación de esfuerzo de integración puramente
técnica (si se encontrara una fuente): 0.5–1 día (nuevo campo opcional en `vehicles.json`,
selector adicional en el asistente, sin tocar el contrato de `epc_link`).

**Alternativa recomendada en su lugar:** **AÑADIRLO SOLO CUANDO EL USUARIO TRAE UN VIN
COMPLETO**, y únicamente si `DecodeVinValues` devuelve `Trim` no vacío para ESE VIN concreto —
mostrado como dato informativo opcional, nunca como un paso obligatorio del asistente de 3
niveles (marca→modelo→año) que hoy existe. Esto es coherente con el patrón ya visto: el campo
sí funciona para otros fabricantes (ej. BMW), así que descartarlo globalmente sería perder esa
señal cuando exista; pero construir un selector de 4º nivel (marca→modelo→año→trim) **antes**
de tener VIN no tiene datos que lo sostengan hoy.
