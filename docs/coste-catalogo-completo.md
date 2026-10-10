# Cuánto cuesta cubrir el catálogo completo

> Medido el **10-oct-2026** sobre los artefactos en disco del catálogo congelado (290 vehículos,
> 13.899 consultas). **Sustituye a la estimación de 9 consultas por vehículo** de
> `docs/catalogo-requisitos-y-precios.md`, que se quedaba corta **5,3 veces** — todo cálculo hecho
> con aquel número está mal por ese factor.

## Lo medido (no estimado)

| Dato | Valor | De dónde sale |
|---|---|---|
| Consultas por vehículo (corrida real) | **47,9** | 13.899 consultas ÷ 290 vehículos |
| Categorías por vehículo | **10** | `data/build/catalogo/index.json` (`categorias`, máximo 10) |
| Piezas por vehículo en esas 10 categorías | **2.745** | 795.998 apariciones de `articleId` ÷ 290 |
| **Reutilización de artículos** | **12,44×** | 795.998 apariciones → **63.969 distintos** |

Ese último es el dato que decide el precio: el `articleId` de TecDoc es **global**, así que la misma
pastilla sirve a decenas de variantes y **el detalle se paga una vez por artículo, no una vez por
vehículo**. Sin contarlo, el cálculo sale unas doce veces más caro.

## Cómo se compone el coste

- **La lista de una categoría devuelve TODAS sus piezas con su número, en 1 consulta.** De ahí que
  los números sean baratos.
- **`Article Details`** (posición de montaje, medida, número original): **1 por artículo**.
- **`Parts Cross Reference`** (original ↔ equivalentes de otras marcas): **1 más por artículo**.
- Resolver la variante y su árbol de categorías: 1-3 por vehículo, y se cachea.

## El defecto de cobertura, explicado

Se pidieron **10 categorías** por vehículo; un despiece de turismo tiene **~40-70** grupos. Diez sobre
cincuenta es el **~20 %**: no faltaban piezas de esas categorías, faltaban **categorías enteras**.

## El total en dólares

Escalera de planes (medida el 05-oct en RapidAPI): **Pro 29 USD / 20.000 · Ultra 59 / 100.000 ·
Mega 299 / 1.000.000**. Combinar planes de distinto tamaño es más barato que uno solo.

Parque de las **8 marcas principales — 81 % del parque, ~2.850 variantes**:

| Alcance | Consultas | Compra | **USD** |
|---|---|---|---|
| Números de TODAS las categorías | 153.900 | 2 × Ultra | **118** |
| + ficha exacta de cada pieza (posición, medida, original) | 3.297.409 | 3×Mega + 3×Ultra | **1.074** |
| + equivalencias cruzadas | 6.440.919 | 6×Mega + 5×Ultra | **2.089** |
| Pesimista (si la reutilización fuera 3× y no 12,44×) | 26,2 M | meses de Mega | **7.950** |

Parque de las **4 marcas principales — 62 %, ~1.500 variantes**: **59 / 598 / 1.133 USD**
(pesimista 4.186).

Y dos cifras sueltas que importan:

- **Censo del árbol de categorías** de las 2.850 variantes (2 consultas cada una): 5.700 consultas →
  **29 USD**, un mes de Pro. Convierte el «~50 categorías» en un número exacto antes de comprar.
- **Sostenimiento por demanda**: 29 USD/mes (~348 al año), pagando el detalle solo de lo que la gente
  pida de verdad.

## Qué hacer, en orden

1. **El censo primero** (29 USD): medir el árbol real de categorías antes de firmar nada.
2. **Pedir cotización de volcado completo al proveedor** antes de gastar dos mil dólares en 6,4
   millones de llamadas. A ese volumen un export negociado suele salir más barato y de una vez.
3. **Comprar por orden de valor**: primero todos los números (118 USD) — que ya arregla el 20 % — y
   después el detalle **empezando por lo más pedido**, que es exactamente el Worker de demanda.
4. **Alojamiento**: 3-6 M de artículos no caben en GitHub Pages; el catálogo partido por
   vehículo-categoría que ya usamos + un almacén tipo Cloudflare R2 cuesta céntimos al mes. Es
   dinero, no ingeniería: ni el pipeline ni el Worker se tocan.

## El techo honesto de esta fuente

Con AUTODOC, «100 %» significa **el 100 % de lo que el mercado de repuesto vende** — su árbol de
categorías *es* la lista de piezas comercializadas, que es justo lo que el producto promete
(posición, medida y número original). El despiece completo del concesionario, con cada tornillo y
cada grapa, es otro proveedor y otros precios: datos de referencia del orden de 1.000-2.500 USD al
año, y plataformas OEM de 15.000 a 60.000 USD al año.

## Cómo volver a medirlo sin gastar una sola consulta

```bash
cd ~/Proyectos/piezas-vehiculos/repo
python3 -c "import json;d=json.load(open('data/build/catalogo/index.json'));print(d['consultas'],len(d['vehiculos']))"
grep -oE '"articleId"\s*:\s*"?[A-Za-z0-9_-]+' data/build/catalogo.json | wc -l   # apariciones
grep -oE '"articleId"\s*:\s*"?[A-Za-z0-9_-]+' data/build/catalogo.json | sed -E 's/.*[:"]\s*//' | sort -u | wc -l   # distintos
```
