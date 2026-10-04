# eBay en producción: qué falta y en qué orden

Estado al 04/10/2026. Este documento existe porque el cuello de botella de eBay **no es la
cuenta** (ya está aprobada) sino un requisito de cumplimiento que bloquea el keyset de
producción hasta que se resuelve.

## Por qué todavía no hay precios reales en el sitio

`pipeline/fetch_ebay.py` ya implementa el flujo real (OAuth client-credentials + Browse API)
y funciona, pero hoy corre en **modo mock** porque no existen `EBAY_CLIENT_ID` /
`EBAY_CLIENT_SECRET` en el entorno. Sin llaves no puede obtener un token, así que cae al
fixture local. Para precios y URLs reales hacen falta las llaves de **Production**.

## El bloqueo real: Market Account Deletion

eBay no activa ningún keyset de producción hasta que la aplicación cumpla una de estas dos
cosas (es obligatorio, no opcional):

1. **Suscribirse** a las notificaciones de borrado/cierre de cuenta, exponiendo un endpoint
   HTTPS que responda el reto de verificación.
2. **Acogerse a la exención** ("Not persisting eBay data") si la aplicación no guarda datos
   de eBay.

Este proyecto va por la **opción 1**, y la 2 está descartada a propósito: la exención
declara que no se persisten datos de eBay, y nosotros **sí** persistimos resúmenes de
anuncios (título, precio, URL, imagen) en `data/build/parts.json`, que además es público.
Marcar esa casilla sería declarar algo falso para desbloquear las llaves un rato antes.

La opción 1 cuesta un Worker de ~30 líneas (`infra/ebay-notifications/worker.js`), es gratis
y ya está escrito y probado en local.

## Pasos, en orden

| # | Paso | Quién | Estado |
|---|---|---|---|
| 1 | Crear el keyset de **Production** en developer.ebay.com (Application Keys → Create keyset → Production) | Omar (sesión de eBay) | pendiente |
| 2 | Desplegar el Worker y anotar su URL | Omar o el líder | código listo, falta desplegar |
| 3 | Registrar en el portal el *Notification Endpoint URL* + *Verification token* y guardar (eBay valida el reto al instante) | Omar (sesión de eBay) | pendiente, depende de 2 |
| 4 | Con el keyset ya activado, copiar **App ID (Client ID)** y **Cert ID (Client Secret)** | Omar | pendiente |
| 5 | Guardar las llaves en `.env` (local, ignorado por git) y como **GitHub Secrets** | Omar rellena, el líder carga | pendiente |
| 6 | Correr `build-data.yml` y verificar precios reales en el sitio | líder | pendiente |
| 7 | `EBAY_CAMPAIGN_ID` (eBay Partner Network) cuando se pase a monetización | Omar | Fase 3, no urgente — **mecanismo implementado en T-B5 (ver abajo), falta el ID real** |

## T-B5: mecanismo de afiliado (header + itemAffiliateWebUrl), implementado

Queda implementado en `pipeline/fetch_ebay.py` (ver docstring del módulo para el detalle
completo):

- Si existe `EBAY_CAMPAIGN_ID` en el entorno, la búsqueda manda el header
  `X-EBAY-C-ENDUSERCTX: affiliateCampaignId=<id>` (y `affiliateReferenceId=<ref>` si
  además existe `EBAY_REFERENCE_ID`).
- `offers[].url` usa `itemAffiliateWebUrl` cuando eBay lo devuelve, y cae a `itemWebUrl`
  si no (comportamiento de hoy, sin cambios, mientras no haya campaign id).

**Verificado con un campaign id de PRUEBA (inventado, NO un ID real de EPN — `5338800000`,
nunca usar este valor en producción ni publicarlo con tráfico real)**: con ese id, eBay sí
devolvió `itemAffiliateWebUrl` en cada item, con esta forma:

```
https://www.ebay.com/itm/<id>?_skw=...&hash=...&mkevt=1&mkcid=1&mkrid=711-53200-19255-0&campid=5338800000&customid=<EBAY_REFERENCE_ID o vacío>&toolid=10049
```

Es decir: `campid` lleva el campaign id tal cual, y `customid` lleva `EBAY_REFERENCE_ID` si
se mandó (si no, queda vacío). Sin `EBAY_CAMPAIGN_ID` el campo `itemAffiliateWebUrl` no
viene en la respuesta y `offers[].url` sigue siendo la `itemWebUrl` normal, sin ningún
parámetro de tracking — exactamente el comportamiento de antes de T-B5.

**Qué falta**: el campaign ID real de la cuenta de eBay Partner Network de Omar. En cuanto
exista, basta con ponerlo en `EBAY_CAMPAIGN_ID` (`.env` local + GitHub Secret) — no hace
falta tocar código. El fixture de mock (`pipeline/fixtures/ebay_browse_search.sample.json`)
no tiene `itemAffiliateWebUrl` porque se capturó sin campaign id, así que en modo mock el
camino de afiliado no se ejercita por el fixture; sí está cubierto con mocks sintéticos en
`pipeline/tests/test_fetch_ebay.py`.

## Regla de manejo de las llaves (no negociable)

- El **Cert ID es un secreto**: no se pega en el chat, no se commitea, no se imprime en
  pantalla. Va en `.env` (ya ignorado por `.gitignore`) y en GitHub Secrets.
