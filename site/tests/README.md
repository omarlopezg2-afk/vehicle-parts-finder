# Pruebas del frontend (site/)

Qué tan automatizado quedó, con honestidad:

- **Automatizado:** `site/js/dataClient.js`, `site/js/vin.js`,
  `site/js/vpicClient.js`, `site/js/vehicleSession.js` y la función pura
  `groupCategories` de `site/js/categoryTree.js` tienen tests unitarios
  con `node --test` (nativo de Node, sin dependencias) en
  `site/tests/*.test.js`. Cubren `searchPart` (incluido el match contra
  `other_names`), `getPart`, `getVehicles`, `getCategories`,
  `getPartsByCategory`, `matchVehicleByVIN`, `matchVehicleByMakeModelYear`,
  `getPartsByFitment`, la detección de VIN, `getAllMakes`/
  `getModelsForMakeYear`/`getYearRange` de vpicClient.js (con un
  `fetchImpl` falso inyectado — no pegan contra vPIC real en los tests,
  para no depender de red en CI; la verificación de que vPIC responde con
  CORS abierto y datos reales se hizo a mano, ver el PR de T-E2),
  `saveVehicle`/`loadVehicle`/`clearVehicle`/`formatVehicleLabel` de
  vehicleSession.js (con un polyfill mínimo de `localStorage` en memoria,
  porque Node sin `--experimental-webstorage` no define ese global), y
  (T-E7) `groupCategories` agrupando por `group_slug`/`group_name_es`,
  preservando orden, con fallback a "Otros" si faltan esos campos, sin
  mutar el arreglo de entrada.
  Adicionalmente, `site/tests/vpicClient.real.test.js` (T-A3) SÍ pega
  contra vPIC real (sin `fetchImpl`) para verificar el filtro de
  fabricantes industriales (`MARCAS_INDUSTRIALES_EXCLUIDAS`) con datos
  reales, no con un fixture que ya asume el resultado — requiere red y NO
  está incluido en el conteo de 52 de abajo; correrlo aparte con
  `node --test tests/vpicClient.real.test.js`.
- **NO automatizado (manual):** todo lo visual/DOM (formulario, árbol de
  categorías, ficha de parte, wizard de marca/año/modelo, responsive,
  navegación por teclado). No hay Playwright/Cypress/Puppeteer instalado
  como dependencia de este proyecto — se decidió no agregar una
  dependencia de build/test pesada para un sitio que explícitamente no
  debe tener build step. Esto incluye el acordeón de grupos del árbol de
  categorías (T-E7, `renderCategoryGrid`/`renderVehicleTree`): construye
  DOM real (`document.createElement`), por lo que expandir/colapsar,
  `aria-expanded` y el orden de Tab se verifican a mano (ver sección 8 de
  abajo), igual que el resto del DOM de este proyecto. Si el líder quiere
  cobertura E2E real, lo siguiente sería agregar Playwright como
  devDependency solo para `site/` (no afecta cómo se sirve en
  producción). (Nota T-E3/E4/E5/E6: para verificar este PR se usó una
  instalación *temporal* de
  `puppeteer-core` fuera del repo, apuntando a un Chrome ya instalado en
  la máquina — no se agregó como dependencia del proyecto ni se commiteó
  nada de eso; ver "cómo probar" del PR para los pasos manuales
  equivalentes que no requieren esa herramienta.)

## 1. Correr los tests automatizados

```bash
cd site
node --test tests/*.test.js
# o: npm test
```

Debe imprimir 52 tests, 0 fallos (`dataClient.js`: 20, `categoryTree.js`:
9, `vehicleSession.js`: 8, `vin.js`: 6, `vpicClient.js`: 7,
`vpicClient.real.test.js`: 2). Los últimos 2 (T-A3, filtro de marcas
industriales contra vPIC real) requieren red — mismo trade-off que ya
acepta el lado Python en `pipeline/tests/test_fetch_vehicles_makes.py`.

## 2. Probar el sitio a mano

```bash
cd site
python3 -m http.server 8000
```

Abre `http://localhost:8000/` en el navegador (NO abras `index.html` con
`file://`: algunos navegadores bloquean `fetch` a rutas relativas en
`file://`, y aunque `dataClient.js` cae a la fixture si el fetch falla, es
mejor probar con un servidor real para que coincida con producción).

### Casos a probar

