# Registro de revisiones del líder

Formato por entrada: fecha, tarea, agente, resultado (aprobada / cambios pedidos), motivo.

---

## 25/09/2026 — Fase 0 — Líder

**Resultado: aprobada (autorrevisión de fundación).**

Creado el esqueleto del repo, `CONTRACTS.md` (congelado), `TASKS.md` (T-A1 a T-H1
definidas), este log, y estructura de carpetas completa. Contratos fusionan el plan externo
de Omar (estructura de repo, equipo de agentes, flujo de PR) con el núcleo ya decidido el
24/09 (VIN → vPIC → ensamblaje → deep link EPC → número → eBay Browse API → afiliado).
Diferencia explícita respecto al plan externo: se agrega el agente C (EPC-Puente, no estaba
en el plan de Omar) porque sin él se perdía el paso central del producto; y se mueve la
solicitud a eBay Partner Network de Fase 0 a Fase 3, por evidencia de que un sitio vacío
suele ser motivo de rechazo (ver `investigacion-ebay-24sep2026.md` en la carpeta del
proyecto, fuera del repo).

Pendiente de Omar antes de poder cerrar Fase 0 del todo: cuenta de eBay Developers (gratis,
no depende de tener sitio) y decidir si se compra dominio propio ahora o se deja para Fase 4.

Próximo paso: lanzar en paralelo T-A1, T-B1, T-C1, T-F1, T-G1 (no dependen entre sí).

---

## 03/10/2026 — Fase 1 — Líder

