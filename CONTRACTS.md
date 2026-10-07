# Contratos de datos

> Congelado por el líder el 25/09/2026. **Ningún agente cambia esto sin aprobación del
> líder.** Si un contrato no te sirve, pide el cambio — no lo improvises en tu rama.

## Normalización de número de parte

- `part_number`: valor original, tal como aparece en la fuente, para **mostrar**.
- `part_number_norm`: mayúsculas, sin espacios, guiones, puntos ni barras, para **buscar**.
  Ejemplo: `04152-YZZA1` → `04152YZZA1`.

## `data/build/parts.json`

Array de objetos. Cada parte:

```json
{
  "id": "string (único, estable, no cambia entre builds)",
  "part_number": "04152-YZZA1",
  "part_number_norm": "04152YZZA1",
  "type": "OEM | AFTERMARKET",
  "brand": "Toyota",
  "name": "Filtro de aceite",
  "category": "filtro-aceite",
  "epc_link": {
    "source": "7zap | partsouq | oem-store | null",
    "url": "string|null"
  },
  "image": {
    "url": "string|null",
    "source": "ebay | generic",
    "credit": "string|null"
  },
  "equivalents": ["id", "id"],
  "fitment_ids": ["id", "id"],
  "other_names": ["string", "string"],
  "offers": [
    {
      "store": "eBay",
      "url": "string (link de afiliado cuando exista campaign id; si no, link normal)",
      "price": 0.0,
      "currency": "USD",
      "condition": "string|null",
      "updated_at": "ISO-8601",
      "image": "string (URL de la foto del anuncio) | null"
    }
  ],
  "updated_at": "ISO-8601"
}
```

**`offers[].image`** (agregado 05/10/2026, T-B6): URL de la foto del anuncio, tal como la
devuelve eBay en `image.imageUrl`. Puede ser `null` (el anuncio no trae foto, o eBay cambió la
forma del campo). Es la foto **de ese anuncio**, no una foto canónica de la pieza: el sitio debe
tratarla como tal. No se descarga ni se re-aloja ninguna imagen (ver `docs/legal.md`), solo se
guarda su URL. El `image` de la parte (arriba) sigue siendo `null`/"generic" hasta que haya una
fuente de imagen canónica (p. ej. el producto del catálogo de eBay por ePID).

**Importante — el campo que preserva el flujo principal del proyecto**: `epc_link` es
obligatorio como clave (puede ir `null` dentro si todavía no se resolvió), porque el
producto es "VIN → ensamblaje → deep link a la fuente del diagrama/número de fábrica", no
solo "ya tengo el número, dame precio". Ningún agente debe quitar este campo ni tratarlo
como opcional/secundario.

