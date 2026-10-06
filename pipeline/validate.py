"""validate.py — T-D1 (Agente D: Pipeline-Build)

Validador standalone de los 4 archivos de `data/build/` contra el esquema
de CONTRACTS.md. Sin dependencias externas (solo stdlib) para poder correr
en CI (T-G1) sin instalar nada extra.

Uso:
    python pipeline/validate.py

Exit code:
    0  -> los 4 archivos existen y cumplen el esquema.
    1  -> falta al menos un archivo, no es JSON válido, o algún objeto no
          cumple el esquema (clave faltante, tipo incorrecto, etc.). Los
          errores encontrados se imprimen en stderr, uno por línea.
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from normalize import normalize_part_number  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_DIR = os.path.join(REPO_ROOT, "data", "build")

_VALID_PART_TYPES = {"OEM", "AFTERMARKET"}
_VALID_EPC_SOURCES = {"7zap", "partsouq", "oem-store", None}
_VALID_IMAGE_SOURCES = {"ebay", "generic"}

# ISO-8601 básico (lo que usan todos los módulos del proyecto: terminado en Z).
_ISO8601_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$"
)


class ValidationErrors(list):
    """Lista de mensajes de error, con helpers para acumular con contexto."""

    def add(self, contexto: str, mensaje: str) -> None:
        self.append(f"{contexto}: {mensaje}")


def _load_json(nombre: str, errores: ValidationErrors) -> Any:
    ruta = os.path.join(BUILD_DIR, nombre)
    if not os.path.isfile(ruta):
        errores.add(nombre, f"no existe en {BUILD_DIR}")
        return None
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        errores.add(nombre, f"no es JSON válido: {exc}")
        return None


def _check_type(contexto: str, valor: Any, tipos, campo: str, errores: ValidationErrors, obligatorio: bool = True) -> bool:
    """Devuelve True si el campo existe (cuando obligatorio) y tiene el tipo esperado."""
    if campo not in valor:
        if obligatorio:
            errores.add(contexto, f"falta la clave requerida '{campo}'")
        return False
    dato = valor[campo]
    if not isinstance(dato, tipos):
        nombres = tipos.__name__ if isinstance(tipos, type) else " | ".join(t.__name__ for t in tipos)
        errores.add(contexto, f"'{campo}' debería ser {nombres}, es {type(dato).__name__}")
        return False
    return True


# ---------------------------------------------------------------------------
# parts.json
# ---------------------------------------------------------------------------

_PART_REQUIRED_KEYS = {
    "id", "part_number", "part_number_norm", "type", "brand", "name",
    "category", "epc_link", "image", "equivalents", "fitment_ids",
    "offers", "updated_at",
}

# other_names (CONTRACTS.md, agregado 04/10/2026) es OPCIONAL a propósito:
# no está en _PART_REQUIRED_KEYS y no se exige como clave faltante. Pero SI
# existe en una parte, debe ser list[str] (ver _validate_other_names). El
# build (build_index.py) siempre la deja presente como [] por defecto, pero
# validate.py no debe fallar datos de seed/parts.json de otros orígenes que
# todavía no la incluyan.

_OFFER_REQUIRED_KEYS = {"store", "url", "price", "currency", "condition", "updated_at"}


def _validate_offer(contexto: str, offer: Any, errores: ValidationErrors) -> None:
    if not isinstance(offer, dict):
        errores.add(contexto, f"oferta debería ser un objeto, es {type(offer).__name__}")
        return

    faltantes = _OFFER_REQUIRED_KEYS - offer.keys()
    if faltantes:
        errores.add(contexto, f"oferta sin claves requeridas: {sorted(faltantes)}")

    if "store" in offer and not isinstance(offer["store"], str):
        errores.add(contexto, "oferta.store debería ser str")
    if "url" in offer and not isinstance(offer["url"], str):
        errores.add(contexto, "oferta.url debería ser str")
    if "price" in offer and not isinstance(offer["price"], (int, float)):
        errores.add(contexto, "oferta.price debería ser numérico")
    if "currency" in offer and not isinstance(offer["currency"], str):
        errores.add(contexto, "oferta.currency debería ser str")
    if "condition" in offer and offer["condition"] is not None and not isinstance(offer["condition"], str):
        errores.add(contexto, "oferta.condition debería ser str|null")
    if "image" in offer:
        img = offer["image"]
        if img is not None:
            if not isinstance(img, str):
                errores.add(contexto, "offer.image debería ser str|null")
            elif not img.startswith("http"):
                errores.add(contexto, f"offer.image debería ser una URL http(s), es {img[:40]!r}")
    if "updated_at" in offer:
        if not isinstance(offer["updated_at"], str) or not _ISO8601_RE.match(offer["updated_at"]):
            errores.add(contexto, f"oferta.updated_at '{offer.get('updated_at')!r}' no es ISO-8601")


def _validate_epc_link(contexto: str, epc_link: Any, errores: ValidationErrors) -> None:
    # CONTRACTS.md / regla transversal: epc_link es OBLIGATORIO como clave,
    # aunque su url (y source) puedan ser null. Aquí se valida justamente eso.
    if not isinstance(epc_link, dict):
        errores.add(contexto, f"epc_link debería ser un objeto, es {type(epc_link).__name__}")
        return

    if "source" not in epc_link:
        errores.add(contexto, "epc_link sin la clave 'source' (debe existir aunque sea null)")
    elif epc_link["source"] not in _VALID_EPC_SOURCES:
        errores.add(
            contexto,
            f"epc_link.source '{epc_link['source']!r}' no es 7zap|partsouq|oem-store|null",
        )

    if "url" not in epc_link:
        errores.add(contexto, "epc_link sin la clave 'url' (debe existir aunque sea null)")
    elif epc_link["url"] is not None and not isinstance(epc_link["url"], str):
        errores.add(contexto, "epc_link.url debería ser str|null")


def _validate_image(contexto: str, image: Any, errores: ValidationErrors) -> None:
    if not isinstance(image, dict):
        errores.add(contexto, f"image debería ser un objeto, es {type(image).__name__}")
        return
    for campo in ("url", "source", "credit"):
        if campo not in image:
            errores.add(contexto, f"image sin la clave '{campo}'")
    if "url" in image and image["url"] is not None and not isinstance(image["url"], str):
        errores.add(contexto, "image.url debería ser str|null")
    if "source" in image and image["source"] not in _VALID_IMAGE_SOURCES:
        errores.add(contexto, f"image.source '{image.get('source')!r}' no es ebay|generic")
    if "credit" in image and image["credit"] is not None and not isinstance(image["credit"], str):
        errores.add(contexto, "image.credit debería ser str|null")


def validate_parts(data: Any, errores: ValidationErrors) -> None:
    if not isinstance(data, list):
        errores.add("parts.json", f"debería ser una lista, es {type(data).__name__}")
        return

    ids_vistos: set[str] = set()
    for i, parte in enumerate(data):
        contexto = f"parts.json[{i}]"
        if not isinstance(parte, dict):
            errores.add(contexto, f"debería ser un objeto, es {type(parte).__name__}")
            continue

        faltantes = _PART_REQUIRED_KEYS - parte.keys()
        if faltantes:
            errores.add(contexto, f"faltan claves requeridas: {sorted(faltantes)}")

        pid = parte.get("id")
        if not isinstance(pid, str) or not pid:
            errores.add(contexto, "'id' debería ser str no vacío")
        elif pid in ids_vistos:
            errores.add(contexto, f"'id' duplicado: {pid!r}")
        else:
            ids_vistos.add(pid)

        contexto_id = f"parts.json[{pid or i}]"

        _check_type(contexto_id, parte, str, "part_number", errores)
        _check_type(contexto_id, parte, str, "part_number_norm", errores)
        _check_type(contexto_id, parte, str, "brand", errores)
        _check_type(contexto_id, parte, str, "name", errores)
        _check_type(contexto_id, parte, str, "category", errores)
        _check_type(contexto_id, parte, str, "updated_at", errores)

        if "type" in parte and parte["type"] not in _VALID_PART_TYPES:
            errores.add(contexto_id, f"'type' debería ser OEM|AFTERMARKET, es {parte.get('type')!r}")

        if "updated_at" in parte and isinstance(parte["updated_at"], str):
            if not _ISO8601_RE.match(parte["updated_at"]):
                errores.add(contexto_id, f"'updated_at' {parte['updated_at']!r} no es ISO-8601")

        # Regla de normalización (CONTRACTS.md): part_number_norm debe ser
        # EXACTAMENTE normalize_part_number(part_number). No basta con que
        # "parezca" normalizado: se recalcula y se compara.
        if isinstance(parte.get("part_number"), str) and isinstance(parte.get("part_number_norm"), str):
            esperado = normalize_part_number(parte["part_number"])
            if parte["part_number_norm"] != esperado:
                errores.add(
                    contexto_id,
                    f"'part_number_norm' {parte['part_number_norm']!r} no coincide con "
                    f"normalize_part_number(part_number)={esperado!r}",
                )

        if "epc_link" in parte:
            _validate_epc_link(contexto_id, parte["epc_link"], errores)
        else:
            errores.add(contexto_id, "falta la clave requerida 'epc_link'")

        if "image" in parte:
            _validate_image(contexto_id, parte["image"], errores)

        if "equivalents" in parte:
            if not isinstance(parte["equivalents"], list) or not all(isinstance(x, str) for x in parte["equivalents"]):
                errores.add(contexto_id, "'equivalents' debería ser list[str]")

        if "fitment_ids" in parte:
            if not isinstance(parte["fitment_ids"], list) or not all(isinstance(x, str) for x in parte["fitment_ids"]):
                errores.add(contexto_id, "'fitment_ids' debería ser list[str]")

        if "other_names" in parte:
            if not isinstance(parte["other_names"], list) or not all(isinstance(x, str) for x in parte["other_names"]):
                errores.add(contexto_id, "'other_names' debería ser list[str]")

        if "offers" in parte:
            if not isinstance(parte["offers"], list):
                errores.add(contexto_id, "'offers' debería ser una lista")
            else:
                for j, offer in enumerate(parte["offers"]):
                    _validate_offer(f"{contexto_id}.offers[{j}]", offer, errores)


# ---------------------------------------------------------------------------
# vehicles.json
# ---------------------------------------------------------------------------

_VEHICLE_REQUIRED_KEYS = {"id", "make", "model", "year", "trim", "engine"}


def validate_vehicles(data: Any, errores: ValidationErrors) -> None:
    if not isinstance(data, list):
        errores.add("vehicles.json", f"debería ser una lista, es {type(data).__name__}")
        return

    ids_vistos: set[str] = set()
    for i, vehiculo in enumerate(data):
        contexto = f"vehicles.json[{i}]"
        if not isinstance(vehiculo, dict):
            errores.add(contexto, f"debería ser un objeto, es {type(vehiculo).__name__}")
            continue

        faltantes = _VEHICLE_REQUIRED_KEYS - vehiculo.keys()
        if faltantes:
            errores.add(contexto, f"faltan claves requeridas: {sorted(faltantes)}")

        vid = vehiculo.get("id")
        if not isinstance(vid, str) or not vid:
            errores.add(contexto, "'id' debería ser str no vacío")
        elif vid in ids_vistos:
            errores.add(contexto, f"'id' duplicado: {vid!r}")
        else:
            ids_vistos.add(vid)

        contexto_id = f"vehicles.json[{vid or i}]"
        _check_type(contexto_id, vehiculo, str, "make", errores)
        _check_type(contexto_id, vehiculo, str, "model", errores)
        _check_type(contexto_id, vehiculo, int, "year", errores)

        if "trim" in vehiculo and vehiculo["trim"] is not None and not isinstance(vehiculo["trim"], str):
            errores.add(contexto_id, "'trim' debería ser str|null")
        if "engine" in vehiculo and vehiculo["engine"] is not None and not isinstance(vehiculo["engine"], str):
            errores.add(contexto_id, "'engine' debería ser str|null")


# ---------------------------------------------------------------------------
# search_index.json
# ---------------------------------------------------------------------------

_SEARCH_INDEX_REQUIRED_KEYS = {"id", "part_number_norm", "name", "brand"}


def validate_search_index(data: Any, errores: ValidationErrors) -> None:
    if not isinstance(data, list):
        errores.add("search_index.json", f"debería ser una lista, es {type(data).__name__}")
        return

    for i, entrada in enumerate(data):
        contexto = f"search_index.json[{i}]"
        if not isinstance(entrada, dict):
            errores.add(contexto, f"debería ser un objeto, es {type(entrada).__name__}")
            continue

        faltantes = _SEARCH_INDEX_REQUIRED_KEYS - entrada.keys()
        if faltantes:
            errores.add(contexto, f"faltan claves requeridas: {sorted(faltantes)}")

        eid = entrada.get("id")
        contexto_id = f"search_index.json[{eid or i}]"
        _check_type(contexto_id, entrada, str, "id", errores)
        _check_type(contexto_id, entrada, str, "part_number_norm", errores)
        _check_type(contexto_id, entrada, str, "name", errores)
        _check_type(contexto_id, entrada, str, "brand", errores)

        if isinstance(entrada.get("part_number_norm"), str):
            esperado = normalize_part_number(entrada["part_number_norm"])
            if entrada["part_number_norm"] != esperado:
                errores.add(
                    contexto_id,
                    f"'part_number_norm' {entrada['part_number_norm']!r} no está normalizado "
                    f"(normalize_part_number lo cambiaría a {esperado!r})",
                )


# ---------------------------------------------------------------------------
# categories.json
# ---------------------------------------------------------------------------

_CATEGORY_REQUIRED_KEYS = {"slug", "name_es", "svg"}


def validate_categories(data: Any, errores: ValidationErrors) -> None:
    if not isinstance(data, list):
        errores.add("categories.json", f"debería ser una lista, es {type(data).__name__}")
        return

    slugs_vistos: set[str] = set()
    for i, categoria in enumerate(data):
        contexto = f"categories.json[{i}]"
        if not isinstance(categoria, dict):
            errores.add(contexto, f"debería ser un objeto, es {type(categoria).__name__}")
            continue

        faltantes = _CATEGORY_REQUIRED_KEYS - categoria.keys()
        if faltantes:
            errores.add(contexto, f"faltan claves requeridas: {sorted(faltantes)}")

        slug = categoria.get("slug")
        contexto_id = f"categories.json[{slug or i}]"
        _check_type(contexto_id, categoria, str, "slug", errores)
        _check_type(contexto_id, categoria, str, "name_es", errores)
        _check_type(contexto_id, categoria, str, "svg", errores)

        if isinstance(slug, str):
            if slug in slugs_vistos:
                errores.add(contexto_id, f"'slug' duplicado: {slug!r}")
            slugs_vistos.add(slug)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def validate_referential_integrity(
    parts: Any, vehicles: Any, categories: Any, errores: ValidationErrors
) -> None:
    """Integridad referencial ENTRE archivos (T-D5).

    `validate_parts`/`validate_vehicles`/`validate_categories` solo validan la
    FORMA de cada archivo por separado; esto valida que las referencias que
    cruzan archivos realmente existan:

    - `parts.json[*].category` debe existir como `slug` en `categories.json`.
      (Bug real detectado en Ronda 4: `MR297182` usaba `clip-parachoques`, que
      nunca existió en `categories.json` — la parte quedaba invisible en toda
      navegación por categoría sin que `validate.py` lo detectara.)
    - `parts.json[*].fitment_ids[*]` debe existir como `id` en `vehicles.json`
      (una lista vacía sigue siendo válida: significa "no fijado a un
      vehículo concreto").

    Requiere que los tres argumentos ya sean listas (llamar solo cuando
    `_load_json` no devolvió None para ninguno de los tres).
    """
    if not isinstance(categories, list):
        return
    if not isinstance(parts, list):
        return

    slugs_validos: set[str] = {
        c.get("slug") for c in categories if isinstance(c, dict) and isinstance(c.get("slug"), str)
    }
    ids_vehiculos_validos: set[str] = set()
    if isinstance(vehicles, list):
        ids_vehiculos_validos = {
            v.get("id") for v in vehicles if isinstance(v, dict) and isinstance(v.get("id"), str)
        }

    for i, parte in enumerate(parts):
        if not isinstance(parte, dict):
            continue
        pid = parte.get("id")
        contexto_id = f"parts.json[{pid or i}]"

        categoria = parte.get("category")
        if isinstance(categoria, str) and categoria not in slugs_validos:
            errores.add(
                contexto_id,
                f"'category' {categoria!r} no existe en categories.json (slug huérfano: "
                "la parte no aparecería en ninguna categoría del sitio)",
            )

        fitment_ids = parte.get("fitment_ids")
        if isinstance(fitment_ids, list):
            for fid in fitment_ids:
                if isinstance(fid, str) and fid not in ids_vehiculos_validos:
                    errores.add(
                        contexto_id,
                        f"'fitment_ids' referencia {fid!r}, que no existe en vehicles.json",
                    )


def validate_fitment(errores: ValidationErrors) -> None:
    """Valida `fitment.json` (T-B8) **si existe**. Es opcional a propósito: un build sin
    credenciales de eBay no lo genera, y eso no debe romper la validación.

    Las reglas que importan: solo entran ofertas con compatibilidad **EXACT** (prometer
    "le queda" con un `POSSIBLE` sería mentir), los enlaces tienen que ser de eBay, y la
    nota que aclara que esta fuente NO da el número de parte tiene que estar presente.
    """
    ruta = os.path.join(BUILD_DIR, "fitment.json")
    if not os.path.exists(ruta):
        return

    try:
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        errores.add("fitment.json", f"no se pudo leer o parsear: {exc}")
        return

    if not isinstance(datos, dict):
        errores.add("fitment.json", "debería ser un objeto")
        return

    for clave in ("updated_at", "vehiculos", "nota_numero_de_parte"):
        if clave not in datos:
            errores.add("fitment.json", f"falta la clave '{clave}'")
    if isinstance(datos.get("nota_numero_de_parte"), str):
        if "número de parte" not in datos["nota_numero_de_parte"]:
            errores.add("fitment.json", "'nota_numero_de_parte' debería aclarar qué NO da esta fuente")
    else:
        errores.add("fitment.json", "'nota_numero_de_parte' debería ser texto")

    vehiculos = datos.get("vehiculos")
    if not isinstance(vehiculos, list):
        errores.add("fitment.json", "'vehiculos' debería ser una lista")
        return

    for i, v in enumerate(vehiculos):
        ctx = f"fitment.json[{i}]"
        if not isinstance(v, dict):
            errores.add(ctx, "cada vehículo debería ser un objeto")
            continue
        for clave in ("vehiculo_id", "make", "model", "year", "categorias"):
            if clave not in v:
                errores.add(ctx, f"falta la clave '{clave}'")
        for cat in (v.get("categorias") or []):
            cctx = f"{ctx}.categorias[{cat.get('slug') if isinstance(cat, dict) else '?'}]"
            if not isinstance(cat, dict):
                errores.add(cctx, "cada categoría debería ser un objeto")
                continue
            for clave in ("slug", "category_id", "total_en_ebay", "exactos", "ofertas"):
                if clave not in cat:
                    errores.add(cctx, f"falta la clave '{clave}'")
            if "error" in cat and cat.get("ofertas"):
                errores.add(cctx, "una categoría con error no debería traer ofertas")
            for j, of in enumerate(cat.get("ofertas") or []):
                octx = f"{cctx}.ofertas[{j}]"
                if not isinstance(of, dict):
                    errores.add(octx, "cada oferta debería ser un objeto")
                    continue
                if of.get("compatibilidad") != "EXACT":
                    errores.add(octx, f"compatibilidad {of.get('compatibilidad')!r}: solo se aceptan EXACT")
                url = of.get("url")
                if not isinstance(url, str) or "ebay.com/itm/" not in url:
                    errores.add(octx, f"url debería ser un enlace de eBay, es {str(url)[:50]!r}")
                precio = of.get("precio")
                if precio is not None and not isinstance(precio, (int, float)):
                    errores.add(octx, "precio debería ser número o null")


def run_validation() -> ValidationErrors:
    errores = ValidationErrors()

    parts = _load_json("parts.json", errores)
    vehicles = _load_json("vehicles.json", errores)
    search_index = _load_json("search_index.json", errores)
    categories = _load_json("categories.json", errores)

    if parts is not None:
        validate_parts(parts, errores)
    if vehicles is not None:
        validate_vehicles(vehicles, errores)
    if search_index is not None:
        validate_search_index(search_index, errores)
    if categories is not None:
        validate_categories(categories, errores)

    if parts is not None and categories is not None:
        validate_referential_integrity(parts, vehicles, categories, errores)

    validate_fitment(errores)

    return errores


def main() -> int:
    errores = run_validation()
    if errores:
        print(f"[validate] {len(errores)} error(es) encontrados en {BUILD_DIR}:", file=sys.stderr)
        for e in errores:
            print(f"  - {e}", file=sys.stderr)
        return 1

    extra = " + fitment.json (T-B8)" if os.path.exists(os.path.join(BUILD_DIR, "fitment.json")) else ""
    print(f"[validate] OK: los 4 archivos de {BUILD_DIR} cumplen CONTRACTS.md{extra}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
