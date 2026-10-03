# Buscador de piezas de vehículos (multimarca)

VIN o marca/modelo/año/versión → ensamblaje correcto → diagrama y número de parte OEM
(enlazado a la fuente, no copiado) → esa pieza a la venta en eBay con fotos reales →
enlace de afiliado. Multimarca desde el diseño, gratis para el usuario.

**Estado del proyecto y decisiones: ver `PLAN.md`** (la memoria completa vive ahí).
**Contratos de datos entre agentes: ver `CONTRACTS.md`.**
**Tareas en curso: ver `TASKS.md`.**

## Desarrollo

```
cp .env.example .env   # rellenar con llaves de eBay (nunca commitear .env)
```

Estructura:
- `pipeline/` — scripts Python de recolección y construcción de datos.
- `data/` — `raw/` (crudo, no servido), `seed/` (ejemplos), `build/` (JSON finales).
- `site/` — frontend estático que consume `data/build/` vía `site/js/dataClient.js`.
- `.github/workflows/` — CI, recolección programada y deploy a GitHub Pages.
