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
