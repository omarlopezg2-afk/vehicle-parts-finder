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
- Catálogo: 250 vehículos · 2.467 categorías con piezas · 631.797 piezas (todas con foto) · 8.644 con
  especificaciones · 84.289 números originales del fabricante. Se sirve PARTIDO:
  data/build/catalogo/index.json + un archivo por vehículo-categoría. El archivo único
  data/build/catalogo.json es producto intermedio y está fuera de git.
- MERCADO DEL CATÁLOGO: 67 = REPÚBLICA DOMINICANA (semilla data/seed/catalogo/vehiculos.json "pais":
  67; monolito "pais_filtro": 67). NO es EE.UU. (261): los documentos que decían 261 estaban
  equivocados y se corrigieron el 07/10/2026. El índice lleva `pais_filtro` y el sitio lo dice.
- COMBUSTIBLE: las 250 variantes lo tienen (Gasolina 190, Diésel 49, Híbrido 5, Etanol 2,
  Gasolina/GLP 1, Diésel/Eléctrico 1), con cilindrada, potencia en PS y código de motor. Antes solo
  lo tenían 2 de 250: la respuesta que el pipeline ya pagaba traía `fuelType` y no se guardaba.
- Cuarta capa del sitio (T-B25) HECHA y verificada en Chrome headless: etiqueta de mercado + motor +
  combustible encima del bloque, selector de motor cuando hay varios, y ningún número pintado hasta
  que el visitante elige. El motor elegido vive en la URL (.../<slug>/<variante>).
- Worker: vivo y probado (resuelve un Corolla 1992 en 3 consultas; caché en KV; contador del mes).
  Su filtro de país por defecto es EE.UU. (261) y prueba el otro mercado antes de decir que un modelo
  no existe. OJO: el catálogo precalculado es 67, así que un número precalculado y uno del Worker
  pueden venir de mercados distintos: hay que decirlo siempre.
- Cuota RapidAPI: quedan ~7.900 de 20.000 este mes (49 se gastaron en rellenar el combustible).
  No gastar consultas sin decirlo. El Worker tiene tope propio de 2.000.
- Pruebas: 195 del pipeline · 118 del sitio · 8 del Worker (todas en verde).

LO PRÓXIMO
1. QUE EL VISITANTE PUEDA ELEGIR EL MERCADO. Hoy el sitio DICE el mercado (República Dominicana) pero
   no deja cambiarlo, porque el catálogo precalculado es de un solo mercado. Elegir otro mercado es
   preguntarle a la API por demanda: T-B21 (que el sitio llame al Worker, que ya acepta `?pais=`) +
   T-B23. No prometer un selector de mercado hasta que exista.
2. Verificar T-B25 contra partexact.com (el deploy copia data/build → site/data/build en CI).
3. Cuando entren vehículos nuevos al catálogo, correr `pipeline/completar_variantes.py` para que no
   vuelvan a nacer sin combustible (con la caché puesta cuesta 0 consultas).

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
python3 -m pytest pipeline/tests/ -q                 # 195 del pipeline
(cd site && node --test tests/*.test.js)             # 118 del sitio
(cd workers/autodoc-catalogo && npm test)            # 8 del Worker

# variantes: rellenar combustible/cilindrada/potencia (GASTA ~1 consulta por pareja marca+modelo;
# con la caché puesta, 0) y luego partir para el sitio (no gasta)
python3 pipeline/completar_variantes.py --dry-run    # dice qué falta y cuánto costaría
python3 pipeline/completar_variantes.py
python3 pipeline/partir_catalogo.py
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
