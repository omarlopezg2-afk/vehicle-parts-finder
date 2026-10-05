"""Cliente de eBay Browse API (T-B1).

Expone `search_part(part_number_norm) -> list[dict]`, que devuelve resultados en
la forma del campo `offers` de CONTRACTS.md:
    { "store": "eBay", "url", "price", "currency", "condition", "updated_at", "image" }

Dos modos:
- MOCK (por defecto): no requiere llaves. Usa el fixture
  `pipeline/fixtures/ebay_browse_search.sample.json`, que tiene la FORMA real de
  una respuesta de `item_summary/search` (verificada el 24/09/2026, ver
  docs/investigacion-ebay-24sep2026.md).
- REAL: solo se intenta si existen las variables de entorno EBAY_CLIENT_ID y
  EBAY_CLIENT_SECRET (ver .env.example). Si no existen -> mock automático, sin
  fallar. Si existen pero la llamada real falla (red, 401 persistente, 429
  persistente, etc.) -> se cae a mock igual, documentado abajo, para que el
  pipeline nunca se caiga por esto.

Solo usa librería estándar (urllib, json, base64) a propósito: así corre
out-of-the-box sin `pip install` en el modo mock, que es el que no tiene llaves
todavía.

--- Datos técnicos verificados el 24/09/2026 (modo real) ---
Token (client credentials grant):
    POST https://api.ebay.com/identity/v1/oauth2/token
    Header: Authorization: Basic base64(client_id:client_secret)
    Header: Content-Type: application/x-www-form-urlencoded
    Body:   grant_type=client_credentials&scope=https://api.ebay.com/oauth/api_scope
    -> devuelve access_token, válido ~7200s (2h). No se cachea entre llamadas de
       este módulo: cada proceso del pipeline pide su propio token (el pipeline
       corre una vez por ejecución programada, no hace falta más).

Búsqueda:
    GET https://api.ebay.com/buy/browse/v1/item_summary/search?q=<numero_parte>&limit=50
    Header: Authorization: Bearer <token>
    Header: X-EBAY-C-MARKETPLACE-ID: EBAY_US

Límite: 5000 llamadas/día por defecto (se sube gratis pidiéndolo, "Application
Growth Check"). Este módulo no implementa un contador de cuota propio; si eBay
responde 429 se aplica el manejo descrito abajo.

--- Modo afiliado (T-B5, eBay Partner Network) ---
Para que eBay pague comisión por los clics, la documentación de EPN dice literal:
"In order to receive a commission for your sales, you must use the URL returned
in the itemAffiliateWebUrl field" — no basta con pegarle parámetros a mano a
itemWebUrl.

Cómo se activa aquí:
- Si existe `EBAY_CAMPAIGN_ID` en el entorno (no vacío), la búsqueda manda el
  header `X-EBAY-C-ENDUSERCTX: affiliateCampaignId=<id>`.
- Si además existe `EBAY_REFERENCE_ID` (el "custom id" de EPN), se añade al mismo
  header, separado por coma: `affiliateCampaignId=<id>,affiliateReferenceId=<ref>`.
- Si NO existe `EBAY_CAMPAIGN_ID`, el header no se manda (comportamiento idéntico
  al de hoy, enlaces normales).
- En `_map_item_summary_to_offer`, `offer.url` usa `itemAffiliateWebUrl` cuando
  el item lo trae (no vacío); si no viene, cae a `itemWebUrl` como siempre. Esto
  pasa tanto si pedimos el header como si no — es solo "usa la mejor URL
  disponible", nunca se inventan parámetros de tracking en el cliente.

**Importante sobre el modo mock**: el fixture `fixtures/ebay_browse_search.sample.json`
es una respuesta REAL capturada SIN campaign id, así que no contiene el campo
`itemAffiliateWebUrl`. Eso significa que el camino de afiliado (preferir
`itemAffiliateWebUrl`) no se puede ejercitar end-to-end en modo mock con el
fixture tal cual; se prueba con mocks de `unittest.mock` que sintetizan un item
con ese campo (ver `pipeline/tests/test_fetch_ebay.py`), y se verá de verdad solo
en modo real, con un campaign ID auténtico de EPN.
"""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
OAUTH_SCOPE = "https://api.ebay.com/oauth/api_scope"
MARKETPLACE_ID = "EBAY_US"

_FIXTURE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "ebay_browse_search.sample.json")

