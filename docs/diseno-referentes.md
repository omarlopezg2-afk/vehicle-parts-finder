# Referentes de diseño (benchmark) — 04/10/2026

> Medido con capturas reales, no de memoria. **Lección de método**: Chrome *headless* con su
> identificador por defecto (`HeadlessChrome`) recibe cáscaras vacías de los sitios con
> protección antibot — Partsouq devolvió 43 KB y eBay **0 bytes**. Con identificador de
> navegador normal y perfil persistente: Partsouq **281 KB** y eBay **505 KB**. El fallo era
> el navegador, no los sitios. (Ya estaba anotado para Partner Center y no se aplicó.)

## Partsouq — la referencia para nuestro buscador

- **Promesa grande** en la cabecera: *"Auto Parts Around the World"*.
- **Un solo campo: "Part Number or VIN/Frame"** con botón grande de buscar.
- Debajo, **ejemplos clicables**: `8850160190, 4864060010, ...` — enseña qué escribir.
- Dos ayudas: *"How to make order?"* y *"Where is VIN/Frame?"*.
- **Banda de confianza con cifras**: 210.940 clientes / 190 países / 17.000.000 piezas / 2 días
  de despacho promedio.
- **Catálogo por marcas en parrilla de logos** (Toyota, Lexus, Nissan, Infiniti, Mitsubishi…).

## eBay Motors — la referencia para la imagen y la personalización

- Buscador clásico dominando la cabecera.
- **Hero con fotografía real de piezas** y la personalización como acción principal:
  *"Añade tu vehículo a Mi Garaje para encontrar artículos que se ajusten"* + botón.
- **"Compra por categoría" con foto real en cada celda**: llantas, exteriores, interiores,
  iluminación, suspensión, motor, aire y combustible, transmisión, frenos.

## Conclusión: los tres hacen lo que nosotros no

1. **Una promesa grande arriba** (nosotros: tagline de 16 px).
2. **Una sola acción principal** (nosotros: dos tarjetas iguales y dos botones primarios).
3. **Fotografía real de pieza** (nosotros: 33 iconos SVG y **0 fotos** — verificado: 0
   referencias a imágenes de anuncios en el HTML inicial, con 1.190 ofertas que **sí** traen foto).

## Qué integramos, y de dónde

| # | Cambio | De dónde | Por qué |
|---|---|---|---|
| 1 | Ejemplos clicables bajo el campo de búsqueda | Partsouq | Ya aceptamos VIN **o** número; falta enseñar qué escribir. Cambio pequeño, efecto alto |
| 2 | Banda de confianza con cifras **reales** | Partsouq | 28 números verificados, 1.190 ofertas reales, 33 categorías, datos de eBay + vPIC. Solo lo que ya se cumple |
| 3 | **Fotos de pieza** en categorías y resultados | eBay | Tenemos 1.190 anuncios con foto y mostramos iconos |
| 4 | Marcas como **parrilla de logos** | Partsouq | Hoy es un desplegable de **285 opciones** (medido): malo en el teléfono |
| 5 | **Promesa grande** y "añade tu vehículo" como acción hero | eBay + Partsouq | Hoy es un tagline pequeño y la barra de vehículo aparece escondida |
| 6 | Un camino dominante y el otro secundario | los dos | Hoy compiten de igual a igual |

## Qué NO copiamos (criterio, no copia)

- **La densidad extrema de RockAuto**: funciona para su público, pero es su carácter, no el
  nuestro; y en móvil es inservible.
- **Los "17.000.000 de piezas"**: nosotros diremos la verdad —28 números de parte verificados
  contra la API real— porque *"verificado uno por uno contra eBay"* convence más que una cifra
  inflada, y además es la regla del producto: prometer solo lo que ya se cumple.

## Correcciones a mi propio diagnóstico

- El *"No pudimos cargar la lista de marcas"* que se veía en mi captura del móvil **fue un
  artefacto de la captura**, no un fallo del sitio: con un render normal el desplegable trae
  **285 marcas** y no aparece ningún mensaje de error.
