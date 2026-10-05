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

---

## 04/10/2026 — eBay en producción, parte 1: keyset creado y endpoint de notificaciones desplegado — Líder

**El hallazgo que cambió el plan**: la cuenta de eBay Developer ya estaba aprobada, pero eso
no basta. eBay **no activa el keyset de Production** hasta que la aplicación cumpla el
requisito de notificaciones de borrado/cierre de cuenta: o se suscribe exponiendo un endpoint
HTTPS que responda su reto de verificación, o se acoge a la exención "Not persisting eBay
data".

**La exención se descartó a propósito.** Nuestra tubería sí persiste datos de eBay (títulos,
precios, URLs e imágenes de anuncios en `data/build/parts.json`, que además es público), así
que marcar esa casilla sería declarar algo falso para desbloquear las llaves un rato antes.
Se va por la suscripción, que cuesta un Worker gratis.

**Lo que se construyó y se verificó (T-B2)**:

- `infra/ebay-notifications/worker.js`: responde el reto con
  `sha256(challenge_code + verification_token + endpoint_url)` en el orden que exige eBay y
  `content-type: application/json`; acusa las notificaciones reales con 204; devuelve 400 sin
  `challenge_code`, 405 en otros métodos y **500 si faltan variables** (falla fuerte en vez
  de devolver un hash falso, que dejaría el keyset bloqueado sin decir por qué).
- 8/8 comprobaciones en local y en CI (job nuevo en `ci.yml`), con el hash contrastado contra
  una implementación independiente — no validado con el mismo código que lo produce.
- **Desplegado** con Wrangler en el subdominio propio `ebay.partexact.com` (Wrangler creó el
  registro proxeado; el ápice sigue en DNS only y el sitio no se tocó, comprobado después).
- Contra el endpoint real: el hash que devuelve coincide **carácter por carácter** con el
  calculado en local, y los casos límite responden 400/204/405.

Dos tropiezos reales del despliegue, para no repetirlos: `wrangler deploy` falla si
`workers_dev = true` y la cuenta no tiene subdominio `workers.dev` registrado — con la ruta
de dominio propio y `workers_dev = false` despliega sin pedir nada. Y el primer intento dejó
un Worker vacío (solo con el secreto) porque `wrangler secret put` crea el Worker si no
existe: no es un problema, el `deploy` posterior sube el script al mismo nombre.

**Lo que falta (T-B3, del lado de Omar)**: registrar en el portal la URL
`https://ebay.partexact.com/` y el token de verificación (vive en el `.env` local y nunca se
imprimió en pantalla) y confirmar que eBay valida el reto y activa el keyset. Después, T-B4:
cargar App ID y Cert ID con `scripts/seed-secrets.sh` y correr el pipeline en modo real.

**Tropiezo propio, documentado porque es el tipo de error que se repite**: al commitear, se
coló al repo público `infra/ebay-notifications/.wrangler/cache/wrangler-account.json` — un
archivo de caché local de Wrangler que contiene el **id de la cuenta de Cloudflare y el
nombre de la cuenta** (que en este caso incluye el correo de Omar). No son credenciales, pero
no tienen nada que hacer en un repo público. Corregido: `**/.wrangler/` agregado a
`.gitignore`, archivo sacado del árbol y commit reescrito (`--amend`) con `--force-with-lease`.
Verificado que `main` ya no lo sirve (404 en raw.githubusercontent). Queda dicho con
honestidad: el commit huérfano anterior sigue accesible por SHA directo hasta que GitHub haga
su recolección de objetos inalcanzables, así que la limpieza no es al 100 % — para que sea
definitiva habría que pedirlo a soporte de GitHub. Regla para el futuro: **nunca** `git add -A`
en carpetas que contienen cachés de herramientas (`.wrangler/`, `.venv/`, `node_modules/`);
revisar lo que `git status` propone antes de commitear.

---

## 04/10/2026 — eBay en producción, parte 2: keyset activo y datos reales en el sitio — Líder

**El keyset estaba "Non Compliant" por un formulario a medio llenar.** La captura del portal
lo dejó claro: los tres campos de *Alerts & Notifications* (correo de alertas, endpoint y
token de verificación) estaban vacíos. No era un problema de credenciales ni de código — de
hecho el App ID del `.env` coincidía con el del keyset que mostraba el portal (comprobado
programáticamente, sin imprimir valores).

