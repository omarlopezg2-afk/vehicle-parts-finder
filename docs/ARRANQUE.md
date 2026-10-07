# Dónde arrancar — PartExact (actualizado 07/10/2026)

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
- Worker: vivo y probado (resuelve un Corolla 1992 en 3 consultas; caché en KV; contador del mes).
  Su filtro de país por defecto es EE.UU. (261), igual que el catálogo, y prueba el otro mercado
  antes de decir que un modelo no existe.
- Cuota RapidAPI: ~12.070 de 20.000 usadas este mes. El Worker tiene tope propio de 2.000.
  No gastar consultas sin decirlo.
- Pruebas: 175 del pipeline · 101 del sitio · 8 del Worker.

LO PRÓXIMO (T-B25): la cuarta capa en el sitio — que diga y deje elegir MERCADO + MOTOR + COMBUSTIBLE
1. Localizar la función que pinta el bloque de piezas (clases `numero`, `numero-marca`,
   `numero-detalle`, `numero-original`). NO adivinar dónde está: buscarla.
2. Poner la etiqueta de variante encima del bloque (`etiquetaDeVariante()` ya existe y está probada).
3. Selector cuando hay varias variantes (`getVariantesDeVehiculo()` ya existe).
4. Mercado (el Worker ya acepta `?pais=`) y combustible (`traducirCombustible()` ya existe) en la
   misma pantalla: es UNA sola pregunta, "¿cuál es tu carro exactamente?".
5. Verificar con Chrome headless contra el servidor local (ya corre en el puerto 8765) y contra
   partexact.com.

REGLAS QUE NO SE ROMPEN
- Ningún número sin decir de qué mercado, de qué motor y de qué combustible es.
- En español NUNCA se escribe "gas" a secas: en RD significa gasolina y GLP a la vez. "Gasolina" o
  "Gas (GLP)", completos.
- Ninguna pieza inventada ni de ejemplo: antes no mostrar nada que dar un número que no le queda.
- El sitio TODAVÍA NO está para un cliente hasta que entre la cuarta capa (hoy muestra una de las dos
  variantes sin decir cuál, y eso puede dar el número de un motor equivocado).
```

---

## Comandos útiles (para no buscarlos)

```bash
cd ~/Proyectos/piezas-vehiculos/repo

# pruebas
python3 -m pytest pipeline/tests/ -q                 # 175 del pipeline
(cd site && node --test tests/*.test.js)             # 101 del sitio
(cd workers/autodoc-catalogo && npm test)            # 8 del Worker

# catálogo: partir para el sitio (no gasta cuota) y validar
python3 pipeline/partir_catalogo.py
python3 pipeline/validate.py

# descargar catálogo de la API (GASTA cuota; respeta --max-consultas)
set -a && . ./.env && set +a
python3 pipeline/fetch_autodoc.py --max-consultas 18000

# Worker
cd workers/autodoc-catalogo && npx wrangler deploy

# vista previa local (si no está corriendo)
cd site && python3 -m http.server 8765
```

## Archivos donde está lo que importa

- `TASKS.md` — el tablero. T-B22 (variantes), T-B23 (mercado), T-B24 (gas/GLP), T-B25 (dónde retomar).
- `site/js/catalogoMap.js` — traducción de categorías, variantes, combustible.
- `site/js/dataClient.js` — lo único que lee `data/build`.
- `pipeline/fetch_autodoc.py` — el catálogo (con `PresupuestoAgotado` y la alarma anti-cuelgue).
- `workers/autodoc-catalogo/` — el Worker por demanda (KV + tope mensual).
- `docs/` — criterio de flota, la API, el dominio bloqueado, el piloto.