# Timeout corto: este cliente corre en un pipeline programado (GitHub Actions),
# no debe colgarse esperando una red lenta.
_HTTP_TIMEOUT_S = 10
# Reintento simple documentado para 401/429 (ver _request_with_retry):
# - 401 (token inválido/expirado): 1 reintento, pidiendo un token nuevo.
# - 429 (rate limit): 1 reintento tras una espera corta.
# Si el reintento también falla, se cae a mock (nunca se tumba el pipeline).
_MAX_RETRIES = 1
_RETRY_BACKOFF_S = 2


class EbayAuthError(Exception):
    """Fallo autenticando contra eBay (credenciales inválidas, red, etc.)."""


def has_real_credentials() -> bool:
    """True si EBAY_CLIENT_ID y EBAY_CLIENT_SECRET están en el entorno (no vacíos)."""
    return bool(os.environ.get("EBAY_CLIENT_ID")) and bool(os.environ.get("EBAY_CLIENT_SECRET"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------
# Modo real
# --------------------------------------------------------------------------

def get_access_token(client_id: str, client_secret: str) -> str:
    """Pide un token de aplicación por client credentials grant.

    Lanza EbayAuthError si la petición falla (credenciales inválidas, red, etc.)
    para que el llamador decida (reintentar o caer a mock); no la silencia aquí.
    """
    credentials = f"{client_id}:{client_secret}".encode("utf-8")
    basic_auth = base64.b64encode(credentials).decode("ascii")

    body = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "scope": OAUTH_SCOPE,
    }).encode("utf-8")

    req = urllib.request.Request(
        TOKEN_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Basic {basic_auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT_S) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise EbayAuthError(f"token eBay: HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise EbayAuthError(f"token eBay: error de red: {exc}") from exc

    token = payload.get("access_token")
    if not token:
        raise EbayAuthError(f"token eBay: respuesta sin access_token: {payload}")
    return token


def _build_affiliate_header() -> str | None:
    """Construye el valor del header X-EBAY-C-ENDUSERCTX para EPN, o None.

    None (sin header) si EBAY_CAMPAIGN_ID no está en el entorno o está vacío,
    para que sin esa variable el comportamiento sea exactamente el de hoy (sin
    tracking de afiliado, enlaces normales).

    Si además EBAY_REFERENCE_ID está presente, se añade affiliateReferenceId
    separado por coma (mismo header, varios parámetros), como documenta eBay
    para X-EBAY-C-ENDUSERCTX.
    """
    campaign_id = os.environ.get("EBAY_CAMPAIGN_ID")
    if not campaign_id:
        return None

    parts = [f"affiliateCampaignId={campaign_id}"]
    reference_id = os.environ.get("EBAY_REFERENCE_ID")
    if reference_id:
        parts.append(f"affiliateReferenceId={reference_id}")
    return ",".join(parts)


def _do_search_request(part_number_norm: str, token: str, limit: int) -> dict[str, Any]:
    """Una sola llamada GET a item_summary/search. Puede lanzar urllib.error.HTTPError."""
    query = urllib.parse.urlencode({"q": part_number_norm, "limit": limit})
    url = f"{SEARCH_URL}?{query}"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": MARKETPLACE_ID,
    }
    affiliate_header = _build_affiliate_header()
    if affiliate_header:
        headers["X-EBAY-C-ENDUSERCTX"] = affiliate_header
    req = urllib.request.Request(
        url,
        method="GET",
        headers=headers,
    )
    with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT_S) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _search_real(part_number_norm: str, client_id: str, client_secret: str, limit: int) -> dict[str, Any]:
    """Busca en la API real con manejo simple de 401/429.

    - 401: se asume token vencido/invalido -> se pide un token nuevo y se
      reintenta UNA vez.
    - 429: rate limit -> se espera _RETRY_BACKOFF_S y se reintenta UNA vez.
    - Cualquier otro fallo (incluido que el reintento también falle): se
      relanza para que el llamador (search_part) caiga a mock.
    """
    token = get_access_token(client_id, client_secret)

    attempt = 0
    while True:
        try:
            return _do_search_request(part_number_norm, token, limit)
        except urllib.error.HTTPError as exc:
            if attempt >= _MAX_RETRIES:
                raise
            if exc.code == 401:
                token = get_access_token(client_id, client_secret)
                attempt += 1
                continue
            if exc.code == 429:
                time.sleep(_RETRY_BACKOFF_S)
                attempt += 1
                continue
            raise