**Secuencia real, con la evidencia de cada paso:**

1. Omar guardó el correo, la URL `https://ebay.partexact.com/` y el token de verificación, y
   envió una notificación de prueba.
2. `wrangler tail` en crudo capturó el reto de eBay llegando al Worker:
   `GET https://ebay.partexact.com/?challenge_code=… -> 200`. El endpoint pasó la
   verificación. (Del botón de prueba solo se vio ese GET; el POST de borrado no apareció,
   y es normal: eBay solo lo manda cuando hay un borrado real. Si llega, el Worker responde
   204.)
3. El token de OAuth empezó a funcionar: `TOKEN OK (expira en 7200s)`.
4. Búsqueda real del Browse API: **3.846 resultados** para `04152YZZA1`, con precios reales.

**Datos reales en el sitio**: con las llaves en GitHub Secrets (cargadas con
`scripts/seed-secrets.sh`, que lee el `.env` y usa la entrada estándar para que los valores
no pasen por la línea de comandos), `build-data.yml` regeneró `data/build/*.json` con **103
ofertas reales** de eBay para 3 números de parte. La tubería completa queda: API de eBay →
pipeline → GitHub Actions → `partexact.com`.

**Bug encontrado por verificar en vez de asumir**: el commit del build llevaba la marca
`[skip ci]`, así que GitHub **no disparaba el deploy** y el sitio seguía sirviendo el
fixture — con el build en verde, parecía que todo había funcionado. Confirmado comparando lo
que servía el sitio (12,99 / 7,49 USD del fixture) con lo del repo (28,00 / 31,99 USD
reales). Corregido por partida doble: se lanzó el deploy a mano para publicar ya, y se quitó
`[skip ci]` de `build-data.yml` con el porqué escrito en el propio archivo. Regla que queda:
**un job en verde no prueba que el usuario final vea los datos** — hay que mirar el artefacto
publicado.

**Segundo tropiezo, con el mismo origen y una lección nueva**: al comitear la corrección —
cuyo mensaje *explicaba* que se había quitado la marca de omitir CI— **el propio mensaje
contenía esa marca entre corchetes**, y GitHub la interpreta en **cualquier parte del
mensaje**, no solo en la primera línea. Resultado: el push del commit `6ec77dd` no disparó
ningún workflow (0 runs para ese SHA, comprobado con la API), el mismo síntoma que
acabábamos de arreglar. Regla: al documentar esta marca, escribirla de forma que no sea
literal en el mensaje de commit (o citarla sin corchetes). La verificación buena, otra vez,
fue mirar los runs por SHA y no conformarse con que el push dijera «ok».

---

## 04/10/2026 — eBay Partner Network declinó la solicitud (automática): qué sabemos y qué no — Líder

**Hecho**: Omar envió la solicitud a EPN el 04/10/2026 (cuenta de eBay personal, propiedad
`https://partexact.com/`, Business Model `Content/Reviews`, sitio declarado) y la respuesta
fue un **rechazo automático**.

**Lo que el correo dice y lo que NO dice**: es una plantilla que enumera **tres motivos
posibles** sin indicar cuál aplicó —
(a) país no soportado por el programa,
(b) el correo ya se usó para registrar una cuenta EPN,
(c) no cumplir otros criterios del Network Agreement / Código de Conducta.
El propio correo remite a `epnhelp@ebay.com` para preguntar. **No se puede deducir el motivo
del texto**, y por eso no se toca el plan hasta saberlo.

**Lo que sí se pudo comprobar**:

- El **Network Agreement vigente** (publicado el 22/01/2026) define la elegibilidad geográfica
  **por prohibición, no por lista**: solo excluye estar en un país embargado por EE.UU. o en
  la lista SDN del Tesoro. La República Dominicana no está en ninguna de las dos, así que el
  motivo (a) no encaja con la letra del propio acuerdo — aunque no se descarta que el
  obstáculo real sean sus vías de pago.
- El acuerdo exige además que **la cuenta de eBay esté "in good standing" en todo momento**,
  lo que convierte a la cuenta usada en un candidato a revisar.
