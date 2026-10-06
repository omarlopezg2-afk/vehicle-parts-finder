# Piloto T-B7 — ¿se puede conseguir el número exacto de parte? (05/10/2026)

**Pregunta**: el usuario quiere una página donde encuentre cualquier pieza de cualquier
vehículo, obtenga **el número exacto** y un enlace de compra. ¿Se puede, con las llaves que
tenemos y sin pagar datos?

**Método**: consultas reales a la API de eBay con el vehículo real del usuario
(**2020 Mitsubishi Outlander Sport**), midiendo cada paso. Nada de deducciones: cada
afirmación de aquí abajo salió de una llamada de verdad (≈40 llamadas de la cuota, de ~5.000/día).

## Lo que SÍ se obtuvo (y es mucho)

`compatibility_filter` funciona, gratis, con nuestras llaves. Poniendo el vehículo concreto
(`Year:2020;Make:Mitsubishi;Model:Outlander Sport`) y una categoría de pieza del catálogo de
**eBay Motors** (árbol 100), la búsqueda devuelve los anuncios **que le quedan a ese carro**,
cada uno con:

- `compatibilityMatch: "EXACT"` (o `POSSIBLE`) — el grado de compatibilidad, por anuncio
- `compatibilityProperties`: `Year: 2020`, `Make: Mitsubishi`, `Model: ...`
- foto (`image` + `thumbnailImages` + `additionalImages`), precio, condición, vendedor y envío

Medido por categoría (50 anuncios leídos en cada una):

| Categoría (id de eBay Motors) | Resultados | Compatibilidad EXACT | Con foto |
|---|---:|---:|---:|
| Limpiaparabrisas (179852) | 3.446 | **50/50** | 50/50 |
| Filtro de aire (33659) | 657 | 48/50 | 50/50 |
| Amortiguadores (33590) | 657 | 46/50 | 50/50 |
| Radiador (33602) | 1.041 | 36/50 | 49/50 |
| Frenos (33559) | 3.544 | (5/5 en la prueba inicial, todos EXACT) | — |

O sea: **el fitment se consigue de verdad, gratis y a escala.** Y la categoría **tiene que
pertenecer al árbol de eBay Motors**: con las categorías genéricas de EBAY_US la API responde
*"This category ID does not support fitment"*. El árbol de Motors es el **100**.

## Lo que NO se obtuvo: el número de parte

Se probaron las tres puertas que existen, y las tres están cerradas:

| Puerta | Resultado |
|---|---|
| `fieldgroups=EXTENDED` en la búsqueda | Añade `shortDescription` y la ciudad. **No** añade `product` ni `mpn` |
| `getItem` del anuncio (`PRODUCT` y `COMPACT`) | **No** trae `product`, ni `mpn`, ni `brand`. Tampoco la compatibilidad |
| API de catálogo por `epid` (`commerce/catalog/v1_beta/product/…`) | **HTTP 403**: *"Insufficient permissions to fulfill the request"* — puerta cerrada para nuestras llaves |

Y del título del anuncio solo se puede *adivinar* un número en una fracción de los casos:
**13 de 50** en filtros de aire, **7 de 50** en radiadores, **4 de 50** en limpiaparabrisas y
**0 de 50** en amortiguadores (que son kits, sin número). Un número adivinado que salga mal es
peor que no darlo: manda al cliente a comprar la pieza equivocada, que es justo lo que el
producto existe para evitar.

## La puerta del número, probada en los dos entornos (05/10/2026)

Las llaves de sandbox se consiguen (hay que generarlas aparte en el portal, y se distinguen
porque el **App ID lleva `SBX`** en el segmento del medio; el de producción lleva `PRD`).
Con ellas, en **sandbox**:

| Prueba | Resultado |
|---|---|
| Token de sandbox | **OK** (expira en 7.200 s) — las llaves funcionan |
| Browse API en sandbox (control) | **HTTP 200**, devuelve anuncios |
| **Catalog API: búsqueda de producto** | **HTTP 403 — "Insufficient permissions"** |
| **Catalog API: producto por epid** | **HTTP 403 — "Insufficient permissions"** |

Es decir: **la Catalog API está cerrada para nuestra aplicación en los dos entornos**, no solo
en producción. No es un problema de llaves ni de configuración: es un permiso que nuestra app
no tiene y que la documentación describe como *Limited Release, solo para desarrolladores
selectos aprobados por unidades de negocio*. La nota de que "cualquiera puede usar las APIs en
sandbox" aplica a las **Buy APIs**, no a esta, que es del grupo **Commerce**.

**Consecuencia**: el número de parte vía eBay queda descartado por las dos vías (el campo no
existe en los anuncios, y el catálogo que lo tiene está cerrado). El camino al número sigue
siendo el diagrama oficial a un clic. La pregunta para soporte de eBay ahora es mucho más
precisa: *"en sandbox también devuelve 403; ¿cuál es el proceso de aprobación?"*.

## Conclusión: qué prometemos y qué no

**No podemos prometer "el número exacto".** Ese dato vive en un catálogo licenciado (que es
exactamente lo que iMotriz compró y por eso lo cobra) y nuestras llaves no lo alcanzan.

**Sí podemos prometer, con dato real y gratis**: *"esto es lo que le queda exacto a tu carro,
con su precio real y su foto"* — y, para el número, **el diagrama oficial a un clic**
(`epc_link`, que ya existe en el contrato del proyecto). O sea:

> El número lo confirmas tú en el diagrama (un clic); nosotros te decimos qué le queda y a
> qué precio.

Eso no es un consuelo: es un producto distinto y más honesto que el de la competencia, y es el
único que podemos sostener con lo que tenemos. Además encaja con la regla del proyecto:
**prometer solo lo que ya se cumple.**

## Lo que cambia en el plan

El catálogo no debe construirse persiguiendo números de parte, sino **emparejando vehículos con
categorías**: por cada vehículo × categoría de Motors, una llamada devuelve cientos de anuncios
que le quedan EXACTO. Con ~5.000 llamadas/día se cubre un catálogo enorme sin gastar un céntimo.
Lo que falta es el trabajo de deduplicar y ordenar esa oferta, no de obtener el dato.
