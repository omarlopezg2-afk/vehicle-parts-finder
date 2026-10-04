# Pruebas del frontend (site/)

Qué tan automatizado quedó, con honestidad:

- **Automatizado:** `site/js/dataClient.js`, `site/js/vin.js` y
  `site/js/vpicClient.js` tienen tests unitarios con `node --test`
  (nativo de Node, sin dependencias) en `site/tests/*.test.js`. Cubren
  `searchPart`, `getPart`, `getVehicles`, `getCategories`,
  `matchVehicleByVIN`, `matchVehicleByMakeModelYear`, `getPartsByFitment`,
  la detección de VIN, y `getAllMakes`/`getModelsForMakeYear`/
  `getYearRange` de vpicClient.js (con un `fetchImpl` falso inyectado —
  no pegan contra vPIC real en los tests, para no depender de red en CI;
  la verificación de que vPIC responde con CORS abierto y datos reales se
  hizo a mano, ver el PR de T-E2).
- **NO automatizado (manual):** todo lo visual/DOM (formulario, árbol de
  categorías, ficha de parte, wizard de marca/año/modelo, responsive,
  navegación por teclado). No hay Playwright/Cypress/Puppeteer instalado
  en este proyecto — se decidió no agregar una dependencia de build/test
  pesada para un sitio que explícitamente no debe tener build step. Si el
  líder quiere cobertura E2E real, lo siguiente sería agregar Playwright
  como devDependency solo para `site/` (no afecta cómo se sirve en
  producción).

## 1. Correr los tests automatizados

```bash
cd site
node --test tests/*.test.js
# o: npm test
```

Debe imprimir 28 tests, 0 fallos (`dataClient.js`: 16, `vin.js`: 6,
`vpicClient.js`: 6).

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
   fixture, Mitsubishi Outlander Sport 2020) y presiona "Buscar".
   - Debe aparecer la tarjeta del vehículo y una cuadrícula de categorías
     con sus SVG.
   - Click en "Filtro de aceite" → debe aparecer la ficha de la parte
     `1230A114`, con botón "Ver diagrama y número en la fuente" (abre
     `epc_link.url` en pestaña nueva), su equivalente WIX, y una oferta de
     eBay con botón "Comprar en eBay".
   - Debe aparecer debajo la caja "¿Ya tienes el número de tu pieza?
     Pégalo aquí". Escribe `WIX-57060` y confirma que te lleva al flujo de
     búsqueda por número y muestra esa pieza.
   - Prueba también `5YFBURHE5FP123456` (Toyota Corolla 2015, fixture).
   - Prueba un VIN de 17 caracteres que NO está en la fixture (ej.
     `AAAAAAAAAAAAAAAAA`) → debe mostrar mensaje de "no encontramos un
     vehículo", sin romperse.

2. **Flujo número de parte** — escribe `1230A114` (o `1230-A114`, con
   guion: debe normalizar igual) y presiona "Buscar". Debe mostrar
   directamente la ficha de esa parte, sin pasar por el árbol de vehículo.
   - Prueba también una búsqueda de texto libre, ej. `filtro` o `wix`, para
     confirmar el fallback a coincidencia parcial.
   - Prueba un número que no existe, ej. `ZZZZZZZZZZ` → mensaje de "no
     encontramos piezas", sin romperse.

3. **Flujo "elige tu vehículo sin VIN" (drill-down marca → año → modelo)**
   — junto al buscador, presiona el botón "¿No tienes tu VIN a mano? Elige
   tu vehículo" (debe cambiar `aria-expanded` a `true` y mostrar el
   wizard).
   - Espera a que cargue la lista de marcas (viene de vPIC en vivo —
     requiere internet). Elige **Mitsubishi**, luego **2020**, luego
     **Outlander Sport**, y presiona "Ver piezas para este vehículo".
   - Debe llevarte al MISMO árbol de categorías que el flujo VIN (compara
     con el punto 1 usando el VIN real `JA4AP4AU3LU023739`: ambos caminos
     deben mostrar "Mitsubishi Outlander Sport 2020" con el mismo motor).
   - El botón "Buscar" de vuelta se oculta y el wizard se cierra al
     completarse.
   - Prueba un año/marca sin modelos (poco común, pero si vPIC no tiene
     datos para esa combinación) → debe mostrar un mensaje claro, sin
     romperse.
   - Prueba con internet desconectada (o bloqueando vpic.nhtsa.dot.gov) →
     el mensaje de estado debe decir que no se pudo cargar, sin dejar la
     pantalla en blanco ni tirar un error no manejado en consola.

4. **Responsive / sin scroll horizontal** — con las herramientas de
   desarrollador del navegador, prueba el modo de dispositivo móvil (ej.
   375px de ancho, iPhone SE). Verifica que no aparezca una barra de
   scroll horizontal en ninguna pantalla (buscador, wizard de
   marca/año/modelo, árbol de categorías, ficha de parte con ofertas).

5. **Navegación por teclado** — usando solo Tab/Shift+Tab/Enter/Espacio
   (sin mouse):
   - Desde que carga la página, Tab debe llevarte primero al enlace
     "Saltar al contenido", luego al campo de búsqueda, luego al botón
     "Buscar", luego al botón "¿No tienes tu VIN a mano?...".
   - Al abrir el wizard con Enter/Espacio, Tab debe llevarte a los tres
     `<select>` (marca, año, modelo — cada uno navegable con flechas como
     cualquier `<select>` nativo) y luego al botón "Ver piezas para este
     vehículo".
   - En el árbol de categorías, cada botón de categoría debe ser
     alcanzable con Tab y activable con Enter/Espacio.
   - Cada botón/enlace/select enfocado debe tener un contorno amarillo
     visible (`:focus`, ver `site/css/styles.css`).
   - Los enlaces "Ver diagrama…" y "Comprar en…" deben ser alcanzables con
     Tab y abrir en pestaña nueva con Enter.

6. **Aviso de datos de ejemplo** — como `data/build/parts.json` y
   `data/build/vehicles.json` reales de T-D1 todavía no existen al momento
   de esta entrega, debe aparecer una franja amarilla arriba del todo:
   "Mostrando datos de ejemplo (fixture de desarrollo)...". Esto es
   esperado y documentado; desaparece sola cuando T-D1 entregue los JSON
   reales y se copien a `site/data/build/` (ver comentario en
   `dataClient.js`).

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
