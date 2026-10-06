# Cómo entrar al catálogo: puertas, requisitos y precios

> Indagado el 05/10/2026 en fuentes primarias (Auto Care Association vía
> automotiveaftermarket.org, theprontonetwork.com, apa.parts, guías de datos ACES/PIES).
> Responde a: *"¿qué requisitos debemos mostrar para ser vendedores de repuestos y entrar
> gratis al catálogo?"*

**Corrección de un error mío anterior**: dije que el catálogo "no está a la venta". Es verdad
para el **catálogo de aplicaciones curado** (Epicor PartExpert y similares: se entrega a
distribuidores, no se vende). Pero **los datos de referencia de la industria sí se venden, con
precio público, y son baratos**. Son dos cosas distintas y conviene no confundirlas:

- **Datos de referencia** (el "idioma"): qué vehículos existen, cómo se llaman las piezas, qué
  atributos tienen. Es la **taxonomía** — **no** trae los números de parte de cada marca.
- **Catálogo de aplicaciones** (el "contenido"): los números de parte reales de cada fabricante
  con sus aplicaciones por vehículo. Eso lo aporta cada marca.

## Puerta 1 — Ser vendedor autorizado de una marca (la que él pregunta)

Para vender marcas "con candado" (Bosch, Denso, ACDelco, Mopar, Motorcraft...) hay que demostrar
que uno es distribuidor legítimo. Lo que piden, literalmente:

| Requisito | Detalle |
|---|---|
| **Facturas de un distribuidor autorizado** | No recibos de tienda al detal: facturas que muestren **volumen de compra real** |
| **Carta de autorización del dueño de la marca** | La marca autoriza por escrito a ese revendedor |

Y una vez autorizado, **los datos ACES/PIES de esa marca se piden al fabricante o a su
proveedor de datos**: eso es el "catálogo gratis" al que se refiere la pregunta. No es gratis en
el vacío: viene con ser revendedor de verdad.

## Puerta 2 — Ser distribuidor de un grupo de compra (el catálogo completo, gratis)

Los grupos de compra son cooperativas **de distribuidores mayoristas**, no de tiendas ni de
software:

- **The Pronto Network**: 250+ distribuidores, 1.500+ tiendas, 200+ proveedores. A sus miembros
  les entrega el catálogo electrónico **"with no up-front cost"**, hoy servido por
  *ShowMeTheParts*, buscable por número de parte, referencia cruzada o año/marca/modelo.
- **APA (Automotive Parts Associates)**: cooperativa sin fines de lucro con **~60 distribuidores
  mayoristas independientes** como socios.
- **Aftermarket Auto Parts Alliance**: distribuidores independientes, tiendas y talleres de
  Norteamérica.

Requisito real: **ser un distribuidor mayorista establecido** ✗ — no es una puerta para un
proyecto de software, y el requisito no es dinero: es **ser del rubro**.

## Puerta 3 — Comprar los datos de referencia (precio publicado y escalado por ingresos)

La **Auto Care Association** vende las bases de referencia de ACES/PIES, y en marzo de 2025
publicó un plan **basado en los ingresos de la empresa**:

| Dato | Precio |
|---|---|
| **VCdb light duty** (vehículos) para empresas **de menos de 1 millón USD de ingresos** | **2.500 USD/año** (socio) |
| **Bases PIES** (de producto) | **1.050 USD** (socio) / 1.470 (no socio) … **hasta 7.763 USD** (socio) / 10.868 (no socio) |

Es decir: **del orden de 1.000 a 2.500 USD al año**, y una empresa pequeña paga lo mínimo.
(Aparte están las herramientas para *fabricar* ACES de una marca — DCi, MyFitment, SEMA Data
Co-op: 15.000–60.000 USD/año — pero eso es para quien **produce** el catálogo, no para quien lo
consume. Un revendedor **pide** los datos, no los fabrica.)

## Lo que esto significa para el proyecto

1. **El fitment que ya medimos (Browse API, gratis) no depende de nadie** y sigue siendo la base.
2. **Para los números de parte**, la vía realista no es comprar un catálogo, es **ser
   revendedor**: facturas con volumen + carta de la marca. Con eso, los datos de esa marca
   llegan, y llegan gratis.
3. **La puerta más limpia y barata para empezar es la Auto Care Association**: membresía +
   suscripción a las bases de referencia por ~1.000–2.500 USD/año según ingresos. Da el idioma
   común (vehículos, tipos de pieza, atributos) sobre el que se montan los datos de las marcas.
4. **Y siempre queda el camino local**: los importadores dominicanos ya están dentro de este
   sistema. Un acuerdo con uno de ellos es, en la práctica, la versión dominicana de la
   "puerta 2" — sin tener que montar un almacén propio.

## ¿Y recolectar los catálogos fabricante por fabricante? (medido 05/10/2026)

La idea: *"ya tenemos el listado de fabricantes de eBay, vamos a buscarlos según esa lista"*.
Medido antes de opinar:

**1. Ese listado no es lo que parece.** El aspecto "Brand" de eBay en estas categorías tiene
**~10.200 valores** (10.204 en limpiaparabrisas, 10.208 en filtros de aire, 10.394 en
radiadores) — y **casi los mismos en todas**, o sea que no es una lista de fabricantes de la
categoría: es **todo lo que los vendedores han escrito alguna vez** en ese campo. Los primeros
valores lo delatan: `Unbranded`, `1`, `1&1`, `101 Octane`, `1-800-Radiator`. Perseguir esa lista
es perseguir vendedores, errores de tecleo y basura.

