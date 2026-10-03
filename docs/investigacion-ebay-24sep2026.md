# Investigación eBay (cuenta dev + afiliados EPN) — 24/09/2026

> Resultados en bruto de 3 investigaciones en paralelo, guardados para retomar cuando
> Omar lo indique. Falta: consolidar en PLAN.md y decidir dominio antes de aplicar a EPN.

## 1. Cuenta de desarrollador + token Browse API (fuente oficial)

- Registro gratis en https://developer.ebay.com/join → /signin?tab=register.
  Pide: username, password, email (x2), aceptar API License Agreement, captcha.
  Sin campo de país en el formulario. Aprobación ~1 día hábil (no verificable en vivo).
- Con la cuenta activa: https://developer.ebay.com/my/keys → crear keyset de Production
  (App ID/Client ID + Cert ID/Client Secret).
- Token por client credentials grant, YA sirve para Browse API sin pasos de afiliado:
  `POST https://api.ebay.com/identity/v1/oauth2/token`
  Header: `Authorization: Basic base64(client_id:client_secret)`
  Body: `grant_type=client_credentials&scope=https://api.ebay.com/oauth/api_scope`
  → `access_token` válido 7200s (2h).
- Llamada real: `GET https://api.ebay.com/buy/browse/v1/item_summary/search?q=<numero_parte>&limit=50`
  Headers: `Authorization: Bearer <token>`, `X-EBAY-C-MARKETPLACE-ID: EBAY_US`.
- Límite por defecto: 5,000 llamadas/día (se sube gratis con "Application Growth Check").
- Ojo: la aprobación EPN que menciona "Buy APIs Requirements" aplica a afiliados/checkout/
  Offer API, NO al uso de solo lectura de item_summary/search — ese ya funciona con el
  scope base en cuanto hay token.
- No se pudo verificar restricción de país (el chart de entidades eBay en ebayinc.com no
  cargó el día de la verificación).

Fuentes: developer.ebay.com/join, /signin, /my/keys, /my/api_test_tool,
/api-docs/static/oauth-client-credentials-grant.html, /api-docs/buy/buy-requirements.html,
/api-docs/buy/browse/resources/item_summary/methods/search, /develop/get-started/api-call-limits.

## 2. eBay Partner Network (EPN) — requisitos oficiales

- SÍ se puede/debe aplicar ANTES de tener el sitio con contenido: el Network Agreement dice
  literalmente "EPN must accept your application before you may display any Promotional
  Content or deploy any Promotional Method" — o sea la aprobación es previa al despliegue.
- El formulario (partnernetwork.ebay.com → Sign Up → login con cuenta eBay) SÍ exige declarar
  al menos una "propiedad promocional" (sitio web / app / red social) en "Promotional
  Information", pero no hay requisito objetivo publicado de tráfico mínimo o antigüedad.
- Aceptación "a la sola discreción" de EPN, puede rechazar "por cualquier motivo, sin
  compensación". No hay criterio numérico publicado.
- Elegibilidad: mayor de 18, no estar en país embargado por EE.UU. / listas de sanciones.
  No hay lista pública de países excluidos como afiliado (aparte de sanciones EE.UU.).
- Pago: mensual, se bloquea 30 días tras cerrar el mes, se paga ~día 10 hábil del mes
  siguiente. Umbral mínimo 10 USD (o equivalente). Métodos: transferencia bancaria o PayPal
  (2% comisión hasta tope). Requiere W9 (EE.UU.) o W8-BEN/W8-BEN-E (fuera de EE.UU.) antes de
  cobrar cualquier pago.
- Integración con Browse API: header `X-EBAY-C-ENDUSERCTX: affiliateCampaignId=<10 dígitos>,
  affiliateReferenceId=<opcional>` → las respuestas devuelven `itemAffiliateWebUrl` ya con
  tracking. Enlace manual (si no se usa API): esquema con `mkevt=1&mkcid=1&mkrid=...&
  siteid=...&campid=<EPN-CAMPAIGN-ID>&toolid=10001&customid=...`.

Fuentes: partnernetwork.ebay.com/solutions/joining-the-ebay-partner-network,
partnernetwork.ebay.com/page/network-agreement, developer.ebay.com/api-docs/buy/static/api-browse.html,
partnerhelp.ebay.com (Tax Information, Payment/Withdrawal, EPN link parameters).

## 3. Evidencia real de solicitantes (foros, no solo teoría oficial)

- Motivo de rechazo más citado: "the stated website... is non-functioning or inaccessible"
  o "quality... not in line with our network standards" — un sitio vacío/placeholder SÍ es
  motivo típico de rechazo en la práctica, aunque la letra oficial no lo exija.
- Tiempos reales muy dispersos: desde horas hasta 3-13 meses en casos atípicos (foros 2008-2013,
  poca evidencia fresca 2024-2026).
- Se puede reaplicar en cualquier momento tras rechazo simple (no baneo por causa). Reaplicar
  con el mismo sitio vacío suele repetir el rechazo; reaplicar tras mejorar el sitio ha
  funcionado en 2do/3er intento.
- Riesgos reportados: cierre por país no soportado (detectado a veces después de aprobar),
  cierre por inactividad, baneo permanente por "cuentas vinculadas" en reintentos repetidos
  desde mismo IP/dispositivo/PayPal.
- **Recomendación del investigador**: publicar primero una versión mínima pero funcional
  (home real, alguna página de categoría/búsqueda con contenido propio, política de
  privacidad + aviso de afiliados visible) y RECIÉN ENTONCES aplicar a EPN — no aplicar hoy
  con dominio vacío. Contradice el supuesto original del PLAN.md ("aplicar ya aunque no haya
  nada que enlazar"): ese paso debería moverse a DESPUÉS de tener un mínimo navegable, no antes.

## Pendiente para cuando Omar retome

1. **Decidir el dominio** (~10-12 USD/año, no comprado todavía) — bloquea tanto el registro
   de developer (recomendable, aunque no lo exige el formulario) como sobre todo EPN.
2. **Actualizar PLAN.md**: mover "aplicar a EPN" a después de tener un sitio mínimo funcional
   (no vacío), manteniendo "cuenta developer + token Browse API" como el paso que SÍ se puede
   hacer ya mismo, en paralelo al desarrollo, porque no depende de tener sitio.
3. Registrar cuenta developer (gratis, minutos + ~1 día de aprobación) puede adelantarse sin
   riesgo, ya que no exige sitio ni compromete nada.