1. **Flujo VIN** — escribe `JA4AP3AW9LZ012345` (VIN de ejemplo en la
   fixture, Mitsubishi Outlander Sport 2020) en la columna "¿Conoces tu
   VIN?" y presiona "Buscar".
   - Debe aparecer la barra fija "Tu vehículo: Mitsubishi Outlander Sport
     2020 [Cambiar vehículo]" arriba de todo (T-E4) y una cuadrícula de
     categorías con sus SVG.
   - Click en "Filtro de aceite" → debe aparecer la ficha de la parte
     `1230A114`, con botón "Ver diagrama y número en la fuente" (abre
     `epc_link.url` en pestaña nueva), su equivalente WIX, una **tabla de
     fitment** "Esta pieza aplica para:" con columnas Año/Marca/Modelo
     (T-E6, en la fixture solo trae la fila 2020/Mitsubishi/Outlander
     Sport), y una oferta de eBay con botón "Comprar en eBay".
   - Debe aparecer debajo la caja "¿Ya tienes el número de tu pieza?
     Pégalo aquí". Escribe `WIX-57060` y confirma que te lleva al flujo de
     búsqueda por número y muestra esa pieza.
   - Prueba también `5YFBURHE5FP123456` (Toyota Corolla 2015, fixture).
   - Prueba un VIN de 17 caracteres que NO está en la fixture (ej.
     `AAAAAAAAAAAAAAAAA`) → debe mostrar mensaje de "no encontramos un
     vehículo", sin romperse.

2. **"Mi vehículo" persistente (T-E4)** — después del paso 1, recarga la
   página (F5).
   - Debe saltar directo al árbol de categorías de "Mitsubishi Outlander
     Sport 2020" sin pedir el VIN de nuevo (lee `localStorage`, clave
     `vpf:selectedVehicle`).
   - Presiona "Cambiar vehículo" en la barra: debe ocultarse la barra,
     borrarse `localStorage`, y volver al mensaje inicial ("Escribe un VIN
     ... o elige tu vehículo"). Recarga otra vez: ya NO debe recordar el
     vehículo anterior.
   - Repite el flujo pero resolviendo el vehículo por el wizard (paso 4) en
     vez de VIN: también debe persistir igual.

3. **Flujo número de parte** — escribe `1230A114` (o `1230-A114`, con
   guion: debe normalizar igual) en el mismo campo y presiona "Buscar".
   Debe mostrar directamente la ficha de esa parte, sin pasar por el árbol
   de vehículo (y sin tocar la barra "Tu vehículo" si ya había una).
   - Prueba también una búsqueda de texto libre, ej. `filtro` o `wix`, para
     confirmar el fallback a coincidencia parcial.
   - Prueba un número que no existe, ej. `ZZZZZZZZZZ` → mensaje de "no
     encontramos piezas", sin romperse.

4. **Selector marca → año → modelo, SIEMPRE visible (T-E3)** — en la
   columna "O elige tu vehículo", junto al buscador (sin ningún botón que
   la oculte, a diferencia de antes).
   - Espera a que cargue la lista de marcas (viene de vPIC en vivo —
     requiere internet). Elige **Mitsubishi**, luego **2020**, luego
     **Outlander Sport**, y presiona "Ver piezas para este vehículo".
   - Debe llevarte al árbol de categorías y actualizar la barra "Tu
     vehículo" (con los datos reales de `data/build/vehicles.json` si ya
     existen, o la fixture).
   - Prueba un año/marca sin modelos (poco común, pero si vPIC no tiene
     datos para esa combinación) → debe mostrar un mensaje claro, sin
     romperse.
   - Prueba con internet desconectada (o bloqueando vpic.nhtsa.dot.gov) →
     el mensaje de estado debe decir que no se pudo cargar, sin dejar la
     pantalla en blanco ni tirar un error no manejado en consola.
   - Verifica en todo momento (antes/durante/después de usar el wizard)
     que el campo de VIN/número de parte sigue visible al lado — nunca
     debe desaparecer ni quedar detrás de un toggle.

5. **Categorías destacadas en el home (T-E5), AHORA agrupadas (T-E7)** —
   antes de resolver ningún vehículo (recarga la página o presiona
   "Cambiar vehículo" primero).
   - Debe verse la sección "Categorías populares" con una lista de
     **grupos** colapsados (Mantenimiento, Frenos, Motor, Eléctrico,
     Suspensión y dirección, Refrigeración, Iluminación, Carrocería y
     exterior, Otros — 9 grupos con las 13 categorías de
     `data/build/categories.json`), cada uno como un botón con su nombre,
     un contador de cuántas categorías tiene y una flecha (▾).
   - Click en un grupo (ej. "Frenos") → debe expandirse mostrando el grid
     de SVG de sus slugs hoja (Pastillas de freno, Discos de freno) justo
     debajo, la flecha debe rotar y `aria-expanded` del botón debe pasar
     de `"false"` a `"true"` (verificable con el inspector o las
     herramientas de accesibilidad del navegador).
   - Click otra vez en el mismo grupo → debe colapsarse (oculta el grid,
     `aria-expanded` vuelve a `"false"`).
   - Click en una categoría hoja (ej. "Pastillas de freno") dentro de un
     grupo expandido, SIN vehículo resuelto → debe mostrar las piezas de
     esa categoría para TODO el catálogo (mismo comportamiento que antes
     de T-E7, no cambió), con un aviso explicando que para ver solo lo
     que aplica a tu auto hay que resolver el vehículo arriba.
   - Ahora resuelve un vehículo (VIN o wizard) y vuelve a hacer click en
     una categoría hoja del grid del home → debe mostrarte solo las
     piezas que le quedan a ESE vehículo (mismo comportamiento que el
     árbol de categorías del flujo VIN).
   - Dentro del flujo VIN/wizard (después de resolver un vehículo), el
     árbol "Elige la categoría de la pieza" debe mostrar el MISMO
     acordeón de grupos (es el mismo componente `renderCategoryGrid`
     reutilizado, ver cabecera de `categoryTree.js`).