**`other_names`** (agregado 04/10/2026, inspirado en el patrón "Other Names" de
factorymitsubishiparts.com/RevolutionParts): lista de sinónimos/nombres alternativos de la
misma pieza (ej. para un clip de parachoques: "Bumper Cover Retainer Clip", "Sight Shield
Clip", "Grille Clip"...). Opcional — puede ser `[]` si no se conocen sinónimos. `searchPart`
en `dataClient.js` debe matchear también contra este campo, no solo contra
`part_number_norm`/`name`, para que alguien que busca "clip de parrilla" encuentre la pieza
aunque el nombre canónico sea otro.

---

## `data/build/catalogo.json` (agregado 07/10/2026, T-B13)

**Opcional**: lo genera `pipeline/fetch_autodoc.py` con la API de AUTODOC (TecDoc) vía RapidAPI,
y es **el archivo que sí da el número de parte**. Si no existe (o no hay `RAPIDAPI_KEY`), la
validación no falla y el sitio simplemente no muestra números.

```json
{
  "generado_en": "ISO-8601",
  "fuente": "AUTODOC Parts Catalog (TecDoc) vía RapidAPI",
  "pais_filtro": 67,
  "incompleto": false,
  "consultas": 27,
  "vehiculos": [
    {
      "etiqueta": "Mitsubishi Outlander Sport 2020 (2.0 gasolina)",
      "vin": "JA4AP4AU3LU023739",
      "vehiculo": { "make": "MITSUBISHI", "model": "Outlander Sport", "year": "2020",
                    "cilindrada_l": 2.0, "potencia_hp": 148.0, "motor": "MIVEC", "valido": true },
      "autodoc": { "manufacturerId": 77, "modelId": 8631, "vehicleId": 126680 },
      "avisos": [],
      "categorias": [
        {
          "nombre": "Disc Brake", "ruta": "Braking System / Disc Brake",
          "buscado": "brake pad", "categoryId": 100027,
          "articulos": [
            { "numero": "D2N097", "marca": "ADVICS", "pieza": "Brake Pad Set, disc brake",
              "articleId": 123456, "foto": "https://...", "tipoFoto": "image/webp" }
          ]
        }
      ]
    }
  ]
}
```

**Reglas que el validador hace cumplir** (y por qué):

1. **Todo artículo con `numero` y `marca` no vacíos.** Un número sin marca no se le puede ofrecer
   a nadie. Mismo espíritu que el `EXACT` de `fitment.json`: mejor no mostrar nada que mostrar
   algo que no se sostiene.
2. **`foto` es `https` o `null`** (nunca una ruta local de una prueba).
3. **Ninguna categoría vacía**: el módulo las descarta; si aparece una, es un fallo del build y
   hay que enterarse ahí, no en el sitio.
4. **`fuente`, `incompleto` y `consultas` presentes**: queda escrito de dónde salió el dato y si
   el presupuesto de consultas se agotó a mitad, para no confundir "no hay piezas" con "no se
   llegó a preguntar".

**La clave NUNCA viaja al frontend.** El sitio es estático: estas llamadas se hacen en el build
(secreto de GitHub Actions) y el navegador solo lee este archivo.

**Coste medido (07/10/2026)**: ~26 consultas por vehículo catalogado (1 del VIN, ~3 de jerarquía,
1 de categorías y ~20 de artículos). El plan gratis son 100 al mes; el de 29 USD, 20.000. Detalle
completo en `docs/piloto-tb10-autodoc.md`.

---

## `data/build/fitment.json` (agregado 05/10/2026, T-B8)

**Opcional**: lo genera `pipeline/fetch_fitment.py` cuando hay credenciales de eBay, y lo
refresca el build programado junto con los demás. Si no existe, la validación no falla.

```json
{
  "updated_at": "ISO-8601",
  "fuente": "eBay Browse API (compatibility_filter, árbol de eBay Motors)",
  "nota_numero_de_parte": "texto que aclara que esta fuente NO da el número de parte",
  "vehiculos": [
    {
      "vehiculo_id": "id de vehicles.json",
      "make": "string", "model": "string", "year": 2020,
      "categorias": [
        {
          "slug": "slug de categories.json (o propio del catálogo)",
          "nombre": "string",
          "category_id": "id de categoría del árbol de eBay Motors (100)",
          "total_en_ebay": 3435,
          "leidos": 200,
          "exactos": 49,
          "ofertas": [
            {
              "titulo": "string",
              "url": "https://www.ebay.com/itm/...",
              "precio": 12.99,
              "moneda": "USD",
              "condicion": "string|null",
              "compatibilidad": "EXACT",
              "foto": "string|null",
              "item_id": "string"
            }
          ]
        }
      ],
      "categorias_con_ofertas": 8,
      "ofertas_totales": 200
    }
  ]
}
```

**Reglas que el validador hace cumplir** (y por qué):

1. **Solo `compatibilidad: "EXACT"`.** La promesa del producto es "esto le queda a tu carro";
   meter un `POSSIBLE` sería mentir con el dato.
2. **Los enlaces tienen que ser de eBay** (`ebay.com/itm/`): evita que un build raro meta datos
   de laboratorio, el mismo tipo de guardián que ya existe para `parts.json`.
3. **`nota_numero_de_parte` es obligatoria y tiene que decir qué NO da esta fuente.** Es la
   constancia escrita de que el número de parte no se obtiene por aquí (ver
   `docs/piloto-tb7.md`), para que nadie lo prometa sin volver a medir.
4. **`error` y ofertas son excluyentes** en una categoría: si la API falló, va el error y no
   hay ofertas que mostrar.

**Cobertura medida (05/10/2026)**: funciona en modelos del mercado estadounidense y en los que
los vendedores cubren globalmente (el Hilux dio 47 compatibilidades EXACT); **no** hay datos
para modelos exclusivos de otros mercados (un Corolla Axio japonés dio 0). Antes de añadir
vehículos, comprobarlos con el mismo método.

## `data/build/vehicles.json`

Array de objetos, uno por combinación vehículo resuelta vía vPIC:

```json
{ "id": "string (único)", "make": "Mitsubishi", "model": "Outlander Sport", "year": 2020,
  "trim": "string|null", "engine": "string|null" }
```

## `data/build/search_index.json`

Índice liviano para búsqueda en el navegador (sin precios ni links, solo lo necesario para
filtrar rápido en el cliente):

```json
{ "id": "string", "part_number_norm": "string", "name": "string", "brand": "string" }
```

## `data/build/categories.json`

```json
{ "slug": "filtro-aceite", "name_es": "Filtro de aceite", "svg": "filtro-aceite.svg",
  "group_slug": "mantenimiento", "group_name_es": "Mantenimiento" }
```

**Catálogo de categorías: congelado en `docs/taxonomia-categorias.md`** (04/10/2026, Ronda 4).
Ese documento es la lista exacta de slugs, nombres, grupos y archivo SVG de cada categoría, y
las reglas de inclusión. El esquema de arriba **no cambia**; lo que se congela es el
contenido. Todo slug que exista en `categories.json` debe tener: su fila en ese documento, su
archivo SVG en `site/assets/categories/` y (salvo pendiente declarado) al menos una parte real
en el seed. **Un slug nunca se renombra una vez publicado**, porque es la clave que referencian
`parts.json.category` y `search_index.json`.

**Jerarquía de 2 niveles** (agregado 04/10/2026, inspirado en la taxonomía estándar de la
industria — sistema → pieza — que usan catálogos grandes como RockAuto; es terminología
genérica del sector, no contenido propietario de nadie). `group_slug`/`group_name_es` son
**obligatorios** desde ahora (todo slug pertenece a un grupo), pero es un cambio
**retrocompatible**: el campo `category` en `parts.json` sigue apuntando al slug HOJA
(ej. `"pastillas-freno"`), nunca al grupo — así que nada que ya lea `parts.json.category`
se rompe. Solo `categoryTree.js` necesita aprender a agrupar visualmente por `group_slug`
antes de mostrar los slugs hoja. Grupos sugeridos de partida (el agente que implemente
puede ajustar nombres, pero mantener el mismo *tipo* de agrupación): Frenos, Motor,
Eléctrico, Suspensión y dirección, Refrigeración, Mantenimiento, Carrocería y exterior,
Interior, Iluminación.

## Regla de escalado (no negociable sin pasar por el líder)

El frontend **solo** lee datos a través de `site/js/dataClient.js`, con esta superficie:

- `searchPart(q)` — por `part_number_norm` o texto libre.
- `getPart(id)`
- `getVehicles()`

Si el catálogo crece y hay que migrar a Supabase (u otra base), **solo cambia ese módulo**.
Ningún otro archivo de `site/` debe hacer fetch directo a `data/build/*.json`.

## Reglas transversales (aplican a todos los agentes)

1. Nunca commitear llaves, tokens ni secretos. Van en GitHub Secrets (Actions) o en un
   `.env` local ignorado por git.
2. Nunca re-alojar ni copiar diagramas de catálogos EPC (7zap, Partsouq, tiendas oficiales):
   son dibujos de fábrica con derechos. Solo se guarda el **deep link** (`epc_link.url`).
3. Scraping solo permitido para precio/equivalencias de sitios pequeños que lo autoricen
   (robots.txt + términos revisados). Nunca eBay, nunca tiendas grandes, nunca diagramas EPC.
4. Todo texto de cara al usuario en español.
5. Cada entrega indica: qué se hizo, cómo probarlo, supuestos y problemas conocidos.
