# Por qué declinaron la solicitud a eBay Partner Network

> Investigación del **04/10/2026**, hecha por el líder con **fuentes primarias** (el acuerdo
> vigente, la ayuda oficial y las páginas del propio EPN). Todo lo que no sea cita textual o
> hecho comprobable está marcado como **inferencia**. Consulta de fuentes: 04/10/2026.

## 1. Lo que dice el acuerdo vigente (publicado el 24/09/2026)

El acuerdo que aplica a esta solicitud es el publicado el **24 de septiembre de 2026** en
`partnernetwork.ebay.com/page/network-agreement`. Cuatro cláusulas deciden casi todo:

**(a) El rechazo es discrecional y no hay apelación de derecho.** Sección II.A.1, textual:

> "EPN will notify you if EPN accepts or rejects your application. **EPN may in its sole
> discretion reject your application and terminate the Agreement for any reason without any
> compensation to you.**"

Y en "Term":

> "EPN's rejection of your application automatically terminates the Agreement."

Traducción práctica: no existe un derecho a una explicación ni a que revisen la decisión. Lo
único que queda es **que quieran** aceptar una solicitud futura. Esto no cierra la puerta,
pero sí determina con quién se habla: con soporte, como negocio, no como reclamación.

**(b) No se puede volver a aplicar a ciegas.** Sección II.A.1.a–d:

> "You may not apply without EPN's prior written consent if EPN has previously terminated your
> account… You may not register more than one account without prior written approval from EPN…
> You may not cancel your current account and register a subsequent account without prior
> written approval from EPN."

Esto **confirma la decisión de no mandar otra solicitud** mientras no haya respuesta: repetir
el alta es, en el mejor caso, ruido; en el peor, choca con la regla de una sola cuenta.

**(c) Todo método promocional no expresamente permitido exige aprobación previa por escrito.**
EXHIBIT A, *Additional Restricted Promotional Methods*, textual:

> "Any Promotional Method that is not expressly permitted or prohibited under these
> Participation Requirements is a **Restricted Promotional Method and cannot be used without
> EPN's prior written approval**."

**(d) Mostrar productos de eBay con la API es un programa aparte, y existe.** Definición 8:

> "eBay's Buy API Program: An **approved EPN Program** that permits Affiliates who have entered
> into an agreement with eBay, or an EPN approved third party, to **display and facilitate the
> purchase of products through eBay's API**."

Y la documentación del propio Browse API dice que, para cobrar comisión, hay que usar la URL
del campo `itemAffiliateWebUrl` — que es exactamente lo que hace nuestro `pipeline/fetch_ebay.py`
desde T-B5. Es decir: **el modelo de PartExact no es un invento raro; es un programa que eBay
documenta** — pero requiere estar dentro de EPN y que el método esté aprobado.

De paso, dos reglas que ya cumplimos o tenemos previstas: la divulgación de afiliado (FTC) y
que **todo el tráfico pase primero por nuestro sitio** y luego a eBay.

## 2. Lo que dice la ayuda oficial sobre los países

Artículo *"Why aren't all eBay countries available as a program in EPN?"* (22/09/2025), textual:

> "there are regulatory, financial, and other factors that prevent us from supporting some
> countries. **In many cases, the main limitation is that we cannot reliably send commission
> payments via wire transfer or PayPal there.** We regularly review the list of supported
> countries and add new ones as soon as it becomes possible."

Conclusiones verificadas: **no publican ninguna lista de países soportados**, y el criterio
declarado es la **capacidad de pago**, no el país en sí. El acuerdo, en V(B)(3), lista las
monedas en que se puede cobrar: USD, GBP, EUR, AUD, CAD, NOK, ILS, SEK, SGD, DKK y HKD —
**el peso dominicano no está**, así que un publicador en RD cobraría en divisa extranjera.

También verificado: **eBay Ambassador no es una alternativa** — es "For US & UK-based users
only".

## 3. Lo que se puede comprobar desde fuera (y lo que no)

**PayPal sí opera en la República Dominicana**, con retiros a banco local. De la propia
página de PayPal para DO:

> "Link your local bank to withdraw USD or local currency funds in your local currency… You can
> transfer your PayPal funds directly to your bank account and withdraw the funds in Dominican
> pesos." — y en su tabla de comisiones, para DO: 100 DOP por retiro en DOP, o 0,5 % (mínimo
> 10 USD) por retiro en USD.

**Límite honesto de este dato**: que PayPal pueda *recibir* dinero en RD no garantiza que el
producto que EPN usaría para pagar (**PayPal Payouts**, pago masivo a terceros) tenga cobertura
en RD. No lo pude confirmar con fuente oficial. Es el hueco exacto que el correo a EPN debería
cubrir, si algún día se envía.

**Evidencia secundaria** (marcada como tal, no es fuente oficial): reseñas de publicadores a
los que **les cerraron la cuenta después de generar comisiones** alegando "país no soportado",
con esta observación que importa para nuestro caso:

> "Oddly enough, this information wasn't made clear during the signup process. **If you don't
> support a country, why allow registration in the first place?**"

