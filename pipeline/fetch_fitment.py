#!/usr/bin/env python3
"""pipeline/fetch_fitment.py — catálogo por fitment (T-B8).

QUÉ HACE
    Para un vehículo concreto y cada categoría de pieza, pide a la Browse API los anuncios
    cuya compatibilidad está DECLARADA para ese vehículo, y guarda los más baratos de cada
    categoría.

POR QUÉ ASÍ (ver docs/piloto-tb7.md, medición del 05/10/2026)
    - `compatibility_filter` + una categoría del árbol de **eBay Motors** (id 100) devuelve
      los anuncios que le quedan a ese vehículo, con `compatibilityMatch` y
      `compatibilityProperties` (año/marca/modelo). Medido: 50/50 EXACT en limpiaparabrisas,
      48/50 en filtros de aire. Gratis, dentro de la cuota.
    - Las categorías del árbol general NO sirven: la API responde "does not support fitment".
    - **El número de parte NO se obtiene** por esta vía (ni el campo `mpn` en los anuncios, ni
      la Catalog API, que responde 403 incluso en sandbox). Por eso el sitio no promete el
      número: manda al diagrama oficial (`epc_link`) para confirmarlo. No cambiar esto sin
      volver a medir.
    - **Cobertura medida**: funciona en modelos del mercado estadounidense y en modelos que los
      vendedores cubren globalmente (el Hilux respondió con 47 EXACT). NO hay datos para
      modelos exclusivos de otros mercados (un Corolla Axio japonés dio 0). Si se añaden
      vehículos, comprobar primero con tb8_cobertura.

CÓMO SE USA
    from fetch_fitment import build_fitment
    build_fitment(vehiculos, limite_por_categoria=25)  ->  data/build/fitment.json
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

# Categorías del árbol de eBay Motors (100). **Cada id se eligió midiendo**: se pide al
# árbol su sugerencia y se comprueba con una búsqueda real que devuelva anuncios con
# `compatibilityMatch`. No se adivina ninguno. Comprobados el 05/10/2026:
#   179852 limpiaparabrisas 15/15 EXACT · 33659 filtro de aire 12/12 · 33559 frenos 50/50
#   33590 amortiguadores 47/62 · 33602 radiador 6/8 · 174072 bujías 8/8
#
# Y la limitación medida: **no todo tipo de pieza tiene categoría con fitment en eBay**.
# El filtro de aceite (33660) y las baterías (33675, 179846) devuelven CERO anuncios en
# todas las categorías candidatas: por esa vía no se pueden cubrir. Si se añade una
# categoría nueva, comprobar primero que devuelva EXACT — si no, solo gasta cuota.
CATEGORIAS = [
    {"slug": "limpiaparabrisas", "nombre": "Limpiaparabrisas", "category_id": "179852"},
    {"slug": "filtro-aire", "nombre": "Filtro de aire", "category_id": "33659"},
    {"slug": "pastillas-freno", "nombre": "Frenos", "category_id": "33559"},
    {"slug": "amortiguadores", "nombre": "Amortiguadores y resortes", "category_id": "33590"},
    {"slug": "radiador", "nombre": "Radiador", "category_id": "33602"},
    {"slug": "bujias", "nombre": "Bujías", "category_id": "174072"},
]

SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
MAX_LIMIT = 200  # máximo que acepta la API por llamada
_RETRY_BACKOFF_S = 5


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_access_token(client_id: str, client_secret: str) -> str:
    """Token OAuth de aplicación (mismo esquema que usa fetch_ebay.py)."""
    import base64

    datos = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope"}).encode()
    cred = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    req = urllib.request.Request(
        "https://api.ebay.com/identity/v1/oauth2/token", data=datos,
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "Authorization": "Basic " + cred})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["access_token"]


def _buscar(token: str, anio: Any, marca: str, modelo: str, category_id: str,
            limite: int = MAX_LIMIT) -> dict[str, Any]:
    """Una llamada a la Browse API con compatibility_filter."""
    """Una llamada a la Browse API con compatibility_filter."""
    params = {
        "q": "parts",
        "category_ids": category_id,
        "compatibility_filter": f"Year:{anio};Make:{marca};Model:{modelo}",
        "limit": str(min(limite, MAX_LIMIT)),
    }
    url = SEARCH_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/json",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_MOTORS_US"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _a_oferta(item: dict[str, Any]) -> dict[str, Any]:
    """Un anuncio compatible -> forma de oferta de fitment (subconjunto estable y pequeño)."""
    precio = item.get("price") or {}
    crudo = precio.get("value")
    valor = None
    if isinstance(crudo, (int, float, str)) and str(crudo).strip():
        try:
            valor = float(crudo)
        except (TypeError, ValueError):
            valor = None
    imagen = item.get("image")
    return {
        "titulo": (item.get("title") or "")[:180],
        "url": item.get("itemWebUrl") or "",
        "precio": valor,
        "moneda": precio.get("currency") or "USD",
        "condicion": item.get("condition"),
        "compatibilidad": item.get("compatibilityMatch"),
        "foto": (imagen or {}).get("imageUrl") if isinstance(imagen, dict) else None,
        "item_id": item.get("itemId"),
    }


def buscar_categoria(token: str, vehiculo: dict[str, Any], categoria: dict[str, Any],
                     limite_por_categoria: int = 25) -> dict[str, Any]:
    """Los anuncios que le quedan EXACTOS a un vehículo en una categoría, los más baratos.

    Se piden hasta 200 (el máximo de la API) y se conservan los `limite_por_categoria` más
    baratos: el sitio enseña las mejores opciones, no un volcado de 200.
    """
    anio = vehiculo.get("year")
    marca = str(vehiculo.get("make") or "")
    modelo = str(vehiculo.get("model") or "")
    try:
        respuesta = _buscar(token, anio, marca, modelo, categoria["category_id"])
    except urllib.error.HTTPError as e:
        return {"slug": categoria["slug"], "nombre": categoria["nombre"],
                "category_id": categoria["category_id"], "error": f"HTTP {e.code}",
                "total_en_ebay": 0, "exactos": 0, "ofertas": []}
    except Exception as e:  # red, JSON inesperado...: no tumba el build
        return {"slug": categoria["slug"], "nombre": categoria["nombre"],
                "category_id": categoria["category_id"], "error": type(e).__name__,
                "total_en_ebay": 0, "exactos": 0, "ofertas": []}

    items = respuesta.get("itemSummaries") or []
    exactos = [i for i in items if i.get("compatibilityMatch") == "EXACT"]
    ofertas = [_a_oferta(i) for i in exactos]
    ofertas.sort(key=lambda o: (o["precio"] is None, o["precio"] or 0))
    return {
        "slug": categoria["slug"],
        "nombre": categoria["nombre"],
        "category_id": categoria["category_id"],
        "total_en_ebay": respuesta.get("total", 0),
        "leidos": len(items),
        "exactos": len(exactos),
        "ofertas": ofertas[:limite_por_categoria],
    }


def build_fitment(vehiculos: list[dict[str, Any]], categorias: list[dict[str, Any]] | None = None,
                  limite_por_categoria: int = 25, token: str | None = None
                  ) -> dict[str, Any]:
    """Construye el catálogo por fitment de una lista de vehículos."""
    categorias = categorias if categorias is not None else CATEGORIAS
    if token is None:
        token = get_access_token(os.environ["EBAY_CLIENT_ID"], os.environ["EBAY_CLIENT_SECRET"])

    por_vehiculo = []
    for v in vehiculos:
        categorias_vehiculo = [buscar_categoria(token, v, c, limite_por_categoria) for c in categorias]
        con_ofertas = [c for c in categorias_vehiculo if c.get("ofertas")]
        por_vehiculo.append({
            "vehiculo_id": v.get("id"),
            "make": v.get("make"), "model": v.get("model"), "year": v.get("year"),
            "categorias": categorias_vehiculo,
            "categorias_con_ofertas": len(con_ofertas),
            "ofertas_totales": sum(len(c["ofertas"]) for c in categorias_vehiculo),
        })

    return {
        "updated_at": _now_iso(),
        "fuente": "eBay Browse API (compatibility_filter, árbol de eBay Motors)",
        "nota_numero_de_parte": ("Esta fuente NO da el número de parte; solo la compatibilidad. "
                                 "El número se confirma en el diagrama oficial (epc_link)."),
        "vehiculos": por_vehiculo,
    }


if __name__ == "__main__":
    import sys

    ruta_vehiculos = sys.argv[1] if len(sys.argv) > 1 else "data/build/vehicles.json"
    ruta_salida = sys.argv[2] if len(sys.argv) > 2 else "data/build/fitment.json"
    with open(ruta_vehiculos, encoding="utf-8") as f:
        vehiculos = json.load(f)
    datos = build_fitment(vehiculos)
    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
    for v in datos["vehiculos"]:
        print(f"[fitment] {v['make']} {v['model']} {v['year']}: "
              f"{v['categorias_con_ofertas']} categorías con ofertas, {v['ofertas_totales']} ofertas")
    print(f"[fitment] guardado en {ruta_salida}")