**Resultado: las 5 tareas de Fase 1 (T-A1, T-B1+T-B2, T-C1, T-F1, T-G1) aprobadas y
fusionadas a `main` (PRs #1 a #5).** CI en verde con las 5 piezas integradas (43 tests).

Revisión por tarea:
- **T-A1 (vPIC)**: cumple el esquema, maneja VIN inválido sin excepción, 7 tests contra la
  API real (incluye un VIN real de Outlander Sport 2020, no el de Omar específicamente —
  documentado en el PR, reemplazable). Aprobado sin cambios.
- **T-B1/T-B2 (eBay)**: modo mock funciona out-of-the-box con fixture realista, modo real
  implementado según los datos verificados el 24/09 pero sin probar contra la API real
  (no hay llaves todavía — Omar está tramitando la cuenta developer). Normalización
  correcta. Aprobado sin cambios; falta prueba end-to-end cuando haya llaves.
- **T-C1 (EPC-Puente)**: la pieza más importante del plan. 7zap funciona con estructura
  estable (verificado por fetch HTTP con headers de navegador real, no por screenshot —
  Cloudflare bloqueó el navegador automatizado del agente en 7zap/Partsouq/tiendas
  oficiales). Partsouq funciona por VIN directo. Tienda oficial de Mitsubishi: sin URLs
  estables por categoría, el agente lo reportó con honestidad en vez de inventar un link.
  Aprobado — es exactamente el nivel de rigor que se pedía.
- **T-F1 (SVG)**: 13 iconos con viewBox y stroke-width idénticos, estilo consistente
  verificado por script (no hubo renderizador disponible para verificación visual real,
  queda como riesgo menor a revisar a simple vista más adelante). Aprobado.
- **T-G1 (CI)**: workflow correcto, corrió en verde en el PR. Aprobado.

**Corrección del líder al integrar (no requirió reabrir ningún PR)**: el agente C puso sus
tests en `tests/` (raíz) en vez de `pipeline/tests/`; el CI solo corre `pytest pipeline/`,
así que esos 14 tests nunca se ejecutaban en el pipeline de integración aunque pasaran en
local — un hueco real que no se habría notado sin revisar el log de Actions tarea por
tarea, no solo el resultado "success" del check. Se movieron a `pipeline/tests/` siguiendo
la misma convención de import de A y B, directo a `main` (commit del líder, no un PR de
agente, porque es trabajo de integración). Verificado después: 43/43 tests pasan desde
`pipeline/`, CI en verde con el fix incluido.

Próximo paso: lanzar T-D1 (Pipeline-Build, ya puede arrancar con A+B+C en main) y T-E1
(Frontend, puede arrancar ya con `data/seed/` + los SVG de F).

---

## 03/10/2026 (tarde) — Fase 2 — Líder

**Resultado: T-D1 y T-E1 aprobadas y fusionadas a `main` (PRs #6 y #7).** CI en verde,
76 tests Python + 18 tests Node, build+validate limpios.

Revisión por tarea:
- **T-D1 (build_index.py + validate.py)**: corre 100% offline/mock según se pidió — si
  vPIC no responde cae a un vehículo fijo de respaldo, eBay ya caía a mock sin llaves
  (T-B1), EPC nunca hace red. `validate.py` falla con exit code distinto de 0 si algo no
  cumple CONTRACTS.md, tal como necesita `ci.yml` (T-G1) para usarlo. 33 tests propios.
  Aprobado sin cambios.
- **T-E1 (frontend)**: cumple las 4 pantallas pedidas, `dataClient.js` es el único archivo
  que hace fetch (verificado con grep), responsive y navegable por teclado. Agregó 2
  funciones fuera de la superficie literal del contrato (`matchVehicleByVIN`,
  `getPartsByFitment`) para el flujo VIN→categorías que el contrato no cubría — se
  aceptan, viven en el único archivo que toca JSON, no rompen la regla de escalado.

**Gap real encontrado al integrar los dos PRs (ninguno se habría notado revisándolos por
separado, solo apareció al mezclarlos)**: T-D1 genera `vehicles.json` con
`id: "vin-<VIN>"` y SIN campo `vin` separado. T-E1 había asumido —correctamente marcado
como supuesto a revisar en su propio PR— que existía un campo `vin` suelto, porque su
fixture de desarrollo lo tenía. Sin el fix, `matchVehicleByVIN` nunca habría encontrado un
vehículo real, solo los de la fixture. Corregido en el merge de integración (commit en la
rama de E antes de fusionar, no un PR nuevo): la función ahora extrae el VIN del patrón
`vin-<VIN>` del `id`, con fallback a un campo `vin` opcional por compatibilidad. Verificado
end-to-end: servidor HTTP local sirviendo `site/`, consulta con el VIN real
`JA4AP3AU0LU000302` (el mismo que usa T-A1/T-D1) devuelve el Mitsubishi Outlander Sport
2020 real, no un dato de fixture.

También se copiaron los 4 `data/build/*.json` reales de T-D1 a `site/data/build/` (lo que
T-E1 ya asumía que pasaría vía build/deploy), con README explicando que es temporal hasta
que T-G2 lo automatice. Conflicto de fusión en `TASKS.md` (ambos PRs editaban filas
distintas) resuelto sin pérdida de información.

Pendiente de Omar: sigue sin llegar la aprobación de la cuenta de eBay Developer (en
trámite). No bloquea nada de lo construido hasta ahora — todo corre en modo mock.

Próximo paso: T-G2 (`build-data.yml` + `deploy-site.yml`, ya puede arrancar con T-D1 en
main) es la única tarea de Fase 2 que falta antes de poder publicar el sitio en GitHub
Pages. T-H1 (legal/EPN) sigue aplazada a Fase 3.

---

## 03-04/10/2026 — Repo público + Pages + Fase 2.5 (drill-down) — Líder

**Repo pasado a público** (`gh repo edit --visibility public`) porque GitHub Pages no
funciona con repos privados en plan Free (confirmado con un intento real contra la API:
`"Your current plan does not support GitHub Pages for this repository"`). No había secretos
en el código (las llaves van en `.env`/Secrets, nunca en el repo), así que no hay riesgo.
Pages activado (`build_type=workflow`). **T-G2 fusionado (PR #8)**: `build-data.yml` +
`deploy-site.yml`. El agente fue honesto sobre no poder probar el deploy real antes del
merge (restricción real de GitHub: `workflow_dispatch` en rama feature da 404) — lo verifiqué
yo después del merge: deploy automático corrió en éxito, sitio responde 200 en
https://omarlopezg2-afk.github.io/vehicle-parts-finder/ con datos reales.

**Fix de líder**: Omar probó el sitio con su VIN real (`JA4AP4AU3LU023739`) y no lo
encontró — el build usaba un VIN de ejemplo distinto puesto a mano en Fase 0. Verificado
contra vPIC: el VIN de Omar decodifica a Mitsubishi Outlander Sport 2020 (el caso de prueba
exacto de PLAN.md). Cambiado `EXAMPLE_VIN` en `build_index.py`, regenerado y desplegado.

**Monetización multi-tienda**: investigación con fuentes oficiales (AutoZone, O'Reilly,
Advance Auto Parts, RockAuto). Ninguna tiene API de precio/stock. Solo **Advance Auto
Parts** tiene programa de afiliados real y corre en Impact.com (misma cuenta que eBay EPN)
— se agrega a Fase 3. AutoZone (red distinta, Pepperjam/Ascend, no justifica el overhead),
O'Reilly (sin programa de venta real) y RockAuto (su propio newsletter niega vender en
sitios de afiliados) quedan descartados. Documentado en PLAN.md.

**T-A2 (PR #9, aprobada)**: `get_all_makes()` y `get_models_for_make_year()` agregadas a
`fetch_vehicles.py` (Python/pipeline), completando el drill-down marca→modelo→año que
PLAN.md siempre mencionó pero no se había construido. Filtrado car+mpv de vPIC, documentado
que no es perfecto (mezcla camiones Fuso bajo "Mitsubishi", excluye pickups puras).

**T-E2 (PR #10, aprobada)**: integración al frontend. El agente eligió fetch directo del
navegador a vPIC (Opción A) en vez de un JSON pre-generado (Opción B), verificando CORS
abierto antes de decidir — yo lo re-verifiqué de forma independiente con curl real:
`access-control-allow-origin: *`. Nuevo módulo `site/js/vpicClient.js`, aislado de
`dataClient.js`, documentado como excepción deliberada a la regla de escalado de
CONTRACTS.md (vPIC no es nuestro catálogo, es un servicio externo). Verificado por mí tras
el merge: solo 2 archivos hacen fetch en todo `site/js/` (dataClient.js y vpicClient.js,
confirmado con grep), 28/28 tests pasan, y probé el flujo real contra la API real de vPIC:
247 marcas filtradas (vs 12,380 crudas sin filtrar), Mitsubishi presente, "Outlander Sport"
presente en los modelos de Mitsubishi 2020.

Pendiente de Omar: cuenta eBay Developer (en trámite), y ahora también Advance Auto Parts
vía Impact.com cuando se llegue a Fase 3.

---

## 04/10/2026 — Fase 2.5 (UX inspirada en factorymitsubishiparts.com) — Líder

**Resultado: T-D2 y T-E3/E4/E5/E6 aprobadas y fusionadas (PR #11, PR #12).** 96 tests
Python + 40 tests Node, build+validate limpio, deploy automático verificado en vivo.

**T-D2 (PR #11)**: campo `other_names[]` propagado en `build_index.py` (default `[]`,
nunca falta la clave, mismo patrón que `epc_link`), validado por tipo en `validate.py`
(falla si no es array de strings). Parte de ejemplo agregada en `data/seed/` con 3
sinónimos reales de un clip de parachoques. Aprobado sin cambios.

**T-E3/E4/E5/E6 (PR #12)**: las 4 mejoras de UX pedidas por Omar tras ver
factorymitsubishiparts.com.
- **T-E3** (la prioridad de Omar): verificado en el HTML real servido — ambas secciones
  (`¿Conoces tu VIN?` / `O elige tu vehículo`) están en el DOM sin ningún botón/`hidden`
  que las oculte, mobile-first apiladas y lado a lado desde 760px. Confirmado también en
  el sitio ya publicado.
- **T-E4**: `vehicleSession.js` nuevo, aislado de `dataClient.js` (mismo criterio que
  `vpicClient.js`: localStorage es estado de sesión del navegador, no catálogo).
- **T-E5**: decisión de diseño documentada — clic en categoría sin vehículo resuelto
  navega el catálogo completo de esa categoría (`getPartsByCategory()`, nueva función en
  `dataClient.js`, mismo patrón que `getPartsByFitment`/`matchVehicleByVIN`: vive ahí para
  no romper la regla de escalado aunque no esté en la superficie literal del contrato).
- **T-E6**: tabla de fitment se oculta si `fitment_ids` está vacío (no tabla vacía),
  verificado con los datos reales actuales (vacíos hoy, por eso no se ve aún en
  producción — comportamiento esperado, documentado honestamente por el agente).
- **Bonus no pedido explícitamente pero correcto**: `searchPart()` ya matchea contra
  `other_names[]`, coordinado con T-D2 en paralelo sin pisarse (archivos distintos).
  Verificado por mí tras fusionar ambos PRs: buscar "grille clip" (un sinónimo, no el
  nombre canónico "Clip retenedor de parachoques") sí encuentra la pieza.

Encontré un bug real de CSS durante la verificación visual del propio agente (`[hidden]`
perdía contra `.vehicle-bar{display:flex}`) — ya lo corrigió él mismo antes de entregar,
documentado en su reporte. No hubo que reabrir nada.

**Backlog registrado para la próxima ronda** (pedido explícito de Omar, con imagen de
referencia, NO lanzar sin indicación): 3 huecos verificados contra vPIC antes de anotarlos
en `TASKS.md` — (1) filtro de marcas sigue colando fabricantes industriales (confirmado:
FREIGHTLINER aparece en car+mpv), (2) falta nivel de Trim/Submodelo (confirmado que vPIC
NO lo resuelve de forma confiable: el VIN real de Omar trajo `Trim` vacío), (3) categorías
del catálogo más granulares (RockAuto como referencia de taxonomía estándar de industria,
no de datos propietarios).

Pendiente de Omar: cuenta eBay Developer (en trámite), Advance Auto Parts vía Impact.com
(Fase 3).

---

## 04/10/2026 — Ronda 3 (marcas, trim, categorías jerárquicas) — Líder

**Resultado: T-A3, T-F2, T-E7 aprobadas y fusionadas (PR #14, #13, #15). T-C2 cerrada sin
código, hallazgo documentado en TASKS.md.**

**Incidente de cuota**: la ventana de 5h de Anthropic se agotó anoche justo cuando los 3
agentes de la ronda terminaban. T-A3 y T-C2 quedaron a medias (código listo pero sin PR
abierto, o investigación cortada a mitad). Al retomar: T-A3 se revisó y su PR se abrió
manualmente por el líder (el código ya estaba completo y verificado); T-C2 se relanzó con
contexto explícito de dónde se había cortado, para no repetir investigación ya hecha.

**T-A3 (filtro de marcas)**: lista de exclusión explícita (no heurística), investigada
contra la API real de vPIC — de ~207 fabricantes de camión/bus, solo 3 se colaban en
car+MPV (Freightliner, Blue Bird, Orion Bus); se agregaron esos + una lista de fabricantes
industriales conocidos como defensa en profundidad. Comparación por nombre EXACTO, no
substring — verificado por el líder que esto es necesario: existe una marca legítima
"Sprinter (Dodge Or Freightliner)" que se habría filtrado por error con un match de
substring. Verificado post-merge contra la API real: Freightliner (solo) ya no aparece,
el Sprinter sigue ahí, Mitsubishi/Toyota/Isuzu presentes. 98+43 tests.

**T-C2 (Trim)**: durante la ejecución se detectó en vivo que el agente había quedado
**enganchado en un bucle real** — 4 reintentos seguidos de `browser_exec` contra un perfil
de Chrome bloqueado (mismo error de lock de SQLite que el líder ya había visto antes en
esta sesión), sin avanzar. Corregido con `delegate_task(action='steer')`: se le ordenó
dejar de usar el navegador, cambiar a `curl`/`web_search` como alternativa, y cerrar con
una conclusión honesta si no lograba nada concluyente en pocos intentos más — en vez de
dejarlo reintentando indefinidamente. El agente respondió bien a la corrección. Conclusión
final: 7zap confirmado que NO tiene el dato en su catálogo público (solo infraestructura
i18n sin poblar); Partsouq ni confirmado ni descartado (Cloudflare bloqueó el acceso
directo, pero hay evidencia indirecta de que su esquema de datos sí lo tiene para modelos
hermanos del Outlander Sport). No se construye nada; el wizard se queda en 3 niveles.

**Verificación adicional pedida por Omar**: tras cerrar T-C2, Omar preguntó qué requeriría
"cambiar a Partsouq". El líder intentó verificar en vivo el link de Partsouq que el
proyecto ya genera, con el navegador real (no headless) — 3 intentos, incluyendo clic en
el checkbox de Cloudflare Turnstile tras que Omar cerrara su Chrome personal para liberar
el perfil. Ni siquiera con perfil real y clic humano-simulado se pasó el challenge (quedó
en "Verificando..." y volvió al estado inicial) — confirma que el bloqueo no es solo
cuestión de clic, hay algo del entorno CDP/automatizado que Cloudflare detecta. Queda
pendiente que Omar lo pruebe él mismo en su navegador normal para confirmar si un usuario
real sin automatización sí pasa. Conclusión para el proyecto: aunque se resolviera el
acceso, Partsouq no tiene URLs de catálogo construibles de antemano (usa un token `ssd`
generado por su servidor al resolver un VIN en su buscador) — el cuello de botella real es
arquitectónico, no solo de acceso.

**T-F2 (categorías jerárquicas)**: 13 slugs agrupados en 8 grupos + "Otros" con criterio
técnico-automotriz razonable (Frenos, Motor, Eléctrico, Suspensión y dirección,
Refrigeración, Mantenimiento, Iluminación, Carrocería y exterior). `validate.py` sigue en
verde (no valida el campo nuevo contra tipo todavía, documentado honestamente por el
agente, no bloqueante).

**T-E7 (árbol agrupado)**: patrón estándar de disclosure widget (`aria-expanded` +
`aria-controls` + atributo `hidden`), sin reinventar roles ARIA complejos para una
jerarquía de 2 niveles — decisión correcta. No tocó `app.js` (mismo componente reutilizado
sin cambiar firma). Verificado por el líder con el navegador real tras el merge: 8 grupos
renderizados, toggle de `aria-expanded` funciona (`false`→`true` al click, panel se
revela). 52/52 tests.

Pendiente de Omar: cuenta eBay Developer (en trámite), Advance Auto Parts vía Impact.com
(Fase 3).

---

## 04/10/2026 — Confirmación de Partsouq por Omar — Líder

**Resultado: Partsouq SÍ funciona de punta a punta para un usuario real — queda
confirmado, cerrando la duda que quedó abierta en la Ronda 3.**

Omar probó en su propio navegador (no automatizado) el link que el proyecto ya genera
(`https://partsouq.com/en/search/all?q=<VIN>`) con su VIN real
(`JA4AP4AU3LU023739`):

1. **Pasó el challenge de Cloudflare Turnstile sin problema** — algo que el navegador
   automatizado del líder no logró en 2 intentos distintos (ver entrada de Ronda 3).
   Confirma que el bloqueo es puramente de detección de automatización, no del link.
2. **La búsqueda devolvió 3 coincidencias de vehículo** para el mismo VIN (ASX(G.EXP),
   Outlander Sport(P&G), Outlander Sport(MMNA)) — Partsouq decodifica por plataforma
   compartida (chasis GA2W) y lista las variantes de mercado, no un único resultado.
   MMNA = Mitsubishi Motors North America, la variante correcta para EE.UU.
3. **Al entrar a esa variante, cargó un catálogo OEM ilustrado real**: categoría "Engine"
   con 24 diagramas (Oil pump & Oil filter, A/T valve body, Power steering oil pump,
   cylinder head, camshaft/timing, engine mount), con sub-etiquetas de pieza clicables
   (ej. "Engine oil filter", "Oil pump chain"). Esto es exactamente lo que el flujo
   VIN→EPC del proyecto necesita: diagrama real + ruta hacia el número de parte.

**Matiz honesto, no un problema**: el catálogo etiqueta el vehículo como "Airtrek /
Outlander" (nombre de plataforma global), no "Outlander Sport" (nombre de mercado EE.UU.)
— es la misma pieza/catálogo, solo cambia el nombre comercial mostrado. Tampoco aparece
ningún selector de trim BE/ES/GT/SE/SP en esta pantalla — consistente con el hallazgo de
T-C2: el campo "Modification" de Partsouq usa códigos de tren motriz (H-LINE, S-CVT), no
los nombres de trim de marketing de EE.UU.

**Conclusión actualizada para el proyecto**: Partsouq es una fuente EPC viable para
usuarios reales (no solo "URL construida pero sin verificar" como quedó documentado
antes) — el link de búsqueda por VIN que ya generamos en `fetch_epc_links.py` SÍ lleva a
un catálogo real y navegable. El límite que sigue en pie es que **nuestros agentes no
pueden verificarlo de forma automatizada** (Cloudflare), así que cualquier intento futuro
de extraer datos de Partsouq (ej. para completar T-C2) seguirá necesitando verificación
manual o una técnica anti-Cloudflare real — no cambia la recomendación de "no vale la
pena automatizar scraping aquí", pero sí sube la confianza en el link que mostramos al
usuario.

Pendiente de Omar: cuenta eBay Developer (en trámite), Advance Auto Parts vía Impact.com
(Fase 3).

---

## 04/10/2026 — Fase 4: dominio comprado y sitio publicado en `partexact.com` — Líder

**Contexto**: era el pendiente que quedó abierto al cerrar el nombre de marca. Omar pidió
comprarlo reutilizando la cuenta de Cloudflare donde ya vive `wifimonitor.app`.

**Qué se hizo, con la evidencia real de cada paso:**

1. **Compra** en Cloudflare Registrar (misma cuenta que `wifimonitor.app`): 10,46 USD/año,
   renovación automática activada, contacto WHOIS redactado por Cloudflare, tarjeta guardada
   de la cuenta (terminada en 5730). Orden `ea1d18dd-15b0-44cc-93f0-81c0ca732c22`.
2. **Verificación independiente del registro** (no la pantalla de confirmación del panel):
   `whois partexact.com` → `Creation Date: 2026-10-04T11:23:30Z`, `Registry Expiry Date:
   2027-10-04`, `Registrar: Cloudflare, Inc.`, nameservers `gracie`/`skip.ns.cloudflare.com`.
3. **DNS** hecho en el panel de Cloudflare, no por API (esta cuenta no tiene token de API y
   no valía la pena crear uno para 5 registros): 4 A en el ápice → 185.199.108.153 / .109 /
   .110 / .111.153, y CNAME `www` → `omarlopezg2-afk.github.io`, **todos con el proxy
   APAGADO (DNS only)**. Verificado con `dig` contra 1.1.1.1: los 4 A en el ápice, el CNAME
   de `www` y su resolución a esos mismos 4 A de GitHub.
4. **GitHub Pages**: `pages.cname = partexact.com` puesto por API; el certificado quedó en
   `authorization_created` para `partexact.com` + `www.partexact.com` (lo emite GitHub solo,
   tarda unos minutos). `www` ya responde 301 → `http://partexact.com/` y el ápice sirve el
   HTML con el `<title>` de marca correcto (`PartExact — Encuentra la pieza exacta de tu
   vehículo`), comprobado con una petición real al dominio, no con la vista previa del panel.

**Decisión técnica que conviene no olvidar**: los registros van en *DNS only*. Con el proxy
naranja de Cloudflare activo, GitHub Pages no puede completar el reto HTTP para emitir su
propio certificado (Cloudflare responde en su lugar). Si algún día se quiere el proxy por
performance/anti-bot, hay que asumir el certificado de Cloudflare y pasar el modo SSL a
*Full (strict)* — es una configuración o la otra, no las dos a la vez.

**Lo que NO se hizo, a propósito**: renombrar el repo (`vehicle-parts-finder` →
`partexact`) y el logo. Ninguno bloquea nada; ambos quedan anotados en `PLAN.md`.

**Correo del dominio (misma fecha, pedido por Omar al ver las recomendaciones del panel)**:
Cloudflare mostraba 3 recomendaciones y solo una era real — las dos de "los visitantes no
pueden llegar a partexact.com / www" eran **cálculos viejos** hechos con la zona vacía
(el panel no las recalcula al instante); el sitio ya servía y `dig` lo confirmaba. La real
era la de correo: el dominio no tenía ni MX ni SPF ni DMARC, o sea que cualquiera podía
falsificar `@partexact.com` (phishing con la marca) y no había forma de recibir un
`soporte@` cuando lo pida una tienda o eBay Partner Network.

Se activó **Email Routing** (gratis): 3 MX `route1/2/3.mx.cloudflare.net`, SPF
`v=spf1 include:_spf.mx.cloudflare.net ~all`, DKIM en `cf2024-1._domainkey`, y reglas
`soporte@`, `hola@` y `support@partexact.com` → la dirección verificada de Omar (la
verificación fue automática, sin correo de confirmación que clicar). Y **DMARC Management**
con `p=none` (solo monitoreo, no bloquea nada) + reportes a Cloudflare. Todo verificado por
DNS público; el *catch-all* se dejó en `Drop` a propósito (que no entre spam de direcciones
inventadas).

**Nota para pruebas futuras**: desde la red de casa **no se puede** probar la entrega
entrante hablándole directo al MX: Cloudflare rechaza la conexión con *"Sender IP reverse
lookup rejected"* (la IP residencial no tiene rDNS válido). La prueba de punta a punta hay
que hacerla enviando desde un correo real (Gmail) a `soporte@partexact.com` y mirando el
**Activity log** de Email Routing para confirmar el reenvío.

**Prueba de punta a punta: ✅ pasada (04/10).** Omar envió un correo desde su Gmail a
`soporte@partexact.com`; el Activity log de Email Routing lo registra como **Forwarded**
(asunto «Hola Hermes», remitente `omar.lopezg2@gmail.com`). El reenvío de la marca al
buzón real funciona. Dos matices que salieron en la prueba, y que conviene recordar:

1. **Gmail no enseña el reenvío cuando el remitente y el destino son la misma cuenta.**
   Cloudflare lo avisó por correo: Gmail deduplica, así que el mensaje reenviado no
   aparece como nuevo (se ve el que uno mandó). No es un fallo del reenvío — el propio
   Cloudflare manda un aviso explicándolo. Para probar «de verdad» hay que enviar desde
   una cuenta distinta a la de destino (o mirar el Activity log, que es la fuente que no
   miente).
2. **El primer intento desde Gmail falló** y el segundo funcionó: era la caché negativa
   del DNS (el dominio se registró minutos antes, así que durante un rato "partexact.com
   no existe" seguía cacheado en el resolutor de Google). Se cura solo en ~30 min.

Pendiente de Omar para cerrar Fase 3: keyset de **Production** de eBay (la cuenta de
Developer ya fue aprobada el 04/10) — con Client ID + Client Secret se activa el modo real
de `fetch_ebay.py` (GitHub Secrets + `.env` local, nunca en el repo).
