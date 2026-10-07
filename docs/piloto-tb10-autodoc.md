# Piloto T-B10 — la prueba gratis de la API de catálogo de AUTODOC

**Decidido el 06/10/2026**: antes de pagar nada, se gasta el plan **gratis (100 consultas)** y se
mira qué dato devuelve de verdad.

**ESTADO: EJECUTADO el 07/10/2026.** 29 de 100 consultas usadas. Resultado: **la API sirve** — ver
la sección RESULTADO más abajo. Queda pendiente la decisión del usuario de pasar al plan de 29 USD/mes.

## Por qué esta prueba decide tanto

El usuario lo dijo claro y tiene razón: *"lo que necesita el sitio es dar el número de parte"*.
La ruta que llevábamos (recolectar catálogos, licencias, autorizaciones, ACES/PIES) es meses de
trabajo. Esta API es un atajo con precio público: **29 USD/mes por 20.000 consultas**, con
vehículo → piezas numeradas, referencias cruzadas OEM/aftermarket, diagramas y fotos. Lo único que
falta comprobar antes de pagar es si su catálogo **sirve para vehículos del mercado estadounidense**
(AUTODOC es europeo y nuestros vehículos son americanos).

## Lo que hay que tener listo

- Clave de RapidAPI en `.env` (el hueco **ya está reservado**: `RAPIDAPI_KEY=`). Nunca en el chat,
  nunca en el repo.
- Cuenta de RapidAPI suscrita al plan **Basic (0 USD)** de *Autodoc Parts Catalog*.

## La prueba, en concreto

**Vehículos a consultar** (a propósito, con control): dos del mercado estadounidense —**Mitsubishi
Outlander Sport 2020** (el del usuario, que ya sabemos que es `JA4AP4AU3LU023739`) y **Toyota
Corolla 2019**— y **un europeo como control** (por ejemplo un **VW Golf 2016**). Si responde igual
de bien a los americanos que al europeo, el catálogo es global y la duda queda cerrada; si solo
responde al europeo, es un catálogo europeo y la vía se cierra **antes** de pagar.

**Qué hay que averiguar, en este orden** (cada respuesta puede matar la idea, así que van de la más
decisiva a la menos):

1. **¿Cómo identifica los vehículos?** ¿Se puede entrar por marca/modelo/año, o exige un ID interno
   suyo? Si exige IDs propios, hay que ver cómo se obtienen: eso añade un mapeo desde
   año/marca/modelo y es trabajo real.
2. **¿Devuelve el número de parte** con su marca, para un vehículo americano?
3. **¿La referencia cruzada** (`Parts Cross Reference`) conecta el número OEM con los equivalentes
   de otras marcas? Es la pieza que convierte esto en *"el número exacto"*.
4. **¿Qué categorías cubre?** ¿Tiene frenos, limpiaparabrisas, filtros, bujías, amortiguadores?
5. **¿El plan gratis incluye todos los endpoints** o restringe algunos? (En RapidAPI cada plan suele
   limitar endpoints concretos; hay que verlo antes de dar la prueba por buena.)
6. **Forma de la respuesta**: ¿el JSON trae el número limpio como campo propio, o hay que sacarlo del
   texto como pasa con eBay?

**Presupuesto de consultas**: 100 disponibles; la prueba completa son unas **20** (3 vehículos ×
identificación + 3 categorías + 2 detalles, más el control). Sobra margen para repetir algo.


## RESULTADO (07/10/2026) — probado con la clave real. Se gastaron 29 de las 100 consultas gratis

**El criterio de decisión escrito arriba (antes de ver nada) se cumple.** Las seis preguntas,
respondidas con datos reales:

1. **¿Cómo identifica los vehículos?** Híbrido. Decodifica el VIN por su cuenta
   (`/api/vin/decoder-v5/{vin}` -> HTTP 200 con la ficha completa del vehículo) **pero para llegar a
   las piezas hay que resolver su jerarquía TecDoc**: fabricante -> modelo -> variante
   (`vehicleId`) -> categoría -> artículos. El mapeo es directo.
2. **¿Devuelve el número de parte?** Sí, y como campo propio:
   `{"vehicleId":"126680","categoryId":"100027","countArticles":10,"articles":[{"articleNo":"ADBP450211","supplierName":"BLUE PRINT","articleProductName":"Brake Caliper","s3image":"https://..."}]}`
   — número, marca, nombre de la pieza y **foto**.
3. **¿La referencia cruzada?** Sí, y probada con un número de nuestro propio catálogo:
   `04152YZZA1` (Toyota) devuelve `articleNo: 20-50517-SX` **más los otros OEM**
   (`04152-0V010`, `04152-31050`).
4. **¿Categorías?** El árbol TecDoc completo de ese vehículo (396 nodos con jerarquía
   `categoryId1..4`: frenos, aire acondicionado, accesorios...).
5. **¿El plan gratis restringe endpoints?** No se topó con ninguna restricción en 29 consultas
   (idiomas, países, VIN, fabricantes, modelos, variantes, categorías, artículos y OEM).
6. **¿El número viene limpio?** Sí: `articleNo` es un campo propio. No hay que sacarlo del texto
   como pasa con la Browse API de eBay.

**El mercado americano está cubierto**: el Outlander Sport del usuario está en el catálogo
(`modelId 8631`, 30 variantes), y la del motor que dice su VIN (2.0, **148 HP**, código 4B11,
1998 cc, gasolina) existe como `vehicleId 126680`. Detalle revelador: **el mismo modelo se llama
`OUTLANDER SPORT` con el filtro de EE.UU. y `ASX` con el de República Dominicana** — el filtro de
país cambia el nombre comercial, y RD está en la lista (`id 67`) igual que EE.UU. (`id 261`).

**Arquitectura (crítico)**: la clave **nunca** puede viajar al frontend. El pipeline la usa como
secreto en GitHub Actions y el sitio sigue sirviendo JSON estático — exactamente como hace hoy con
el fitment de T-B8.

**Coste real medido**: ~26 consultas por vehículo catalogado (1 del VIN + 3 de jerarquía + 1 de
variantes + 1 de categorías + ~20 de artículos). Con el plan de 29 USD (20.000 consultas) salen
**unos 770 vehículos al mes** con catálogo completo; con caché por (vehicleId, categoryId), más.

## Criterio de decisión (escrito antes de ver el resultado, para no engañarnos después)

- **Si devuelve números para los dos americanos** → se pasa al plan de 29 USD y el producto cambia:
  el sitio pasa de *"te digo qué le queda"* a **"te doy el número, sus equivalencias y a quién le
  queda"**. Eso reemplaza T-B11 y buena parte de los frentes de catálogo abiertos.
- **Si solo cubre europeos** → se cierra la vía y se sigue con lo que ya funciona (fitment de eBay
  T-B8 + el VIN de T-B9), sin gastar un dólar.
- **Si devuelve números pero exige IDs propios difíciles de mapear** → se mide cuánto cuesta el mapeo
  antes de decidir; no se paga hasta saberlo.

## Cómo se ejecuta el día que toque

Con la clave en `.env`: una sola tanda de llamadas desde un script (como se hizo con el sandbox de
eBay) que imprime los resultados **sin exponer la clave**, o directamente en la consola de RapidAPI
(el *Test Endpoint*), que muestra la respuesta sin escribir código. Cualquiera de las dos sirve; la
segunda es más rápida para la primera mirada.
