# Competencia local: quién está en el mercado de repuestos en RD

Levantado el 05/10/2026 con búsquedas y visitas reales a cada sitio (no de memoria).
La pregunta que responde: **¿cuántos sitios unen hoy a vendedores de partes en un solo lugar,
y qué hace cada uno?**

## 1. Marketplaces dominicanos que agrupan vendedores (la categoría exacta)

| Sitio | Qué es de verdad (verificado) | Lo que NO hace |
|---|---|---|
| **ARO — Auto Repuestos Online** (`autorepuestos.online`, también `aro.do`) | Marketplace dominicano "integrado por la mayoría de tiendas de repuestos de RD". En vivo, con páginas por marca (Toyota, Honda, Kia, Ford, Jeep, Chevrolet, Isuzu, Nissan, Suzuki, Mitsubishi, Mazda) y filtro de piezas. Teléfono y correo. Basado en WooCommerce. | No hay búsqueda por VIN ni por número de parte: se navega por marca/categoría. Es inventario, no identificación |
| **La Pieza.DO** (`lapieza.do` + portal de negocios `negocios.lapieza.do`) | El intento más completo: portal para que las tiendas publiquen, cobro (tarjeta/transferencia/efectivo) y entrega por la plataforma ("el cliente paga, tú preparas, nosotros entregamos"). Asistente con IA. Su marketing dice **"100K+ clientes buscando, 500+ negocios vendiendo"** (cifra suya, no verificable). Aclara que no cobra comisiones "por tiempo limitado" | Su discurso al vendedor es *visibilidad de inventario*. Tampoco identifica la pieza por VIN |
| **PiezaGO** (`piezago.do`) | "El marketplace #1 de repuestos de RD". En la práctica hoy es una **página de presentación** con botones a WhatsApp ("Buscar Repuestos", "Vender en Pieza GO"): hay intención y marca, poca plataforma visible | Todo el flujo termina en WhatsApp; sin catálogo propio aún |
| **NetParts** (`netpartspad.com`) | Anunciado como ecosistema (piezas, seguros, grúas, "CarCheck", renta, subastas), con alineación de VIN y "tiendas en el marketplace". **Aún sin lanzar** (pide registro para el día del lanzamiento) | No está operando |

## 2. Los que tienen el tráfico (aunque no sean del rubro)

- **Corotos** (`corotos.com.do/sc/vehiculos/repuestos`) — el clasificados líder del país, con
  categoría real de repuestos nuevos y usados y miles de particulares y talleres. **No ayuda a
  identificar la pieza**: hay que saber qué buscar.
- **MercadoLibre RD** — categoría de autopartes y accesorios, con la confianza y la logística del
  marketplace grande.
- **Facebook Marketplace, grupos de WhatsApp e Instagram** — el canal real de facto del país.

## 3. El que da miedo: ya está hecho, pero no aquí

**iMotriz** (`imotriz.com`) es un marketplace regional maduro (**versión 5.78.5**) operando en
**Colombia, México, Ecuador y Costa Rica** — no en República Dominicana todavía. Su buscador ofrece
exactamente lo que queremos construir:

- buscar por nombre, **número de parte o VIN**
- buscar autopartes **con la placa** del vehículo
- **despiece del vehículo con el VIN**
- **números de parte sustitutos y equivalentes**
- **vehículos compatibles con un número de parte** (la búsqueda inversa)
- y un producto **"Mi Taller"**: software para talleres

O sea: la idea no es nueva ni nuestra; está resuelta, madura, a una frontera de distancia. Y su
existencia valida el modelo (marketplace + fitment + software para talleres) mientras nos avisa de
que **hay una ventana antes de que crucen**.

## 4. La cola larga: tiendas con tienda online propia

