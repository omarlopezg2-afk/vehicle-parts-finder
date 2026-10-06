# ¿Se puede dar el número de parte buscando por **placa**? — Fuentes revisadas (06/10/2026)

Pregunta del usuario: *"estuve pensando el tema de ofrecer piezas con la placa, pero el único
lugar público que conozco que se pudiera conseguir el dato de la placa amarrado a chasis es la
DGII"*. Revisión hecha con las fuentes oficiales y con lo que existe en la región.

## 1. Lo que la DGII **sí** tiene y lo que **no** da

**Tiene el dato**: la DGII registra la placa con su chasis. Su propia documentación lo confirma:
el QR del **marbete** devuelve *"marca y modelo del vehículo renovado, además de su color, año de
fabricación, **número de placa y chasis**"* (brochure oficial del Marbete y ficha de ayuda CA3238),
y el QR de la **placa provisional electrónica** devuelve *"marca, modelo, color, año, **chasis**,
número de placa provisional y fecha de expiración"* (ficha CA4946).

**Pero su consulta pública no sirve para esto.** La "Consulta de Placas" oficial
(`dgii.gov.do/vehiculosMotor/consultas/Paginas/consultaPlacas.aspx`) exige **Cédula o RNC + Placa**
y su propósito declarado es *"saber si un vehículo tiene alguna oposición y si este está a su
nombre"* — es decir: **oposiciones y titularidad, no datos técnicos**, y no devuelve el chasis.
Sin la cédula del propietario no hay consulta.

**Y no existe un servicio público placa -> chasis en RD.** Búsqueda dedicada sin resultados: no
hay API, ni portal, ni "datos abiertos" que resuelva placa -> VIN en el país. Los artículos que
prometen *"consultar la placa sin cédula"* son contenido SEO: o mandan al portal de la DGII (que
pide la cédula) o hablan genéricamente de *"empresas autorizadas"* sin nombrar ninguna.

## 2. El contraste regional (y por qué aquí no hay negocio de eso)

- **Colombia: sí y es un commodity.** El RUNT permite la consulta básica por placa **+ documento
  del propietario**; con el VIN no hace falta el documento. Encima hay APIs comerciales —
  **PlacApi** (`placapi.com`) vende la ficha completa del RUNT por placa *y* por VIN, con
  `noChasis`, `noVin`, `noMotor`, marca, línea, modelo, SOAT, tecnomecánica — documentada y por
  consulta. En Colombia la placa -> chasis se **alquila**.
- **Brasil: apps de placa -> chasis por decenas** (más de 57 datos, incluido el chasis), señal de
  que el negocio existe **cuando el registro es abierto**.
- **República Dominicana: el registro no es abierto.** De ahí que iMotriz cobre por su búsqueda
  por placa en Colombia y que ese mismo producto no se pueda copiar aquí tal cual.

## 3. La puerta que sí está abierta: **el QR del propio vehículo**

La DGII publica su propio dato por QR y lo declara fidedigno: *"estas informaciones obtenidas por
estos medios son fidedignas siempre y cuando provengan del dominio https://dgii.gov.do/"* —
o sea, **el QR contiene una dirección dentro de `dgii.gov.do`** que muestra la ficha del vehículo.
Ese QR está en el **sticker del marbete pegado en el vehículo** (y en el recibo de renovación) y
en la **placa provisional electrónica**.

Consecuencia práctica, y es la buena noticia: **no hace falta inventar nada para leer el chasis del
vehículo que tienes delante — el propio Estado lo publica para quien tenga el vehículo delante**
(el dueño, o el taller con el carro en el elevador y el marbete en el parabrisas).

Lo que hay que comprobar (30 segundos, con el marbete del usuario en mano): qué abre exactamente
ese QR — si es una URL con código que resuelve a una página con la ficha, el sitio puede aceptar
ese enlace o ese código y quedarse con el chasis sin que nadie teclee nada.

## 4. Los dos caminos, ordenados por realismo

1. **El QR (hoy, sin permiso de nadie).** "Escanea el QR de tu marbete y te digo qué piezas te
   quedan". Datos del propio usuario, fuente oficial, cero tecleo. No conocemos a nadie en RD que
   lo haga.
2. **Pedir acceso a la DGII / INTRANT (mañana, si el producto crece).** La DGII ya tiene un
   mecanismo formal de **interconexión con instituciones** (aparece en su catálogo de servicios de
   Vehículos de Motor), y el INTRANT es el dueño del registro. El argumento a favor es honesto:
   ayudar a que la gente compre la pieza correcta. Es una petición por escrito al Departamento de
   Vehículos de Motor, no un scraping.

## 5. Lo que **no** se hace (y por qué queda escrito)

- **No** construir sobre los "consulta la placa sin cédula" que circulan: exponen datos del
  propietario y la **Ley 172-13 de Protección de Datos Personales** existe justamente para eso.
  Además se romperían el día que la DGII cambie el portal.
- **No** scrapear el portal de la DGII: mismo problema y mata cualquier conversación con ellos.

## 6. Conclusión honesta para el producto

La placa **no** puede ser hoy la llave de entrada (el registro dominicano está cerrado). Pero el
**chasis del vehículo que el usuario tiene delante sí es obtenible sin pedirle permiso a nadie**,
por el QR que el propio Estado publica. Y para el caso del taller o del mecánico —que tiene el
carro enfrente— eso es exactamente lo que hacía falta.

Traducción al producto: en vez de *"buscar por placa"*, la función es **"leer el vehículo"**:
escanear el QR del marbete (o el de la placa provisional), o mirar la matrícula, que siempre trae
el VIN. La placa queda como **fase 2 condicionada a la DGII**, no como bloqueo del lanzamiento.
