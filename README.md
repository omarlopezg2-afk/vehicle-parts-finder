# PartExact — buscador de piezas de vehículos (multimarca)

La pieza exacta de tu vehículo, confirmada por VIN. VIN o marca/modelo/año/versión →
ensamblaje correcto → diagrama y número de parte OEM (enlazado a la fuente, no copiado) →
esa pieza a la venta en eBay con fotos reales → enlace de afiliado. Multimarca desde el
diseño, gratis para el usuario.

**Estado del proyecto y decisiones: ver `PLAN.md`** (la memoria completa vive ahí).
**Contratos de datos entre agentes: ver `CONTRACTS.md`.**
**Tareas en curso: ver `TASKS.md`.**

## Empezar aquí (persona o IA que llega nuevo)

1. **`AGENTS.md`** — las reglas que no se rompen, los comandos y cómo se verifica que un número le
   queda. Es lo primero que hay que leer.
2. **`docs/TRASPASO.md`** — el traspaso completo: estado verificado con números, qué tocar y dónde,
   siguientes pasos con su coste en consultas y las trampas que ya costaron tiempo.
3. **`docs/ARRANQUE.md`** — el bloque corto para pegar en una conversación nueva.
4. **`TASKS.md`** — el tablero (lo último es T-B22 → T-B27).

## Desarrollo

```
cp .env.example .env   # rellenar con las llaves (nunca commitear .env)
```

Llaves que usa el proyecto (nombres; los valores, en el `.env` de Omar, que está ignorado por git):
`RAPIDAPI_KEY` (catálogo AUTODOC/TecDoc: **cada consulta se paga** del cupo mensual),
`EBAY_CLIENT_ID` / `EBAY_CLIENT_SECRET` / `EBAY_CAMPAIGN_ID` / `EBAY_REFERENCE_ID` (ofertas; hoy en modo
mock, sin cuenta de developer).

Pruebas: `python3 -m pytest pipeline/tests/ -q` · `(cd site && node --test tests/*.test.js)` ·
`(cd workers/autodoc-catalogo && npm test)`.

Estructura:
- `pipeline/` — scripts Python de recolección y construcción de datos.
- `data/` — `raw/` (crudo, no servido), `seed/` (ejemplos), `build/` (JSON finales).
- `site/` — frontend estático que consume `data/build/` vía `site/js/dataClient.js`.
- `.github/workflows/` — CI, recolección programada y deploy a GitHub Pages.
