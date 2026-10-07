# Worker `autodoc-catalogo` (T-B20)

El catálogo **por demanda**. Resuelve lo que el sitio no tiene precalculado, sin exponer la clave
de AUTODOC y sin que nadie pueda vaciar la cuota del mes.

## Por qué existe

Pre-catalogar todos los años de todos los modelos son años de trabajo: el parque dominicano tiene
30 años de ancho (hay Corollas del 92 todavía rodando) y cada vehículo cuesta ~60 consultas. Con
20.000 al mes, "catalogarlo todo" no se termina. La salida es catalogar **lo que piden**: el primer
visitante de un modelo paga sus consultas, los siguientes lo reciben de caché al instante y con
cero gasto.

El Worker es el único sitio donde la clave puede vivir: el sitio es estático y una clave en el
navegador la lee cualquiera y consume la cuota en un día.

## Rutas

| Ruta | Qué hace | Coste |
|---|---|---|
| `GET /vehiculo?vin=JA4AP4AU3LU023739&categorias=100027` | VIN -> variante exacta -> piezas | ~6 consultas, o 0 si está en caché |
| `GET /vehiculo?make=Mitsubishi&model=Outlander%20Sport&year=2020&categorias=100027` | sin VIN, mejor variante del año | igual |
| `GET /salud` | latido y tope | 0 |

`categorias` es la lista de `categoryId` de TecDoc separada por comas. Sin ella devuelve solo el
vehículo resuelto (gastando ~3 consultas en vez de ~6 por categoría).

## La cuota manda

- El contador del mes vive en KV (`CUOTA`, clave `mes:YYYY-MM`) y se comprueba **antes** de
  cualquier llamada. Agotado el tope se responde 503 y **no se gasta ni una consulta** (hay prueba).
- La caché (`CATALOGO`, clave por país + VIN o marca/modelo/año) dura 90 días: los `articleId` de
  TecDoc no cambian.
- Se pide un máximo de 3 piezas por categoría, igual que el pipeline: lo justo y exacto en vez del
  volcado de marcas.

## Puesta en marcha

```bash
npx wrangler kv namespace create CATALOGO   # pegar los ids en wrangler.toml
npx wrangler kv namespace create CUOTA
npx wrangler secret put RAPIDAPI_KEY        # la clave, nunca en el repo
npm test                                     # 8 pruebas, con dobles de AUTODOC
npx wrangler deploy
```

## Lo que NO hace todavía

- No elige variante sin VIN cuando hay varias posibles: devuelve la mejor del año y **dice cuál usó**
  (`vehiculo.variante`), para que el sitio lo advierta en vez de mentir.
- No se ha desplegado: falta crear los KV y el secreto (requiere la cuenta de Cloudflare).