- El `.env` se rellena a mano en el equipo; el líder carga los secretos **desde el archivo**
  (`gh secret set EBAY_CLIENT_ID < ...`), sin mostrar los valores.
- El repo es **público**: los valores no pueden aparecer en ningún archivo versionado ni en
  logs de Actions.

## eBay Partner Network: lo que hay que tener claro antes de aplicar (verificado 04/10/2026)

Se corrige y amplía aquí lo que quedó en `investigacion-ebay-24sep2026.md`, porque dos datos
de esa investigación estaban desactualizados:

1. **El pago NO llega el mes siguiente.** Los *Program Terms* del alta lo detallan: las
   acciones se **bloquean 30 días después del fin del mes** en que se rastrean, y se pagan
   **10 días después de ese bloqueo**. Traducido: una venta de octubre se bloquea a fines de
   noviembre y se cobra **alrededor del 10 de diciembre**. Son ~2 meses desde la venta, no
   uno. Consecuencia práctica: no cuentes con ese dinero para nada hasta bien pasado el
   segundo mes.
2. **Cobrar por PayPal cuesta 2 %** (con tope de 20 USD al mes); por transferencia bancaria
   (direct deposit / EFT) **no hay comisión**. Si el banco lo permite, transferencia.
3. **Umbral mínimo de pago: 10 USD.** Por debajo, se acumula.
4. **Impuestos**: hay que enviar W-9 (si eres de EE.UU.) o **W-8BEN** (fuera de EE.UU., nuestro
   caso) con firma electrónica. Sin eso no hay pago, aunque haya comisiones.
5. **Zona horaria del formulario de alta**: el campo sale bloqueado con un valor por defecto
   (`MST`). No es un bloqueador — afecta el corte de los reportes, no si te pagan. Lo que sí
   está documentado es que la configuración de la cuenta se puede editar después del alta
   (la propia EPN explica cómo actualizar datos de usuario); conviene revisarlo al entrar por
   primera vez y, si sigue trabado, preguntar a soporte.
6. **Impuesto indirecto (ITBIS/IVA)**: si no hay registro fiscal de este negocio, la respuesta
   honesta es *"I am not registered for Indirect Tax"*. Declarar un registro que no existe
   obliga a dar un número que después traba el pago.
7. **Tarifa real de nuestras categorías** (leída en la tarjeta de comisiones del alta,
   04/10/2026): **`Vehicle Parts & Accessories` = 3 % del importe, tope 550 USD por
   artículo**. Las filas de `eBay Motors` y `US Motors` (4 %, tope 100 USD) son las de
   **vehículos completos**, no de piezas — de ahí el tope bajo, para que un coche de 20.000
   USD no pague 800. Con piezas, el tope de 550 no se alcanza nunca (haría falta un artículo
   de 18.333 USD).
8. **Ventana de atribución: 24 horas — confirmada en los Program Terms del alta**
   (*"Attribution Window: allow attribution from clicks within 1 day(s)"*), con **último clic**
   (*"Credit Policy: Last Click"*). Desde el clic, el comprador tiene 24 h para cerrar una
   compra (Buy It Now); en subasta, pujar dentro de esas 24 h y ganarla dentro de 10 días.
   Dato a favor y importante: **no hace falta que compre la pieza que enlazamos** — cualquier
   transacción válida suya en esa ventana cuenta. Las transacciones tardan hasta 48 h en
   aparecer en los reportes. *(Queda descartada la afirmación de un sitio de afiliados de que
   la ventana se había reducido a 12 h: los términos de esta cuenta dicen 1 día.)*
9. **La cuenta honesta, con los precios reales del sitio** (3 %): filtro de aceite de 28 USD
   → **0,84 USD**; pieza de 69,35 USD → **2,08 USD**; las más caras de las nuestras, 129 USD
   → **3,87 USD**. El umbral de pago de 10 USD son ~12 ventas de filtro; **100 USD al mes
   exigen unos 3.300 USD en compras atribuidas** (~50 pedidos de 65 USD). Es un negocio de
   volumen y de tráfico, no de tarifa — y el dinero llega con dos meses de desfase.

## Cómo verificar que quedó bien (sin creerle a la pantalla)

```bash
# token real de 2 h, en un entorno que tenga el .env cargado
python -c "import sys; sys.path.insert(0,'pipeline'); import fetch_ebay as f; \
print('modo REAL' if f.has_real_credentials() else 'modo MOCK'); print(f.search_part('04152YZZA1')[:1])"
```

Debe imprimir `modo REAL` y devolver ofertas con `url` y `price` de eBay reales (no las del
fixture). En el JSON del fixture la URL apunta a `ebay.com/itm/...` con datos de ejemplo —
si los precios parecen de laboratorio, es que siguió en mock.

## Límites de la API, para tenerlos presentes

- Browse API: ~5.000 llamadas/día por defecto (se puede pedir más gratis, *Application
  Growth Check*). El pipeline hace una llamada por número de parte consultado.
- Token de aplicación: válido ~2 h; el módulo pide uno por ejecución del pipeline (no se
  cachea entre procesos, a propósito).
- Si eBay responde 401/429, `search_part()` reintenta y, si no cede, cae a mock para no
  tumbar el pipeline. Es una decisión de diseño ya revisada: mejor datos de ejemplo que
  sitio caído, pero **el modo en que corrió debe quedar visible** (verificar con el comando
  de arriba, no asumir).