- Dije *"no hay una sola imagen"*: impreciso. Hay 33, pero son los iconos de categoría; lo que
  falta es **fotografía de piezas**. La conclusión se mantiene; el dato estaba mal dicho.

---

## Segundo barrido (04/10/2026, noche)

### Autodoc (autodoc.es) — entró; es la referencia del sector en español

- **Barra de promoción** arriba del todo, en rojo, con una oferta y un reloj: *"¡Este otoño sigue
  sumando kilómetros! Hasta un -37 % en comparación con el PVRP"*.
- **Un solo campo de búsqueda**: *"Introduzca el número o el nombre de la pieza"* — acepta número
  **o** nombre, igual que debería hacer el nuestro.
- **Selector de vehículo en 3 pasos numerados**: marca → modelo → tipo de motor. Y además busca
  por **matrícula** (que en Europa es el equivalente práctico a nuestro VIN).
- **Barra de categorías con etiquetas de estado**: *Limpiaparabrisas (Trending)*,
  *Limpieza y Cuidado (New)*, Neumáticos, Herramientas, Aceite de motor, PLUS.
- **Bloque de marca en posición principal**: un banner grande de *RIDEX PLUS — "Mejora tu
  frenada"* con foto de discos. **Es exactamente lo que planteó Omar**: promocionar marcas en
  grande, en el cuerpo de la página.

### MercadoLibre República Dominicana (móvil) — el hábito local

- **Arriba, solo el buscador**: logo + *"Estoy buscando…"* + menú. Nada compite con la búsqueda.
- **Banner de promoción con foto** y una frase: *"¡Encuentra lo que buscas! Hay miles de
  productos publicados, las mejores marcas y los precios más bajos."*
- **Fila de iconos circulares** de categorías (Moda, Vehículos, Inmuebles, Historial, Celulares).
- **Tarjetas con beneficio + botón**: *"Zapatillas — Encuentra el estilo que se adapta a ti"* +
  *Buscar Zapatillas*. Enseñan **para qué sirve** y dan el botón, en vez de solo listar.

### Los que NO se dejaron capturar (barreras antibot, no fallos míos)

| Sitio | Resultado | Nota |
|---|---|---|
| Advance Auto Parts | **0 bytes**, dos intentos | Rechaza el navegador automatizado de plano. **La captura de Omar es la que sirve**, y es justo donde él vio el bloque de marcas |
| Oscaro.es | Página de *"Verificación de seguridad en curso"* de Cloudflare | Identifica el navegador como bot |
| AutoZone | 24 KB (cáscara vacía) | Muro antibot |
| O'Reilly | 25 KB (cáscara vacía) | Muro antibot |

## Canal de marcas (idea de Omar, 04/10/2026)

Omar lo planteó viendo el bloque de marcas de Advance Auto Parts: **promocionar marcas en grande
—aceites, filtros, correas— acercándose a las marcas que se distribuyen en RD aunque sean
extranjeras**. La evidencia lo respalda: Autodoc hace exactamente eso (banner de RIDEX PLUS en
posición principal) y eBay también (hero con personalización).

**Por qué es estratégicamente valioso**: es una **segunda vía de ingreso que no depende de eBay
ni de EPN** — justo lo que falta desde que declinaron la solicitud. No reemplaza la comisión,
la complementa.

**Pero, con la verdad por delante**: las marcas **pagan por audiencia**, y hoy no hay audiencia.
Es Fase 2, igual que el producto B2B: primero el veredicto de tráfico, después la venta de
espacios. Lo que sí se puede hacer **ahora y gratis**:

1. **Dejar el hueco de marca en el diseño** (un bloque visible y con jerarquía, no un rincón).
2. **Que Comercial arme la lista** de marcas distribuidas en RD (aceites, filtros, correas,
   frenos, encendido) y quién las distribuye localmente.
3. **Regla de transparencia, no negociable**: un espacio pagado se muestra **etiquetado como
   publicidad** y **no puede alterar el orden** de las ofertas. Nuestro propio texto legal
   promete que mostramos las mismas ofertas a todos, con o sin comisión; un bloque de marca
   pagado y sin etiquetar contradiría esa promesa y es exactamente el tipo de cosa que después
   se convierte en un problema legal.
