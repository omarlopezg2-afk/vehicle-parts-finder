# Dónde arrancar — PartExact (actualizado 07/10/2026, tras cerrar T-B25)

**Por qué existe este archivo:** la conversación donde se hizo todo esto quedó larguísima, y una
sesión larga trabaja peor (los detalles se diluyen y los descuidos se cuelan). Este es el punto de
arranque para una conversación nueva: pega el bloque de abajo tal cual y la sesión nueva empieza con
el contexto al día sin cargar horas de historial.

---

## Bloque para pegar

```
Trabajamos en PartExact: dar el número exacto de parte para cualquier vehículo y verificar que le
queda. En español.

Repo: ~/Proyectos/piezas-vehiculos/repo (GitHub omarlopezg2-afk/vehicle-parts-finder)
Sitio: partexact.com (GitHub Pages) · Worker en producción: api.partexact.com

Empieza cargando la skill `partexact-vehicle-parts` y leyendo TASKS.md (sobre todo T-B22 a T-B25).

ESTADO VERIFICADO
- Catálogo: 288 vehículos · 2.813 categorías con piezas (todas con foto) · 8.644+ con especificaciones ·
  84.289+ números originales del fabricante. Se sirve PARTIDO:
  data/build/catalogo/index.json + un archivo por vehículo-categoría. El archivo único
  data/build/catalogo.json es producto intermedio y está fuera de git.
- MERCADO DEL CATÁLOGO: 67 = REPÚBLICA DOMINICANA (semilla data/seed/catalogo/vehiculos.json "pais":
  67; monolito "pais_filtro": 67). NO es EE.UU. (261): los documentos que decían 261 estaban
  equivocados y se corrigieron el 07/10/2026. El índice lleva `pais_filtro` y el sitio lo dice.
- MOTORES: las 288 variantes traen la identidad completa (combustible, cilindrada, potencia en PS y
  código de motor). Antes solo 2 de 250: la respuesta que el pipeline ya pagaba traía `fuelType` y no
  se guardaba. Y el 07/10/2026 se añadieron **43 variantes** con criterio (la gasolina de más potencia
  de cada modelo-año), porque la flota se había armado cogiendo los DOS PRIMEROS motores de la API sin
  criterio: 79 modelo-año no tenían el motor que se ve en RD (el Corolla 2016 sin el 1.8, el Hilux sin
  el 4.0 V6). Cuidado con la ronda 2: en 3 modelos esa gasolina "de más potencia" es una serie de
  escaparate (EVO X, Grand Cherokee 6.2, Yaris GR) y el motor común puede seguir faltando.
- Cuarta capa del sitio (T-B25) HECHA y verificada en Chrome headless: etiqueta de mercado + motor +
  combustible encima del bloque, selector de motor cuando hay varios, y ningún número pintado hasta
  que el visitante elige. El motor elegido vive en la URL (.../<slug>/<variante>).
- Worker: vivo y probado (resuelve un Corolla 1992 en 3 consultas; caché en KV; contador del mes).
  Su filtro de país por defecto es ahora RD (67), el del catálogo, y prueba el otro mercado antes de
  decir que un modelo no existe.
- Cuota RapidAPI: quedan ~6.260 de 20.000 este mes (49 en rellenar el combustible + 1.635 en las 43
  variantes). No gastar consultas sin decirlo. El Worker tiene tope propio de 2.000.
- Pruebas: 212 del pipeline · 118 del sitio · 10 del Worker (todas en verde).

LO PRÓXIMO
1. QUE EL VISITANTE PUEDA ELEGIR EL MERCADO. Hoy el sitio DICE el mercado (República Dominicana) pero
   no deja cambiarlo, porque el catálogo precalculado es de un solo mercado. Elegir otro mercado es
   preguntarle a la API por demanda: T-B21 (que el sitio llame al Worker, que ya acepta `?pais=`) +
   T-B23 + T-B26 (el mercado como ORIGEN: Corea con gas adaptado allá, Japón con la guía invertida
   aquí — y vPIC no decodifica un chasis japonés/coreano, así que para esos carros el mercado es la
   única puerta). No prometer un selector de mercado hasta que exista.
2. PINTAR LOS NÚMEROS ORIGINALES DEL VEHÍCULO. `originales.json` (100-190 números del fabricante por
   coche) viaja al sitio y ninguna pantalla lo lee todavía: es el número que el cliente pide en la
   tienda (T-B27).
3. Verificar T-B25/T-B27 contra partexact.com (el deploy copia data/build → site/data/build en CI).
4. Ronda 2 de motores: contrastar el criterio con el registro de la DGII (el actual, "la gasolina de
   más potencia", deja fuera el motor común en los modelos con serie de escaparate).
5. Cuando entren vehículos nuevos al catálogo, `pipeline/completar_variantes.py` para que no nazcan
   sin combustible (con la caché puesta cuesta 0 consultas).

REGLAS QUE NO SE ROMPEN
- Ningún número sin decir de qué mercado, de qué motor y de qué combustible es.
- En español NUNCA se escribe "gas" a secas: en RD significa gasolina y GLP a la vez. "Gasolina" o
  "Gas (GLP)", completos.
- Ninguna pieza inventada ni de ejemplo: antes no mostrar nada que dar un número que no le queda.
- La potencia de TecDoc va en PS y la del VIN (NHTSA) en HP: no son lo mismo (un PS ≈ 0,986 HP).
- El sitio sigue SIN estar para un cliente mientras no esté el mercado elegible y el aviso legal.
```

