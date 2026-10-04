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
      "updated_at": "ISO-8601"
    }
  ],
  "updated_at": "ISO-8601"
}
```

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
