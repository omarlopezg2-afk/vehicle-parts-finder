# Solicitud a soporte técnico de eBay (Developer Technical Support)

**Estado**: redactada, **no enviada**. Va a **soporte técnico de desarrolladores** (DTS), **no a
EPN** — hay una instrucción explícita de no mandar otra solicitud a EPN mientras se investiga.

**Por qué se pregunta antes de aplicar**: la página oficial *Buy APIs Requirements* dice que el uso
en producción de las Buy APIs es solo para socios y que se solicita **a través de EPN** — que ya nos
declinó. Antes de volver a esa puerta, conviene (1) saber si la Catalog API tiene un canal propio, y
(2) haber medido en sandbox qué datos da de verdad (marca, número de parte, atributos).

---

## Texto de la consulta (en inglés, es el idioma del soporte de eBay)

> **Subject**: Catalog API access path for a read-only parts finder (Application: PartExact)
>
> Hello,
>
> I'm the developer of **PartExact** (https://partexact.com), a parts finder for the Dominican
> Republic market. Users enter a VIN, a part number or their vehicle, and we show them the listings
> that fit their vehicle, linking out to eBay. We already use the **Browse API in production**
> (`item_summary/search`, client-credentials OAuth) and it works well.
>
> Two questions:
>
> 1. **Catalog API access path.** We'd like to use the Catalog API read-only
>    (`GET /commerce/catalog/v1_beta/product/{epid}` and `product_summary/search`) to show the
>    brand, the manufacturer part number and the attributes of the products our users are looking
>    at. Our current production calls return `403 Insufficient permissions`. The Buy APIs
>    Requirements page points to the eBay Partner Network for Buy API production access — does the
>    Catalog API follow the same path, or is there a separate approval process for this read-only
>    use case (you are listed as the contact for this Limited Release API)?
> 2. **Sandbox access.** We already tested this, so you don't have to guess: with a valid sandbox
>    token, the **Browse API works** (HTTP 200) but the **Catalog API returns 403 Insufficient
>    permissions in sandbox too** (`product_summary/search` and `product/{epid}`). So the sandbox
>    is not open for this API either. Given that, what is the correct approval path for the
>    Catalog API, and is it available at all to a read-only, buyer-side use case like ours?
>
> We are not asking for special treatment, and we understand there is no guarantee of approval. We
> just want to follow the correct procedure instead of applying where it can't be granted.
>
> Details, in case they help:
> - eBay developer account / user ID: *(completar)*
> - Application title: **PartExact** (Production keyset already issued and in use)
> - Expected volume: a few hundred calls per day to start (well inside the standard limits)
> - We store only the identifiers and links, never eBay images or descriptions beyond what the API
>   returns for display, and we comply with the eBay API License Agreement.
>
> Thank you,
> *(nombre y correo de contacto)*

## Lo que falta para enviarla

1. **Entrar al portal de desarrolladores.** La bóveda de Hermes **no pudo rellenar** el formulario de
   eBay (su página de ingreso tiene dos campos de contraseña — uno de ellos del registro, oculto — y
   nombres de campo atípicos), y no se insiste: una contraseña no se teclea a mano nunca. El camino
   que sí funciona, y que ya funcionó con Google y con iMotriz, es que **el usuario inicie sesión en
   su propio Chrome y lo cierre**; el navegador del agente trabaja sobre una copia de ese perfil, así
   que hereda la sesión sin que nadie vea una clave.
2. De ahí sacar dos datos: el **user ID de desarrollador** y las **llaves de sandbox** de la app
   (las de sandbox son distintas de las de producción, y son las que permitirían probar la Catalog
   API gratis).
3. Confirmar con qué nombre, correo y empresa firmamos la consulta.

## Plan B, ya medido y sin puertas

Si la respuesta es "hay que pasar por EPN", no se pierde nada: el camino de los **datos ACES/PIES
que los fabricantes publican gratis** para el canal sigue en pie, y el **fitment de la Browse API**
(medido en `docs/piloto-tb7.md`) ya da para el producto que prometemos.