---

## Comandos útiles (para no buscarlos)

```bash
cd ~/Proyectos/piezas-vehiculos/repo

# pruebas
python3 -m pytest pipeline/tests/ -q                 # 212 del pipeline
(cd site && node --test tests/*.test.js)             # 118 del sitio
(cd workers/autodoc-catalogo && npm test)            # 10 del Worker

# variantes: (a) rellenar el combustible/cilindrada/potencia que falte (GASTA ~1 consulta por pareja
# marca+modelo; con la caché puesta, 0) y (b) añadir los motores que le faltan a la flota con criterio
# (GASTA ~48 por variante; primero en seco, y por lotes para no perder lo bajado si se corta)
python3 pipeline/completar_variantes.py --dry-run    # dice qué falta y cuánto costaría
python3 pipeline/completar_variantes.py
python3 pipeline/agregar_variantes.py --listar       # el plan y su coste, sin gastar nada
python3 pipeline/agregar_variantes.py --ejecutar --lote 8
python3 pipeline/partir_catalogo.py                  # no gasta
python3 pipeline/validate.py

# descargar catálogo de la API (GASTA cuota; respeta --max-consultas)
set -a && . ./.env && set +a
python3 pipeline/fetch_autodoc.py --max-consultas 18000

# Worker
cd workers/autodoc-catalogo && npx wrangler deploy

# vista previa local: copiar el catálogo partido y levantar el servidor
cp -r data/build/catalogo/. site/data/build/catalogo/ && (cd site && python3 -m http.server 8765)

# verificación en navegador (SIN --user-data-dir propio, la segunda corrida sale vacía)
google-chrome --headless=new --disable-gpu --no-sandbox --user-data-dir=/tmp/pv/perfil \
  --virtual-time-budget=14000 --dump-dom "http://localhost:8765/#/vehiculo/Toyota/Corolla/2020/pastillas-freno"
#   -> sale la pregunta "¿Cuál es tu carro exactamente?" y CERO fichas .numero-ficha
#   -> con "/v141203" al final, sale la etiqueta con mercado+motor+combustible y las piezas
```

## Archivos donde está lo que importa

- `TASKS.md` — el tablero. T-B22 (variantes), T-B23 (mercado), T-B24 (gas/GLP), T-B25 (cuarta capa: hecha).
- `site/js/app.js` — el pintado (`renderNumerosDeParte`, `renderPreguntaDeVariante`,
  `renderEtiquetaDeVariante`) y el flujo (`runCategorySelection`).
- `site/js/catalogoMap.js` — traducción de categorías, variantes, combustible, mercado y etiquetas.
- `site/js/dataClient.js` — lo único que lee `data/build` (`entradaDeVariante`,
  `getVariantesDeVehiculo`, `matchVehiculoEnCatalogo`).
- `pipeline/completar_variantes.py` — rellena el combustible/cilindrada/potencia de las variantes.
- `pipeline/fetch_autodoc.py` — el catálogo (con `PresupuestoAgotado` y la alarma anti-cuelgue).
- `workers/autodoc-catalogo/` — el Worker por demanda (KV + tope mensual).
- `docs/` — criterio de flota, la API, el dominio bloqueado, el piloto.