- Motivos de rechazo más citados por solicitantes reales (foros): sitio "non-functioning" o
  de calidad insuficiente. El sitio está vivo y responde 200, pero el catálogo tiene **3
  partes**: "calidad" es una hipótesis razonable que el correo no menciona.

**Qué NO cambia**: el acceso a la **API de eBay es otro programa** (Developers) y sigue
funcionando: el sitio sigue mostrando anuncios y precios reales. Lo único bloqueado es la
**comisión**. El trabajo de T-B5 (enlaces de afiliado) queda implementado y probado, esperando
un campaign ID que, hoy, solo EPN puede emitir.

**Consecuencia para Fase 3**: la monetización por eBay está **en pausa hasta aclarar el
rechazo**. Si el motivo es el país y no hay vuelta, hay que reevaluar toda la Fase 3 (la
alternativa ya planificada, Advance Auto Parts vía Impact.com, es una red distinta con su
propia lista de países — **sin verificar** todavía si acepta publicadores en RD).

Pendiente de Omar: (1) comprobar si ya existe una cuenta EPN con ese correo, (2) escribir a
`epnhelp@ebay.com` preguntando por el criterio exacto.

**Actualización (misma fecha) — la cuenta SÍ existe, y eso apunta al motivo (b)**: Omar entró a
partnernetwork.ebay.com con su cuenta de eBay y encontró un panel con una cuenta
**`PartExact` (ID 7896370)** ya creada (pantalla de *Account Settings* con las secciones
General / Profile / Technical, y **sin campos rellenos**). El correo de rechazo afirma que
*"an account has not been created"*, así que esa cuenta **es anterior a la solicitud**: encaja
con el motivo (b) de la plantilla (*"your email address has already been used to register for
an eBay Partner Network account"*). Los números que traía el correo (`1354875`, `9356`) **no
coinciden** con el ID de la cuenta, así que parecen referencias internas del ticket, no la
cuenta — no sirven para cruzarlos.

**CORRECCIÓN de la deducción anterior (misma fecha, tras revisarlo Omar en el panel)**: ese
`PartExact (7896370)` **no es una cuenta de publicador**. Omar lo comprobó: no hay secciones
de enlaces, campañas ni reportes, y no hay funciones de cuenta — **solo está el perfil de la
empresa que llenó al aplicar**, es decir, el registro de la propia solicitud declinada. Por
tanto **el motivo (b) (correo duplicado) queda sin sustento**: el registro existe porque la
solicitud lo creó, no porque hubiera uno anterior. La deducción que hice antes era plausible
pero falsa, y se deja anotada precisamente por eso: **no volver a inferir el motivo desde la
existencia de un ID en el panel**.

Con (b) descartado, quedan en pie **el país (a)** y **los criterios/calidad (c)** — y ninguno
de los dos se puede distinguir desde fuera. La única vía es preguntar a EPN.

**Lo que hay que averiguar ahora, antes de escribir a soporte**: si esa cuenta está
**operativa** (se pueden crear campañas/enlaces → habría campaign ID y T-B5 se desbloquea sin
apelar nada) o si está **pendiente/rechazada** (limbo). Señales a mirar en el panel:
*Account Information* (país, zona horaria trabada en MST, estado), *Media Properties* (si
`partexact.com` ya está declarada) y, sobre todo, dónde se generan los **enlaces/campañas** y
si esa opción está disponible o bloqueada. La campana de notificaciones puede tener el aviso.

---

## 04/10/2026 — T-B5 revisada y fusionada (PR #16): enlaces de afiliado listos, esperando el ID — Líder

**Entrega (agente B)**: `pipeline/fetch_ebay.py` con `_build_affiliate_header()` (header
`X-EBAY-C-ENDUSERCTX: affiliateCampaignId=<id>[,affiliateReferenceId=<ref>]`, y **sin header**
si no hay campaign id) y `_map_item_summary_to_offer` que ahora prefiere
`itemAffiliateWebUrl` sobre `itemWebUrl`. 9 pruebas nuevas, `docs/ebay-produccion.md` y su
fila de `TASKS.md`.

**Lo que verifiqué yo, con la API real, en vez de creerle al autoinforme** (era el punto
crítico de la tarea: si el mecanismo no funciona, el ID real no serviría de nada):

| Prueba | Resultado |
|---|---|
| `python -m pytest pipeline/ -q` en la rama, corrido por el líder | **105/105 en verde** |
| Búsqueda real **sin** `EBAY_CAMPAIGN_ID` | URL plana, sin `campid` — comportamiento de hoy intacto |
| Búsqueda real **con** campaign id inventado (`5338800000`) y reference id | eBay devuelve la URL con `mkevt=1&mkcid=1&mkrid=711-53200-19255-0&campid=...` — el mecanismo funciona tal como dice su documentación |
| Diff de la rama | solo sus 4 archivos; la fila `T-B5` fue la única de `TASKS.md` tocada |
| Secretos | ninguno en el diff; `.env` nunca versionado |

La pieza de código que importa es una línea: `item.get("itemAffiliateWebUrl") or
item.get("itemWebUrl") or ""` — preferir la afiliada y caer a la normal, sin inventar
parámetros de tracking en el cliente.

**Lo que sigue sin poder verificarse, y hay que decirlo**: con un campaign id **real** no se
puede probar hasta que EPN apruebe la cuenta. El ID de prueba demuestra que eBay devuelve la
URL de afiliado cuando se pide, no que la comisión se vaya a pagar a esta cuenta. Esa parte
solo se confirma con el ID de verdad y, más adelante, con el primer reporte de conversiones
de EPN.

**Estado**: T-B5 aprobada y fusionada (9638d73). T-H2 (aviso de afiliados en el footer) sigue
bloqueada a propósito hasta que el ID real esté activo: el aviso tiene que aparecer el mismo
día que los enlaces de afiliado, ni antes ni después.

---

## 04/10/2026 — Ronda 4 revisada, fusionada e integrada: 28 partes y 33 categorías en vivo — Líder

**Tres PRs revisados por el líder y fusionados** (T-C3 #18, T-F3 #17, T-D5 #19), más el
arranque de la taxonomía. Resultado real, verificado contra el sitio publicado:

| Métrica | Antes | Ahora |
|---|---|---|
| Partes en el catálogo | 3 | **28** |
| Ofertas de eBay | 103 | **1.190**, y **1.190 de 1.190 con URL real** (cero datos de laboratorio) |
| Categorías de producto | 12 | **33** (27 con al menos una parte) |
| Pruebas | 105 Python | **114 Python + 52 Node**, todas en verde |

`pipeline/validate.py` en verde, incluida la **integridad referencial nueva** (T-D5): si una
parte apunta a una categoría que no existe o a un `fitment_id` inexistente, la validación
falla. Eso cierra el bug que encontró el líder antes de repartir (`clip-parachoques`).

**La investigación de C (#18) decide bien**: el trim de marketing (BE/ES/GT/SE/SP) **queda
fuera del MVP** con evidencia en vivo — 0 de 10 VIN reales trajeron `Trim` poblado, 7zap llega
a generación pero no a trim, y Partsouq respondió 403 de Cloudflare (que el informe distingue
correctamente de "no existe"). Es la decisión que buscábamos: decir no con pruebas.

**Solapamiento D/F, resuelto por el líder**: el agente D, para que su seed funcionara, creó
**15 de los 21 SVG** y reescribió `categories.json` — archivos del agente F, que ya estaba
fusionado. Resolución: a la rama de D se le devolvieron las versiones de main (con un commit
que explica el porqué) y se conservó **solo lo suyo** (seed, `validate.py`, pruebas). Lección
para futuras rondas: **la taxonomía y los iconos son de un solo dueño**; quien necesite una
categoría nueva, la pide — no la implementa.

**Incidente de proceso**: apareció en el checkout compartido un `data/build/parts.json`
regenerado **en modo mock** (precios de laboratorio) por algún agente que corrió el pipeline
fuera de su clon. Se descartó y **el build se regeneró con las llaves reales** después de
integrar. Regla que queda escrita: los agentes trabajan en su clon, y **los datos se
regeneran en main después de integrar**, nunca se aceptan los `data/build/*.json` que traiga
una rama.

**Pendiente al cierre de esta entrada**: T-A4 (criterio de marcas) seguía corriendo después
de 70 minutos; y la revisión **visual** de los 21 iconos nuevos no se pudo hacer con el
navegador del arnés porque Chrome tenía bloqueado el perfil (y no se le cierra la sesión al
usuario). Sí se verificó lo estructural: los 34 SVG comparten `viewBox 0 0 64 64`,
`stroke-width 2.5` y no tienen referencias externas ni imágenes incrustadas.

---

## 04/10/2026 — Revisión visual de los iconos (pasada) e investigación de EPN — Líder

**Iconos: revisión visual hecha y aprobada.** Con Chrome liberado, miré la parrilla de
categorías en el sitio en vivo. Los 34 iconos se ven coherentes entre sí, con trazo uniforme y
legibles a tamaño de chip. **Único reparo**: el de *Caliper (pinza de freno)* es abstracto
(cuadrado punteado con un círculo dentro) y no se lee como una pinza de freno — candidato a
rehacer, **no bloquea**. Verificado de paso que la parrilla del inicio es un **acordeón por
grupos** y que los conteos por grupo (5+5+6+4+4+3+3+3) suman exactamente las 33 categorías.

**EPN: investigación terminada con fuentes primarias** — `docs/epn-investigacion.md`. El
hallazgo que cambia el diagnóstico: **no habíamos considerado que el problema fuera el modelo
declarado**. El acuerdo (24/09/2026) dice que **todo método promocional no expresamente
permitido exige aprobación previa por escrito** (EXHIBIT A) y define el *Buy API Program* como
un programa aprobado de EPN para **mostrar productos de eBay con la API** (definición 8) — que
es exactamente lo que hace PartExact. En el alta se declaró **"Content/Reviews"**, y PartExact
no es un sitio de contenido: es una herramienta con integración de API. Esa vía de aprobación
previa **no la hemos tocado nunca**.

También documentado: el rechazo es **discrecional y sin apelación de derecho** ("EPN may in its
sole discretion reject your application…"); **no existe lista pública de países soportados** (el
límite declarado es la capacidad de pago, y el peso dominicano no está entre las monedas de
pago que lista el acuerdo); PayPal sí opera en RD y permite retirar a banco local, pero **no se
pudo confirmar** si *PayPal Payouts* cubre RD; y la evidencia secundaria muestra que el
formulario de alta **deja aplicar a países no soportados sin avisar** — por eso, que la
solicitud pasara el formulario no prueba nada (el mismo error de razonamiento que cometí con el
ID del panel).

**Creada T-O3**: pedir la aprobación previa por escrito del método real, en el mismo envío que
T-O1 cuando Omar lo decida. El correo ya no pregunta "por qué me rechazaron" sino **qué modelo
declarar y qué aprobación previa hace falta**.

---

## 05/10/2026 — **Ronda 4 cerrada** (T-A4, el criterio de marcas) — Líder

Entró el último PR de la ronda (**#20**, rama `agent/a-t-a4`) y traía una lección que valía más
que el propio código.

**Qué hace el criterio**: una marca es "fabricante-cascarón" (y se excluye del selector) si su
catálogo completo en vPIC tiene **≤2 modelos distintos y al menos uno se llama como la propia
marca**, normalizando sufijos (Inc, Ltd, Corp). Del selector salen **244 → 222 marcas**: 20
detectadas por el criterio y 2 residuales por nombre exacto. Antes se había probado un criterio
por año fijo y se descartó con evidencia (Byd, Sprinter, Morgan y Sterling tienen su último
registro en años distintos).

**El problema que trajo, y que era de fondo**: sus pruebas llamaban a **vPIC en vivo**. El CI
recibió **HTTP 403** (los runners de GitHub están limitados) y quedó en rojo sin que el código
tuviera nada malo. La prueba definitiva de que eran una lotería: **con el mismo código, Python
3.12 pasó y 3.11 falló**. Y la suite tardaba **39 minutos**.

**Lo que hice al revisar**:
1. Grabé las respuestas **reales** de vPIC para las marcas que se prueban
   (`pipeline/fixtures/vpic_models_for_make.sample.json`).
2. Reescribí las pruebas para reproducirlas, con un **guardián que revienta si algo intenta salir
   a la red**: así ninguna prueba puede pasar "por casualidad" contra la API en vivo.
3. Al volver a fallar el CI (misma causa, en las pruebas viejas de T-A2/T-A3), apliqué el mismo
   tratamiento a **todo** el pipeline, con un módulo compartido (`pipeline/tests/_vpic_sin_red.py`).
4. Prueba nueva: sin dato de vPIC el criterio devuelve `None`, nunca `False` — excluir por
   suposición sería peor que no excluir.

**Resultado medido**: el trabajo de pruebas del CI pasó de **39m24s a 13s**, y la suite completa
de **414s a 2,04s** (137 pruebas en verde). El PR se fusionó además con un conflicto resuelto:
era un artefacto de build (`parts.json`) y se conservó el de main, según la regla ya escrita.

**Pendiente que deja la ronda (T-A5)**: el filtro vive solo en el pipeline; el desplegable del
sitio (`site/js/vpicClient.js`) sigue pidiendo las marcas en el navegador **sin aplicar el
criterio**, así que los fabricantes-cascarón pueden reaparecer ante el usuario. Queda anotado con
su criterio de aceptación, incluida la condición de no duplicar la lógica en dos lenguajes.

---

## 05/10/2026 — **Incidente: el sitio sirvió datos de laboratorio (84 ofertas falsas)** — Líder

**Qué pasó.** Al cerrar la ronda verifiqué el sitio en vivo, como siempre, y en vez de las ~1.190
ofertas reales de eBay servía **84 ofertas inventadas** (URLs tipo
`https://www.ebay.com/itm/110123456789`). Producción estuvo mostrando datos de laboratorio.

**La cadena exacta, que es lo útil:**
1. `pipeline/tests/test_build_index.py` corría el build **en modo mock** (sin llaves, a propósito)
   y escribía el resultado en `data/build/` **del checkout** — no en una carpeta temporal.
2. Yo corrí la suite completa en el worktree de la rama y luego hice `git add -A`. Eso se llevó
   los `data/build/*.json` de laboratorio al commit.
3. El PR pasó el CI **en verde** (el CI valida la *forma* de los datos, no si son reales) y se
   fusionó. El deploy publicó los datos falsos.

**Cómo se detectó**: verificando el sitio publicado. Si me hubiera fiado del CI en verde, no lo
veo. El CI estaba verde porque `validate.py` comprueba el contrato (esquema), no la veracidad.

**Arreglos:**
1. **Causa raíz**: esa prueba ahora escribe en una **carpeta temporal** (`BUILD_DIR` de
   `build_index` y `validate` parcheados), así que una corrida de la suite ya no puede tocar los
   artefactos del repo.
2. **Guardián en el CI**: si hay ofertas y ninguna trae `hash=item` (firma inequívoca de datos de
   laboratorio), el job **falla**. Un build de mock ya no puede llegar a main sin que alguien lo vea.
3. **Datos restaurados**: regenerados con las llaves reales y verificados en el sitio en vivo.

**La lección, que es mía y no de las pruebas.** La regla ya estaba escrita en esta misma bitácora
("los artefactos derivados no se aceptan de una rama; se regeneran en main"), y la incumplí al
hacer `git add -A` en un worktree que acababa de correr la suite. Un `git add -A` no distingue
código de artefactos: hay que **añadir rutas explícitas** o mirar `git status` **buscando los
archivos derivados** antes de commitear en un worktree.

---

## 05/10/2026 — Bug reportado por un usuario real: "atrás" pierde el estado — Líder

Alguien que probó el sitio reportó: buscó una pieza, pulsó **atrás** y el sitio **volvió al
inicio**, no a donde estaba. Diagnóstico por código (no por suposición): `site/js/*.js` **no usa
en ningún punto** `pushState`, `replaceState`, `location.hash` ni `popstate` — ninguna vista deja
entrada en el historial del navegador, así que "atrás" no tiene a dónde volver y sale de la
página. Queda como **T-E5**, con el arreglo propuesto (router por hash + restauración) y su
criterio de aceptación, incluida la verificación con navegador real.

Nota de método: este bug **no lo habría encontrado ninguna prueba automática** que tuviéramos —
ninguna simula el botón atrás. Lo encontró una persona usándolo. Vale la pena tenerlo presente
cuando midamos el embudo: los usuarios encuentran lo que las pruebas no buscan.

---

## 05/10/2026 — **T-E5 resuelto: el estado del sitio vive en la URL** — Líder

**Qué era**: el botón "atrás" del navegador dejaba al visitante al principio del sitio. No era un
fallo exótico: **ninguna vista escribía en la URL**, así que no dejaban entrada en el historial y
"atrás" solo podía salir de la página.

**Cómo se arregló**: un router por hash (`site/js/router.js`) con un estado canónico por vista
(`#/numero/<n>`, `#/categoria/<slug>`, `#/vehiculo/<marca>/<modelo>/<año>[/<slug>]` y `#/vin/<vin>`).
La decisión de diseño que evita los dos problemas clásicos de esto:
- `navegar()` se llama **solo en los 6 puntos donde el usuario actúa** (enviar el buscador, elegir
  vehículo, clic en categoría, clic en el árbol, breadcrumb, "cambiar vehículo") — así la
  restauración nunca reescribe la URL ni puede provocar un bucle de renders.
- La restauración escucha `popstate` **y** `hashchange` con deduplicación por último hash atendido,
  porque un mismo "atrás" puede disparar los dos.

**Verificación con navegador real** (en local y **en el sitio en vivo**, que es lo que cuenta):

| Paso | URL | Lo que se ve |
|---|---|---|
| Al cargar | *(vacía)* | Bienvenida |
| Buscar `04152YZZA1` | `#/numero/04152YZZA1` | "1 resultado encontrado: Filtro de aceite — Toyota" |
| **Atrás** | *(vacía)* | **Vuelve a la bienvenida** (antes salía del sitio) |
| Enlace directo a esa pieza | igual | Renderiza la pieza |
| Enlace directo a `#/categoria/pastillas-freno` | igual | Renderiza la categoría |
| Enlace directo a `#/vehiculo/Mitsubishi/Outlander%20Sport/2020` | igual | Resuelve el vehículo y muestra su árbol, con la barra activa |

**Beneficio que no estaba en el encargo**: los enlaces ahora son **compartibles**. Antes no se podía
mandar a nadie "mira esta pieza"; ahora cada pieza, categoría y vehículo tiene su URL. Para un
buscador de piezas eso vale tanto como el arreglo.

**Pruebas**: 20 nuevas en `site/tests/router.test.js` (ida y vuelta URL↔estado, incluidos los casos
feos: espacios, paréntesis y acentos de marcas reales como "Sprinter (Dodge Or Freightliner)").
Frontend completo: **72 pruebas en verde** (eran 52).

---

## 04/10/2026 — Carta a EPN **enviada** (17:40) — Líder

Se envió a `epnhelp@ebay.com` con las **tres preguntas en una sola carta**: qué criterio causó
el rechazo; cuál es el modelo de negocio correcto y si ese método exige aprobación previa
(SBM / Buy API Program); y si la República Dominicana está soportada **para pagos**.

Se mandó desde el **Gmail de Omar a propósito**: es la dirección con la que se presentó la
solicitud, así que soporte puede localizarla y responder al mismo hilo. Escribir desde
`soporte@partexact.com` habría sido una dirección que EPN nunca ha visto — aquí el objetivo no
era la marca del producto, era que encontrasen la solicitud.

**Evidencia leída del propio mensaje en "Enviados"** (no de la pantalla de confirmación):
destinatario `epnhelp@ebay.com`, remitente `omar.lopezg2@gmail.com`, 4 oct 2026 5:40 p.m.,
asunto "Application declined - request for the specific reason and the correct business model
(property: partexact.com)", **cuerpo íntegro de 2.185 caracteres** (comprobado que el mensaje
menciona `Content/Reviews`, `Buy API Program` y `Dominican Republic`) y **un solo mensaje** para
ese destinatario, sin duplicados.

La carta dice expresamente que **no se volvió a aplicar** ni se creó otra cuenta mientras se
espera respuesta (una de las cláusulas del acuerdo exige consentimiento previo para eso). Texto
versionado en `docs/carta-epn.md`. T-O1 y T-O3 quedan **enviadas**; T-O2 (plan B) **sigue
bloqueada** hasta que respondan.