def _map_item_summary_to_offer(item: dict[str, Any]) -> dict[str, Any]:
    """Convierte un item_summary (real o mock) al shape de `offers` de CONTRACTS.md.

    `url` prefiere `itemAffiliateWebUrl` (la URL con tracking de EPN que eBay exige
    usar para pagar comisión) y cae a `itemWebUrl` si no viene o viene vacía. eBay
    solo devuelve `itemAffiliateWebUrl` cuando la petición llevó un campaign id
    válido (ver `_build_affiliate_header`); sin eso, este campo no existe en la
    respuesta y se usa siempre `itemWebUrl`, igual que antes de T-B5.
    """
    price_obj = item.get("price") or {}
    price_value = price_obj.get("value")
    try:
        price = float(price_value) if price_value is not None else 0.0
    except (TypeError, ValueError):
        price = 0.0

    url = item.get("itemAffiliateWebUrl") or item.get("itemWebUrl") or ""

    # Foto del anuncio (T-B6). eBay ya la devuelve en `image.imageUrl` y hasta ahora
    # se estaba descartando: por eso el sitio no podía enseñar una sola foto de pieza.
    # Se guarda la URL tal cual (no se descarga ni se re-aloja nada, ver legal.md) y
    # puede venir vacía, así que se normaliza a None en vez de dejar "".
    # Defensivo a propósito: si eBay devolviera `image` como texto en vez de objeto,
    # `(item["image"] or {}).get(...)` lanzaría AttributeError y tumbaría el pipeline
    # entero. Sin foto se sigue, que es justo lo que se hacía antes de T-B6.
    imagen = item.get("image")
    image_url = imagen.get("imageUrl") if isinstance(imagen, dict) else None
    if not isinstance(image_url, str) or not image_url:
        image_url = None

    return {
        "store": "eBay",
        "url": url,
        "price": price,
        "currency": price_obj.get("currency") or "USD",
        "condition": item.get("condition"),
        "updated_at": _now_iso(),
        "image": image_url,
    }


# --------------------------------------------------------------------------
# Modo mock
# --------------------------------------------------------------------------

def _load_mock_response(part_number_norm: str) -> dict[str, Any]:
    with open(_FIXTURE_PATH, "r", encoding="utf-8") as f:
        raw_text = f.read()
    # El fixture usa el placeholder {part_number_norm} en title/href para que
    # el mock refleje la búsqueda realmente hecha, no un valor fijo.
    raw_text = raw_text.replace("{part_number_norm}", part_number_norm)
    return json.loads(raw_text)


def _search_mock(part_number_norm: str) -> list[dict[str, Any]]:
    payload = _load_mock_response(part_number_norm)
    items = payload.get("itemSummaries") or []
    return [_map_item_summary_to_offer(item) for item in items]


# --------------------------------------------------------------------------
# API pública
# --------------------------------------------------------------------------

def search_part(part_number_norm: str, limit: int = 50) -> list[dict[str, Any]]:
    """Busca un número de parte en eBay y devuelve una lista de `offers`.

    Modo real solo si EBAY_CLIENT_ID y EBAY_CLIENT_SECRET están en el entorno.
    Si no están, o si el modo real falla (red, credenciales inválidas, 401/429
    persistentes), cae a mock automáticamente: esta función nunca lanza por
    fallos de la API externa, para no tumbar el pipeline.

    Args:
        part_number_norm: número de parte ya normalizado (ver normalize.py).
        limit: máximo de resultados a pedir a eBay (por defecto 50, igual que
            el contrato técnico verificado).

    Returns:
        list[dict] con la forma de `offers` en CONTRACTS.md. Lista vacía si
        part_number_norm está vacío.
    """
    if not part_number_norm:
        return []

    if has_real_credentials():
        client_id = os.environ["EBAY_CLIENT_ID"]
        client_secret = os.environ["EBAY_CLIENT_SECRET"]
        try:
            payload = _search_real(part_number_norm, client_id, client_secret, limit)
            items = payload.get("itemSummaries") or []
            return [_map_item_summary_to_offer(item) for item in items]
        except Exception:
            # Cualquier fallo del modo real (401/429 ya reintentados en
            # _search_real, error de red, credenciales inválidas, JSON
            # inesperado, etc.): fallback documentado a mock para no tumbar
            # el pipeline. Se podría loguear aquí con logging si el pipeline
            # ya tiene un logger central (T-D1).
            return _search_mock(part_number_norm)

    return _search_mock(part_number_norm)


if __name__ == "__main__":
    import sys

    part = sys.argv[1] if len(sys.argv) > 1 else "04152YZZA1"
    mode = "REAL" if has_real_credentials() else "MOCK"
    print(f"[fetch_ebay] modo={mode} part_number_norm={part}")
    for offer in search_part(part):
        print(offer)
