# Legal, privacidad y afiliados

> Estado: **borrador avanzado** (04/10/2026). Falta Fase 3 solo para la parte que depende
> de tener las cuentas reales activas (campaign ID de eBay EPN, de Advance Auto Parts).
> Todo lo demás en este documento ya es verificable contra el código actual del repo.

## 1. Qué recolecta el sitio hoy (verificado contra el código, no una plantilla genérica)

| Dato | Dónde vive | Sale del navegador? |
|---|---|---|
| Vehículo elegido (VIN o marca/año/modelo resuelto) | `localStorage` del navegador (`site/js/vehicleSession.js`) | **No.** Nunca se envía a ningún servidor nuestro — no tenemos servidor propio, el sitio es estático |
| Búsquedas (VIN, número de parte) | No se guarda en ningún lado (ni localStorage ni servidor) | No aplica |
| Analítica / tracking de visitas | **No existe todavía** (verificado: no hay Google Analytics, gtag, ni ningún script de medición en `site/`) | No aplica |
| Cookies propias | **Ninguna** — el sitio no pone cookies | No aplica |

**Lo que esto significa en términos simples**: no hay base de datos de usuarios, no hay
cuentas, no hay nada que un usuario escriba que llegue a nosotros. Todo el estado vive en
su propio navegador y desaparece si borra los datos del sitio.

## 2. Qué pasa cuando el usuario sale del sitio (terceros)

- **eBay**: al hacer clic en una oferta, va a `ebay.com` con la URL real del anuncio
  (`itemWebUrl`, campo que ya devuelve la Browse API). eBay aplica sus propias cookies y
  política de privacidad ahí — no es algo que nosotros controlemos ni recolectemos.
  **Pendiente de Fase 3**: cuando exista el campaign ID de eBay Partner Network, ese link
  pasará a llevar el parámetro de tracking de afiliado (`campid`); hasta entonces el link
  es un enlace normal sin comisión.
- **7zap / Partsouq**: al hacer clic en "Ver diagrama y número en la fuente", va al sitio
  externo correspondiente. Mismo caso: sus propias políticas, no las nuestras.
- **vPIC (NHTSA)**: el navegador del usuario llama directamente a la API pública de vPIC
  (`site/js/vpicClient.js`) para el drill-down marca→año→modelo. Es tráfico
  navegador-a-NHTSA, nunca pasa por nosotros.

## 3. Diagramas y contenido de fábrica (ya decidido, no cambia)

- **Diagramas EPC** (7zap, Partsouq, tiendas oficiales): son dibujos de fábrica con
  derechos de autor. **Nunca se copian ni se re-alojan.** El sitio solo guarda y muestra
  el *deep link* (`epc_link.url`) — el usuario ve el diagrama en el sitio de origen, no en
  el nuestro.
- **Imágenes de producto**: se usan las fotos de los anuncios reales de eBay (vía Browse
  API, campo `image.imageUrl`), enlazadas al anuncio de origen. No se re-alojan ni se
  guardan copias — no hace falta licenciar nada porque no se reproduce nada, solo se
  muestra lo que eBay ya expone públicamente a través de su API.
- **Scraping**: solo permitido en sitios pequeños que lo autoricen explícitamente
  (revisar `robots.txt` y términos antes). Nunca eBay, nunca tiendas grandes, nunca para
  extraer diagramas EPC.

## 4. Aviso de afiliados (texto final, listo para publicar)

Se mostrará de forma visible (footer del sitio y/o junto a cada botón de oferta) en
cuanto exista al menos un programa de afiliados activo (eBay EPN o Advance Auto Parts):

> **Aviso de afiliados**: Este sitio participa en programas de afiliados. Cuando compras
> a través de algunos de los enlaces de esta página, podemos ganar una comisión, sin
> costo adicional para ti. Esto no afecta qué piezas o enlaces te mostramos — mostramos
> las mismas ofertas a todos los usuarios, con o sin comisión.

Checklist de activación (Fase 3, cuando lleguen las cuentas):
- [ ] Insertar el aviso en el footer de `site/index.html` (visible en toda página, no
      solo en la que tiene el botón de compra — es lo que piden la FTC y eBay EPN)
- [ ] Confirmar que `pipeline/fetch_ebay.py` agrega el campaign ID real a las URLs de
      oferta (ver sección "Cómo se enlaza al API" en `PLAN.md`)
- [ ] Mismo aviso aplicado cuando se sume Advance Auto Parts

## 5. Política de privacidad (texto final, listo para publicar)

> **Política de privacidad**
>
> Este sitio no tiene cuentas de usuario, no usa cookies propias y no recolecta datos
> personales en ningún servidor. El vehículo que eliges (por VIN o por marca/año/modelo)
> se guarda únicamente en el almacenamiento local de tu propio navegador (`localStorage`),
> para recordarlo mientras navegas — nunca se envía a nosotros ni a ningún servidor. Puedes
> borrarlo en cualquier momento con el botón "Cambiar vehículo" o limpiando los datos del
> sitio desde tu navegador.
>
> Al buscar tu vehículo sin VIN, tu navegador consulta directamente la base de datos
> pública de vPIC (NHTSA, gobierno de EE. UU.) — esa consulta no pasa por nuestros
> servidores.
>
> Cuando haces clic en un enlace de compra (eBay) o en un enlace a un catálogo de piezas
> (7zap, Partsouq, tiendas de marca), sales de este sitio hacia el sitio externo
> correspondiente, que tiene su propia política de privacidad. Te recomendamos revisarla
> ahí. Algunos de esos enlaces son de afiliado (ver Aviso de afiliados arriba): podemos
> ganar una comisión por tu compra, sin costo adicional para ti.
>
> Este sitio no usa analítica ni herramientas de medición de visitas al día de hoy. Si eso
> cambia en el futuro, esta política se actualizará antes de activarlo.

## 6. Términos de eBay — retención de datos (revisión, verificado contra la doc oficial)

Lo investigado el 24/09/2026 (ver `investigacion-ebay-24sep2026.md`) ya cubre lo esencial:
la Browse API en modo lectura (búsqueda de ítems) no exige aprobación EPN separada ni
tiene restricciones de retención distintas a cualquier integrador — el sitio no guarda
copias de precios/ofertas más allá de lo que `data/build/parts.json` recalcula en cada
`build-data.yml` programado (se sobreescribe, no se acumula histórico). No hay PII de
usuarios de eBay involucrada en ningún punto (no hacemos checkout, no vemos datos de
comprador). **Pendiente formal de Fase 3**: releer los términos completos de la eBay API
License Agreement una vez exista la cuenta de afiliado activa, por si cambia algo
específico de EPN que no aplicaba al uso solo-lectura investigado hasta ahora.

## 7. Lo que falta de verdad para Fase 3 (lo único que depende de las cuentas)

1. Activar el aviso de afiliados en el footer (checklist arriba) cuando exista campaign ID.
2. Confirmar que el link de eBay lleva el parámetro `campid` real.
3. Repetir este mismo ejercicio para Advance Auto Parts cuando se apruebe en Impact.com.
4. Relectura final de términos de eBay ya con la cuenta de afiliado activa (punto 6).

Todo lo demás (secciones 1-5) ya está listo para publicarse tal cual.