6. **Tabla de fitment en la ficha de parte (T-E6)** — ver paso 1
   (`1230A114` trae `fitment_ids` en la fixture). Para confirmar el caso
   "sin tabla": busca una parte cuyo `fitment_ids` esté vacío (en
   `data/build/parts.json` real, al momento de este PR, TODAS las piezas
   tienen `fitment_ids: []` porque T-D1 todavía no llenó ese campo con
   datos reales) → la sección "Esta pieza aplica para:" NO debe aparecer
   (ni una tabla vacía ni un mensaje "0 vehículos").

7. **Responsive / sin scroll horizontal** — con las herramientas de
   desarrollador del navegador, prueba el modo de dispositivo móvil (ej.
   375px de ancho, iPhone SE). Verifica que no aparezca una barra de
   scroll horizontal en ninguna pantalla (buscador + selector apilados,
   barra "Tu vehículo", acordeón de grupos de categorías del home, árbol
   de categorías del vehículo, ficha de parte con tabla de fitment y
   ofertas). El nombre de un grupo largo (ej. "Suspensión y dirección")
   debe partirse en varias líneas dentro del botón en vez de desbordar o
   forzar scroll horizontal (`overflow-wrap: break-word` en
   `.category-group-name`, ver `styles.css`). Confirma que desde ~760px
   de ancho el buscador y el selector de vehículo pasan a verse lado a
   lado.

8. **Navegación por teclado** — usando solo Tab/Shift+Tab/Enter/Espacio
   (sin mouse):
   - Desde que carga la página, Tab debe llevarte primero al enlace
     "Saltar al contenido", luego (si hay un vehículo guardado) al botón
     "Cambiar vehículo", luego al campo de búsqueda, al botón "Buscar", y
     luego a los tres `<select>` del selector de vehículo (marca, año,
     modelo — cada uno navegable con flechas como cualquier `<select>`
     nativo) y al botón "Ver piezas para este vehículo" — todo accesible
     sin ningún clic previo para "revelarlo".
   - En el acordeón de grupos del home y en el árbol de categorías del
     vehículo (T-E7): con el grupo colapsado, Tab debe ir de un botón de
     grupo directo al siguiente (los slugs hoja ocultos con `hidden` NO
     son focusables, así que no "roban" un Tab de más). Enter o Espacio
     con foco en un botón de grupo debe expandirlo/colapsarlo igual que
     el click (son `<button>` nativos, responden a ambas teclas sin JS
     adicional) y actualizar su `aria-expanded`.
   - Con un grupo expandido, Tab desde ese botón de grupo debe entrar
     directo a sus slugs hoja (en el orden en que aparecen) ANTES de
     seguir al botón del siguiente grupo. Cada slug hoja sigue siendo
     alcanzable con Tab y activable con Enter/Espacio (esa lógica no
     cambió respecto a antes de T-E7).
   - Cada botón/enlace/select enfocado (grupo o slug hoja) debe tener un
     contorno amarillo visible (`:focus`, ver `site/css/styles.css`).
   - Los enlaces "Ver diagrama…" y "Comprar en…" deben ser alcanzables con
     Tab y abrir en pestaña nueva con Enter.

9. **Aviso de datos de ejemplo** — si `data/build/parts.json` y/o
   `data/build/vehicles.json` reales todavía no tienen datos completos (al
   momento de esta entrega sí existen pero con `fitment_ids` vacíos en
   todas las piezas, y la columna `other_names` no viene llena — ver
   problemas_conocidos), puede aparecer una franja amarilla arriba del
   todo: "Mostrando datos de ejemplo (fixture de desarrollo)...". Esto es
   esperado y documentado; desaparece sola cuando el archivo real
   correspondiente carga con éxito.

## 3. Qué pasa si T-D1 entrega los JSON reales

`dataClient.js` intenta primero `./data/build/<archivo>.json` (dentro de
`site/`) y solo cae a la fixture si ese fetch falla. Por ahora
`site/data/build/categories.json` ya es una copia del archivo real
aprobado (T-F1); `parts.json` y `vehicles.json` reales no existen todavía
en ninguna rama, así que para esos dos siempre se usa la fixture.

Cuando T-D1 los genere, el supuesto de este agente es que un paso de build
o el workflow de deploy (T-G2) copiará `data/build/*.json` dentro de
`site/data/build/` antes de publicar — ver el comentario largo al inicio
de `dataClient.js` y la sección de supuestos del PR para más detalle. Si
el líder decide otra ruta de despliegue, el único archivo que hay que
tocar es `dataClient.js` (regla de escalado).
