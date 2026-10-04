# Taxonomía de categorías (congelada por el líder, 04/10/2026)

Este documento es el contrato de la Ronda 4 para la taxonomía de categorías. **Congelado**:
los agentes D (seed) y F (categories.json + SVG) construyen contra esta lista; ningún agente
la cambia por su cuenta. Si algo no sirve, se pide al líder.

## Por qué existe

La Ronda 3 dejó 12 categorías de producto reales (más un marcador que no es categoría) y el
backlog de Omar pedía "categorías más granulares, con la taxonomía estándar de la industria".
La estructura de 2 niveles (grupo → categoría) ya estaba construida y funcionando; lo que
faltaba era **el catálogo de categorías en sí**.

Terminología: se adopta el patrón genérico del sector (sistema → pieza, como usan los
catálogos grandes). Es terminología común de la industria, no contenido propietario de nadie:
no se copia ninguna descripción, icono ni texto de otro catálogo.

## Reglas de inclusión (para no volver a discutirlas categoría por categoría)

Una categoría entra solo si cumple las tres:

1. **Es una pieza que el dueño compra por número** — pieza de desgaste, reemplazo o
   reparación. Quedan fuera por ahora: fluidos a granel (aceite, refrigerante, líquido de
   frenos) y piezas de carrocería grandes (parachoques, capó, puertas), que no se envían
   bien ni se buscan por número de la misma forma.
2. **Existe en vehículos que el catálogo ya soporta o va a soportar** (turismos/SUV
   multimarca). No se crean categorías de moto, camión pesado ni maquinaria.
3. **Tiene al menos una parte real verificada** en `data/seed/` — o queda explícitamente
   marcada como pendiente, nunca publicada vacía sin decirlo.

## Los 9 grupos y las 33 categorías

`svg` = nombre del archivo en `site/assets/categories/`. "(existente)" = ya está en el repo;
"(nuevo)" = lo crea el agente F en el mismo estilo de línea simple que los existentes.

### mantenimiento — Mantenimiento
| slug | name_es | svg |
|---|---|---|
| `filtro-aceite` | Filtro de aceite | filtro-aceite.svg (existente) |
| `filtro-aire` | Filtro de aire | filtro-aire.svg (existente) |
| `filtro-cabina` | Filtro de aire de cabina | filtro-cabina.svg (nuevo) |
| `filtro-combustible` | Filtro de combustible | filtro-combustible.svg (nuevo) |
| `limpiaparabrisas` | Limpiaparabrisas (plumilla) | limpiaparabrisas.svg (existente) |

### frenos — Frenos
| slug | name_es | svg |
|---|---|---|
| `pastillas-freno` | Pastillas de freno | pastillas-freno.svg (existente) |
| `discos-freno` | Discos de freno | discos-freno.svg (existente) |
| `tambor-freno` | Tambor de freno | tambor-freno.svg (nuevo) |
| `caliper` | Caliper (pinza de freno) | caliper.svg (nuevo) |
| `manguera-freno` | Manguera de freno | manguera-freno.svg (nuevo) |

### motor — Motor
| slug | name_es | svg |
|---|---|---|
| `bujia` | Bujía | bujia.svg (existente) |
| `correa` | Correa (banda) | correa.svg (existente) |
| `junta-culata` | Junta de culata | junta-culata.svg (nuevo) |
| `soporte-motor` | Soporte de motor | soporte-motor.svg (nuevo) |
| `bomba-combustible` | Bomba de combustible | bomba-combustible.svg (nuevo) |
| `sensor-oxigeno` | Sensor de oxígeno | sensor-oxigeno.svg (nuevo) |

### suspension-direccion — Suspensión y dirección
| slug | name_es | svg |
|---|---|---|
| `amortiguador` | Amortiguador | amortiguador.svg (existente) |
| `rotula` | Rótula (ball joint) | rotula.svg (nuevo) |
| `terminal-direccion` | Terminal de dirección | terminal-direccion.svg (nuevo) |
| `rodamiento-rueda` | Rodamiento de rueda | rodamiento-rueda.svg (nuevo) |

### electrico — Eléctrico
| slug | name_es | svg |
|---|---|---|
| `bateria` | Batería | bateria.svg (existente) |
| `alternador` | Alternador | alternador.svg (existente) |
| `motor-arranque` | Motor de arranque | motor-arranque.svg (nuevo) |
| `bobina-encendido` | Bobina de encendido | bobina-encendido.svg (nuevo) |

### refrigeracion — Refrigeración
| slug | name_es | svg |
|---|---|---|
| `bomba-agua` | Bomba de agua | bomba-agua.svg (existente) |
| `termostato` | Termostato | termostato.svg (nuevo) |
| `radiador` | Radiador | radiador.svg (nuevo) |

### iluminacion — Iluminación
| slug | name_es | svg |
|---|---|---|
| `faro` | Faro | faro.svg (existente) |
| `bombilla` | Bombilla (lámpara) | bombilla.svg (nuevo) |
| `luz-trasera` | Luz trasera | luz-trasera.svg (nuevo) |

### carroceria-exterior — Carrocería y exterior
| slug | name_es | svg |
|---|---|---|
| `espejo-lateral` | Espejo lateral | espejo-lateral.svg (nuevo) |
| `manija-puerta` | Manija de puerta | manija-puerta.svg (nuevo) |
| `clips-y-sujeciones` | Clips y sujeciones | clips-y-sujeciones.svg (nuevo) |

**Total: 33 categorías de producto en 8 grupos.**

### Cambios respecto a la Ronda 3 (explícitos, para que nadie los lea como pérdida)

- `limpiaparabrisas` **cambia de grupo**: estaba en `carroceria-exterior` y pasa a
  `mantenimiento` (es un consumible de mantenimiento; el usuario lo busca ahí). El slug no
  cambia, así que ninguna parte se rompe.
- **`clip-parachoques` desaparece** y se reemplaza por `clips-y-sujeciones`. Motivo real: la
  parte `MR297182` del seed usaba `clip-parachoques`, que **nunca existió en
  `categories.json`** — o sea que hoy el sitio sirve una parte que no aparece en ninguna
  categoría. Es un bug de integridad referencial, no una preferencia de nombres. Además el
  nombre nuevo cubre más casos (clips de parrilla, de guardafango, de moldura), y el
  contrato ya prevé `other_names` para los sinónimos.
- `generico-sin-foto` (grupo `otros`) **no es una categoría de producto**: es el marcador de
  "sin foto" que ya usa el frontend. Se queda en `categories.json` pero no cuenta para el
  total de 33 y no aparece en la navegación por categorías.

## Regla para el futuro

- Un slug nuevo requiere: fila en este documento + SVG en `site/assets/categories/` + al
  menos una parte real en el seed. Las tres cosas, o no entra.
- Los nombres de cara al usuario van en español; el slug es técnico, en minúsculas y con
  guiones, y **nunca cambia** una vez publicado (es la clave que usan `parts.json` y el
  índice de búsqueda).
