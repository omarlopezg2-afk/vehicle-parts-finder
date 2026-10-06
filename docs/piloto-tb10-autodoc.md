# Piloto T-B10 — la prueba gratis de la API de catálogo de AUTODOC

**Decidido el 06/10/2026**: antes de pagar nada, se gasta el plan **gratis (100 consultas)** y se
mira qué dato devuelve de verdad. **No se ejecuta todavía**: lo dispara el usuario cuando diga.

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
