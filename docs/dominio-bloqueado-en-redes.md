# El dominio no abre en algunas redes (redes corporativas y filtros)

**Síntoma reportado (05/10/2026)**: desde la PC del trabajo, `https://partexact.com`
muestra la página genérica de Chrome — *"No se puede acceder a este sitio web / Se ha
restablecido la conexión"* — con **`ERR_CONNECTION_RESET`** y sin página de bloqueo.
Desde el teléfono con datos móviles, abre perfecto.

## Qué se midió (evidencia, no suposiciones)

| Comprobación | Resultado |
|---|---|
| El sitio, desde dos redes distintas | **HTTP 200** (HTML, datos, JS y CSS) |
| TLS desde fuera | 1.2 y 1.3, certificado válido (`CN=partexact.com`, Let's Encrypt) |
| `http://` | Redirige 301 a `https://` |
| DNS interno de la red del reporte (`OCTRGTSRV0046`, 10.64.0.50) | **Resuelve bien**: las 4 IPs de GitHub Pages |
| `nslookup partexact.com 8.8.8.8` desde esa misma red | Responde un nombre inventado (`partexact.com.campero.com`) con la IP `74.119.26.99` — **OSNET / PRWIFI-FLEXTEL (AS21559, Puerto Rico)** |

**Conclusiones**:

1. **No es el sitio.** No hay nada en el servidor que pueda provocar un corte: HTTP/2, TLS
   1.2/1.3, certificado válido, cabeceras normales, sin redirecciones raras.
2. **No es el DNS del destino.** La red donde falla resuelve el dominio correctamente.
3. **La conexión se corta en el camino.** Algo entre la PC y GitHub cierra la conexión TLS.
   Sin página de bloqueo significa que no "responde que no", sino que **corta** — es el
   comportamiento típico de los filtros que bloquean por defecto lo que **no está
   categorizado**, y `partexact.com` tiene días de vida y todavía no aparece en las listas
   de categorías de los fabricantes de filtros.

**Y se pudo precisar dónde muere la conexión** (prueba del propio usuario con `curl.exe -v`,
05/10/2026):

```
* IPv4: 185.199.110.153, 185.199.109.153, 185.199.111.153, 185.199.108.153
*   Trying 185.199.110.153:443...      <- resuelve bien y CONECTA
* ALPN: curl offers http/1.1
* Recv failure: Connection was reset
* schannel: failed to receive handshake, SSL/TLS connection failed
curl: (35) Recv failure: Connection was reset
```

Traducido: el DNS resuelve, la conexión **sí se establece**, y lo que se corta es **el saludo
TLS**. Eso descarta de una vez el bloqueo por IP y el bloqueo por DNS, y confirma un filtro que
deja pasar la conexión y **después la mata por el nombre del dominio** (bloqueo por SNI o por
categoría). Encaja con lo demás: el dominio está en la lista de "no permitido" y por eso no hay
página de bloqueo — no hay nadie que conteste.
4. **El proveedor de internet de esa red secuestra el DNS** (contesta consultas dirigidas a
   `8.8.8.8`). Es una práctica fea de los ISP pequeños, no algo que nosotros podamos
   arreglar; y es también la razón por la que el sitio va **solo en HTTPS con certificado
   válido**: con DNS secuestrado, un sitio sin certificado sí podría ser suplantado por la
   página de aparcamiento; con certificado válido, no.

## Camino rápido (minutos): que lo permitan desde la red

Quien administra el filtro puede permitir el dominio en minutos, y de paso **verá en su
registro qué aparato lo bloqueó y por qué** — que es el dato que hace falta para reclamar la
categoría correcta. Texto listo para un ticket, con lo que suelen pedir:

> **Asunto**: solicitud de acceso a `partexact.com`
>
> Buen día. Necesito acceso a `https://partexact.com`, un buscador de repuestos de vehículos
> que compara ofertas reales de eBay. Es un sitio de negocio legítimo (certificado TLS válido,
> sin descargas ni contenido sospechoso). Al intentar entrar, la conexión se restablece
> (`ERR_CONNECTION_RESET`) sin página de bloqueo, lo que sugiere que el filtro lo está
> bloqueando por no estar categorizado. ¿Podrían indicarme qué aparato lo bloquea y añadirlo
> a la lista de permitidos?
>
> Categoría sugerida: Negocios / Compras / Referencia.

## Camino definitivo (días): pedir la categoría del dominio

Los fabricantes de filtros tienen formularios públicos para reclamar la categoría de un
dominio nuevo. Conviene pedirla **una sola vez** y queda para todos sus clientes:

- **Fortinet (FortiGuard)** — https://url.fortinet.net/rate/submit.php (confirmado el 05/10/2026; pide URL, categoría, captura, nombre, correo y empresa)
- **Zscaler** — https://sitereview.zscaler.com/
- **Palo Alto Networks** — https://urlfiltering.paloaltonetworks.com/
- **Cisco Talos** — https://talosintelligence.com/reputation_center/web_categorization (formulario de categorización) y su política web en `/web_reputation`
- **Broadcom/Symantec (BlueCoat)** — https://sitereview.bluecoat.com/

Datos que piden: la URL, la categoría sugerida (**Negocios/Referencia**, no "Compras" ni
"Sin categorizar"), una captura del sitio, y nombre/correo/empresa de contacto.

## Por qué esto es un tema de negocio, no solo una anécdota

El comprador natural de repuestos —talleres y repuesteras— trabaja detrás de cortafuegos
corporativos, que son exactamente los que bloquean por defecto lo desconocido. Cada dominio
nuevo pasa por esto; se resuelve una vez y queda resuelto para todos esos clientes.