**2. La industria ya reconoce ese trabajo como un producto.** Agregar los catálogos de los
fabricantes es exactamente lo que hacen Epicor, WHI, SEMA Data Co-op y los proveedores de
datos — y su precio público (15.000–60.000 USD/año en las plataformas de datos) **es el costo de
ese trabajo, empaquetado**. No es que sea imposible: es que **ya es el producto de otra gente**.

**3. Por fabricante, el trabajo real es mayor que "descargar un archivo"**: encontrar su canal
de datos (formulario, portal de distribuidor, FTP), conseguir autorización —que normalmente
exige ser revendedor, o sea la misma puerta de la sección anterior—, descargar y **parsear
ACES/PIES** (XML amarrado a las bases VCdb/PCdb/Qdb), validar, deduplicar y **mantenerlo
fresco** (cada marca actualiza su catálogo varias veces al año). Realista: **de horas a días por
fabricante**, más una obligación de mantenimiento para siempre. Para las ~40 marcas que de
verdad pesan en el aftermarket: **semanas o meses de ingeniería, y después nunca termina**.

**4. Advertencia sobre mi propia medición.** También intenté medir el "Pareto" (cuántas marcas
cubren el 90% de los anuncios) y **el número que salió no es confiable**: mi comparador buscaba
nombres de marca dentro del título y capturó el **nombre del vehículo** ("Mitsubishi" 150 veces)
y palabras cortas que coinciden con marcas ("Ram", "Ring", "Stop"). La cifra de "18 marcas = 90%"
**no la sostengo**. Lo que sí se ve en la muestra (278 anuncios) es que hay **unas pocas marcas
reales** (Centric Parts, TRICO, Better Brake Parts, FCS, Callahan) y una cola larga de vendedores
sueltos — consistente con "docenas, no miles", pero medido en serio requeriría otra vía.

## La vuelta estratégica: el dato es valioso, pero nosotros somos la demanda

Si esa información **vale dinero** (y vale), entonces también significa esto: quien la tiene
**necesita compradores**. Nosotros no tenemos que poseer el catálogo; tenemos que **poseer al
cliente**. Con tráfico real, el catálogo viene a nosotros — como revendedores, como socios, o
como anunciantes que quieren aparecer delante de alguien que acaba de saber qué necesita.

Por eso la recomendación no cambia, se refuerza: **no recolectemos catálogos; recolectemos
usuarios.** Y si algún día queremos probar la vía directa, el experimento honesto es **una sola
marca**: pedir sus datos como revendedor y medir cuánto tardó, qué pidieron y qué llegó. Ese
piloto de una marca dice el costo real por marca mejor que cualquier estimación mía.

## 7. La puerta que sí está abierta: alquilar el catálogo (05/10/2026)

**AUTODOC Parts Catalog API**, publicada en **RapidAPI** (autoservicio, precio público, sin
negociación y sin zona gris: su propia descripción dice que es para construir
*"auto parts lookup tools... comparison tools"*, que es exactamente nuestro caso).

| Plan | Precio | Consultas/mes | Equivale a |
|---|---|---|---|
| Basic | **0 USD** | 100 | **11 vehículos** con catálogo completo, para probar |
| **Pro** | **29 USD/mes** | **20.000** | **2.222 vehículos** con catálogo completo |
| Ultra | 59 USD/mes | 100.000 | 11.111 vehículos |
| Mega | 299 USD/mes | 1.000.000 | 111.111 vehículos |

**Qué consume cada consulta**: armar el catálogo de un vehículo son **9** (1 para saber sus
categorías + 8 para las piezas de cada una); el detalle de una pieza es 1.

**Los endpoints que importan** (nombres reales de su documentación):
`Article List by Vehicle ID & Category ID` (vehículo + categoría -> las piezas con su número),
`Article Details`, **`Parts Cross Reference`** (número OEM <-> equivalentes de otras marcas),
`Compatible Vehicles by Article No`, `Parts Diagram Coordinates` y `Article Media` (diagramas y
fotos).

**La cuenta que decide**: el catálogo dominicano estimado (60 modelos x 5 rangos de año = 300
vehículos, con 8 categorías cada uno) son **2.700 consultas** — cabe **7 veces** en el plan de
29 USD, y refrescarlo cada mes gasta el 14% de la cuota.

**Y lo importante**: las búsquedas de los usuarios **no gastan ninguna consulta**, porque el
catálogo se arma una vez al mes y el sitio lo sirve desde su propio JSON (que es justo lo que ya
hacemos con el fitment). Los 20.000 son para **construir**, no para servir. El cargo por ancho de
banda (1 USD por GB sobre 10 GB) no llega a aplicarse nunca a este volumen.

**Único cabo suelto antes de pagar**: AUTODOC es europeo y nuestros vehículos son del mercado
estadounidense. El plan gratis de 100 consultas existe exactamente para comprobarlo con datos.

## Nota lateral que vale la pena

eBay Motors, Amazon Auto y RockAuto **exigen datos ACES para el fitment** de las publicaciones:
sin ellos, las piezas no aparecen en las búsquedas filtradas por vehículo. Es decir, el idioma
que estamos considerando aprender es el mismo que usan los canales grandes — y es la razón por
la que el fitment de eBay que ya aprovechamos es tan valioso.
