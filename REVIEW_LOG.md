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