Cada vez más repuesteras dominicanas montan su web (varias con "filtro por vehículo" o "dinos marca,
modelo y número de parte"): Repuestos Los Bueyes, Autopieza RD, Auto Repuestos Juan Nicasio
(Santiago), Nessparts, Auto Fashion, Kodai Auto Parts (coreanos), Importadora Savinón (mayorista,
28 años), Repuesto.com.do (importación bajo pedido) y los concesionarios oficiales (Santo Domingo
Motors, que ya usa "softwares especializados" de catálogo, o sea un EPC, con atención por teléfono).

## 5. Teardown de iMotriz: cómo gana dinero (verificado en sus propias páginas)

Esto no es un competidor cualquiera: es **el modelo de negocio del rubro, ya funcionando**. Lo que
vende, según sus páginas de vendedores y talleres:

| Lo que cobran | Cómo lo describen ellos |
|---|---|
| **Comisión por venta** | *"Solo pagas una comisión por cada venta exitosa"* en el marketplace |
| **Posicionamiento pagado** | Planes **Esencial / Profesional / Superior** para elegir "el orden de posicionamiento de tus productos en el Marketplace" |
| **Presupuesto de leads** | *"Acelerador de clientes"*: comprar más leads eligiendo las marcas de vehículo que comercializas "y asignando un presupuesto" |
| **Leads por WhatsApp (iMotriz Go)** | Sistema que manda solicitudes de cotización perfiladas **al WhatsApp del vendedor**, "sin necesidad de publicar tus inventarios". Cobrado (el usuario confirma que cobra tras cierta cantidad de consultas) |
| **Software de taller ("Mi Taller")** | SaaS completo: recepción del vehículo, asignación de mecánico, diagnóstico, cotización con despiece, avisos por WhatsApp, encuesta final |
| **Herramientas para distribuidores** | Tienda virtual B2B/B2C, tienda privada, "Tu propio Marketplace", **sincronización por API**, plataforma de compras |

Y el activo de fondo: **el catálogo**. Lo que les venden a los vendedores es *"integramos en tu tienda
nuestros catálogos de autopartes originales"* para que "tus clientes los encuentren con búsquedas por
VIN y/o diagramas de partes". O sea: **el dato del catálogo es su foso**, y el dinero sale de los
vendedores y los talleres, no del comprador.

**Lo que enseñó el intento de usarlo desde aquí**: la búsqueda anónima por VIN no devuelve resultados
sin cuenta (su buscador exige sesión, y ya se sabe que cobra pasado cierto número de consultas). No
se forzó más: son consultas pagadas del usuario, no nuestras. **La precisión real de su fitment solo
la puede contar quien lo ha usado** — y esa es la pregunta abierta de este teardown.

## Lo que dicen los datos sobre nuestro hueco

1. **El espacio de marketplace ya está disputado y no debemos entrar ahí.** Cuatro intentos locales,
   uno de ellos diciendo que agrupa a "la mayoría de las tiendas"; más Corotos y MercadoLibre con
   todo el tráfico. Competir ahí es competir por inventario y vendedores, que son justo lo que no
   tenemos.
2. **Nadie en RD lidera con *el número*.** Todos lideran con *el inventario*: el usuario tiene que
   llegar sabiendo qué buscar. La pregunta "¿cuál pieza es la de mi carro?" queda sin responder en
   todas. Ahí está nuestro sitio.
3. **Los marketplaces locales no son el enemigo: son los primeros anunciantes.** Ya pagan por
   visibilidad entre ellos (La Pieza.DO le vende visibilidad a las tiendas), así que el tráfico de
   alguien que acaba de saber qué necesita vale dinero para ellos. Eso valida el modelo de ingresos
   por anuncios locales con evidencia de mercado, no con una idea.
4. **La desventaja a vigilar**: casi todos prometen "compatibilidad garantizada" — y varios sin
   datos que lo sostengan. Cuando todos prometen lo mismo, la única diferencia real es tener el dato
   de verdad y decirlo con honestidad. Esa es la apuesta pendiente (T-B7).
5. **El modelo de ingresos ya está probado por otro**: iMotriz cobra por posicionamiento, por leads
   (incluidos leads a WhatsApp) y por software de taller. No hay que inventar la monetización: hay
   que **hacerla más barata para el comprador**. Nuestra ventaja estructural es que el sitio es
   estático y las consultas a la API salen de una cuota gratuita: podemos dar **la consulta gratis**
   donde ellos cobran, y ganar del lado del vendedor (posicionamiento, leads) — que es exactamente
   donde ellos ya demostraron que hay dinero.
