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

## Nota lateral que vale la pena

eBay Motors, Amazon Auto y RockAuto **exigen datos ACES para el fitment** de las publicaciones:
sin ellos, las piezas no aparecen en las búsquedas filtradas por vehículo. Es decir, el idioma
que estamos considerando aprender es el mismo que usan los canales grandes — y es la razón por
la que el fitment de eBay que ya aprovechamos es tan valioso.