Es decir: **el formulario de alta deja aplicar a países no soportados y no advierte nada**.
Consecuencia directa: que la solicitud haya pasado el formulario no prueba absolutamente nada
sobre la elegibilidad del país. (Fue el error de razonamiento que cometí antes: inferir del
panel lo que no se puede inferir.)

## 4. Las tres hipótesis, ordenadas por lo accionables que son

Desde fuera **no se pueden distinguir**; el correo existe precisamente para eso. Pero no son
iguales de útiles:

| # | Motivo posible | Qué implicaría | ¿Está en nuestras manos? |
|---|---|---|---|
| **H1** | **El modelo declarado no coincide con el sitio**: se declaró "Content/Reviews" y la propiedad es una herramienta con integración de API (Buy API Program / método restringido que exige aprobación previa) | Existe una vía documentada: pedir la **aprobación previa del método** y/o el **Buy API Program**, y aplicar de nuevo declarando el modelo correcto | **Sí** — es trabajo nuestro redactar bien esa solicitud |
| **H2** | País / pagos (el peso dominicano no está entre las monedas; la ayuda oficial admite el límite de pago) | Habría que rehacer la Fase 3 (plan B: otra red) | **No** (salvo vía de pago alternativa) |
| **H3** | Calidad del sitio: propiedad **con horas de vida**, sin tráfico ni contenido propio, dominio recién comprado | Se arregla solo con tiempo, catálogo y contenido — justo lo que entregó la Ronda 4 | **Sí, con tiempo** |

**H1 es la hipótesis más accionable y no la habíamos considerado.** El punto débil del sitio no
es el país: es que **no es el sitio de contenido que se declaró**. Es una herramienta que
muestra anuncios reales de eBay vía API — potente, pero es otro modelo, y el acuerdo exige
aprobación previa por escrito para métodos que no estén expresamente permitidos.

## 5. Recomendación

1. **No enviar otra solicitud** mientras no haya respuesta (cláusula (b)). Ya decidido.
2. Cuando Omar decida enviar el correo (hoy **en pausa**), ya no debe preguntar "¿por qué me
   rechazaron?" — eso invita a una plantilla. Debe preguntar, en una sola carta, **cómo aplicar
   bien**: qué modelo/business model corresponde a PartExact, si necesita aprobación previa del
   método (y/o el Buy API Program), y si RD está soportado **para pagos**.
3. **El plan B sigue sin lanzarse** (instrucción expresa): primero esta investigación, que ya
   está hecha, y la respuesta de EPN.
4. Nada del sitio se toca. El sitio sigue con datos reales (T-H2 bloqueada a propósito, T-B5
   dormido con el código listo).

**Lo que cambia el diagnóstico**: si el motivo es H1, la puerta **no está cerrada** — hay un
trámite documentado (aprobación previa de método / SBM / Buy API Program) que hasta hoy no
hemos tocado. No es "apelar un rechazo": es **aplicar como corresponde al modelo real**.

## 6. Lo que NO se sabe (y se dirá tal cual)

- Cuál de los tres motivos aplicó. El correo no lo dice y el panel tampoco.
- Si la República Dominicana está en la lista de países soportados: **no es pública**.
- Si PayPal Payouts (el producto con el que pagaría EPN) cubre RD.
- Si una solicitud futura sería aceptada, incluso corrigiendo H1.
- Si la revisión fue automática o humana (la evidencia externa apunta a que las solicitudes se
  revisan a mano para cumplimiento, pero el rechazo llegó el mismo día con texto de plantilla).

## 7. Fuentes

| Fuente | URL | Qué se tomó |
|---|---|---|
| Network Agreement (24/09/2026) | `partnernetwork.ebay.com/page/network-agreement` | II.A.1 (rechazo discrecional), "Term" (el rechazo termina el acuerdo), II.A.1.a–d (una sola cuenta / consentimiento), V(B)(3) (monedas), definición 8 (Buy API Program), EXHIBIT A (métodos restringidos) |
| Ayuda oficial EPN | `partnerhelp.ebay.com/…/countries-available-as-a-program-in-EPN` (22/09/2025) | el límite es el pago, no el país; sin lista pública |
| Modelos de negocio especiales (SBM) | `partnernetwork.ebay.com/resources/special-business-models` | 7 métodos con formulario propio (Email/IM, Lealtad, Software instalable, Apps móviles, Sub-afiliados, PLA, IA) |
| Errores comunes | `partnernetwork.ebay.co.uk/solutions/common-missteps-to-avoid` | divulgación FTC; el tráfico va primero a tu sitio; "ignorance is not a defense" |
| Guía de alta y lista de monedas | `partnernetwork.ebay.com/solutions/joining-the-ebay-partner-network` | la moneda se elige de una lista cerrada y no se puede cambiar después |
| PayPal (DO) | `paypal.com/do/webapps/mpp/business-support/withdrawals` + tabla de comisiones DO | RD soporta recibir y retirar; comisiones DO |
| Reseña de publicador (secundaria) | `affpaying.com/ebay-partner-network` | el cierre por "país no soportado" y la falta de aviso en el alta |
