# AGENTS.md — PartExact (leer antes de tocar nada)

Proyecto de Omar López (omarlopezg2-afk). **Qué es:** dar **el número exacto de la pieza** de un
vehículo y **verificar que le queda** — sin inventar nunca un número. Multimarca, gratis para el
usuario, mercado principal República Dominicana.

**Antes de trabajar, lee `docs/TRASPASO.md`** (traspaso completo: estado verificado, siguientes pasos
con su coste en consultas, cómo se verifica y las trampas que ya costaron tiempo) **y `TASKS.md`**
(el tablero; lo último es T-B22 → T-B27).

Repo: `~/Proyectos/piezas-vehiculos/repo` (privado, `github.com/omarlopezg2-afk/vehicle-parts-finder`).
Sitio en producción: **partexact.com** (GitHub Pages). Worker: **api.partexact.com**. Empujar a `main`
dispara CI + deploy (el deploy copia `data/build/` a `site/data/build/` y publica).

## Las reglas que no se rompen (y el porqué, para no "mejorarlas" hasta convertirlas en mentira)

1. **Ningún número sin decir de qué MERCADO, de qué MOTOR y de qué COMBUSTIBLE es.** Los tres datos van
   con el número. El catálogo va por variante (`vehicleId`) y **123 de 127 modelo-año tienen más de un
   motor**: un número exacto para el motor equivocado es peor que no dar número.
2. **Ninguna pieza inventada, ni de ejemplo, ni "probablemente sirve".** Si el dato no está, no se
   muestra. `catalogo.json` **no tiene fixture a propósito**: un catálogo de mentira enseñaría números
   falsos a un cliente y eso rompe la única promesa del producto.
3. **Nunca "gas" a secas.** En RD significa gasolina *y* GLP a la vez. Siempre "Gasolina" o "Gas (GLP)",
   completos.
4. **No se gasta cuota sin decirlo antes.** RapidAPI tiene 20.000 consultas/mes. Primero en seco
   (`--dry-run` / `--listar`), luego se dice el coste y se espera el OK. El acumulado del catálogo se
   puede bajar a 0 consultas cuando el dato ya está en `data/raw/` (caché).
5. **Prometer solo lo que ya se cumple.** Si algo no se cumple, se quita de la promesa (landing, ficha,
   textos, vídeos) y queda como pendiente. Mejor prometer menos e ir mejorando.
6. **El mercado del catálogo es RD (`pais_filtro: 67`), NO EE.UU. (261).** Lo dicen la semilla
   (`data/seed/catalogo/vehiculos.json`, `"pais": 67`) y el monolito. Antes de etiquetar un mercado, se
   lee el artefacto; no la documentación ni la memoria de nadie.
7. **La unidad del catálogo es la variante (`vehicleId`), no el modelo-año.**
8. **El monolito `data/build/catalogo.json` es producto intermedio y está fuera de git** (cientos de MB).
   A git va la versión partida: `data/build/catalogo/index.json` + un archivo por vehículo-categoría.
9. **La clave de RapidAPI (`RAPIDAPI_KEY`) nunca se imprime ni se commitea**, ni en logs ni en mensajes
   de commit. El pipeline la lee del entorno o del `.env` (ignorado por git).

## Comandos

```bash
cd ~/Proyectos/piezas-vehiculos/repo

# pruebas (las tres suites; hoy: 216 + 149 + 21 en verde)
python3 -m pytest pipeline/tests/ -q
(cd site && node --test tests/*.test.js)
(cd workers/autodoc-catalogo && npm test)

# datos: primero en seco, y solo después se gasta
python3 pipeline/completar_variantes.py --dry-run       # rellenar identidad de variantes (¿cuánto falta?)
python3 pipeline/agregar_variantes.py --listar          # añadir motores que faltan: plan y coste, 0 consultas
python3 pipeline/agregar_variantes.py --ejecutar --lote 8
python3 pipeline/partir_catalogo.py                     # parte el monolito para el sitio (0 consultas)
python3 pipeline/validate.py                            # valida los JSON contra CONTRACTS.md

# ver el sitio en local (el catálogo partido hay que copiarlo: el workflow lo hace en CI)
cp -r data/build/catalogo/. site/data/build/catalogo/ && (cd site && python3 -m http.server 8765)

# verificación en navegador (sin --user-data-dir propio, la SEGUNDA corrida sale vacía)
google-chrome --headless=new --disable-gpu --no-sandbox --user-data-dir=/tmp/pv/x \
  --virtual-time-budget=14000 --dump-dom \
  "http://localhost:8765/#/vehiculo/Toyota/Corolla/2016/pastillas-freno"

# Worker (por demanda, con caché KV y tope propio de 2.000/mes)
cd workers/autodoc-catalogo && npx wrangler deploy
```

## Cómo se comprueba que un número le queda (esto es la verificación del producto)

Con el Corolla 2016 del catálogo real, en local o en partexact.com:

| URL | Qué tiene que salir |
|---|---|
| `#/vehiculo/Toyota/Corolla/2016/pastillas-freno` | La pregunta **"¿Cuál es tu carro exactamente?"** con los tres motores (1.8 / 1.3 / 1.4 D) y **CERO** fichas `.numero-ficha`: sin saber el motor no se enseña ningún número |
| `…/pastillas-freno/v109621` (el 1.8) | `Mercado: República Dominicana · Motor: 1.8 L · 151 PS · Gasolina · 2ZR-FE · Combustible: Gasolina` + 3 números de pastilla |
| `…/pastillas-freno/v52438` (el 1.3) | Su etiqueta con **1.3 L · 99 PS · Gasolina · 1NR-FE** y **números distintos** de los del 1.8 |

Si los dos motores dieran la misma lista, algo está mal (el motor no estaría filtrando). Eso ya pasó:
ver T-B22 en `TASKS.md`.

## Estado en una línea (07/10/2026)

290 vehículos · 2.833 categorías con piezas · índice partido de ~840 KB · 250/250→290/290 variantes con
combustible, cilindrada, potencia y código de motor · cuarta capa del sitio (mercado+motor+combustible)
hecha y verificada en local y en partexact.com · 216 + 149 + 21 pruebas en verde · quedan ~6.100
consultas RapidAPI este mes (el número exacto, en el panel de RapidAPI).
