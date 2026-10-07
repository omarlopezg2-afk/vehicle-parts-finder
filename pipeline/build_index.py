"""build_index.py — T-D1 (Agente D: Pipeline-Build)

Une las salidas de:
  - fetch_vehicles.py (T-A1) -> vehicles.json
  - fetch_ebay.py (T-B1) + normalize.py (T-B2) -> offers y part_number_norm
    dentro de parts.json
  - fetch_epc_links.py (T-C1) -> epc_link dentro de parts.json
  - data/seed/*.json -> catálogo base de partes (campos que ningún fetch_*
    resuelve: id, part_number, type, brand, name, category, equivalents,
    fitment_ids, image, other_names)

y escribe los 4 archivos de `data/build/` que exige CONTRACTS.md: parts.json,
vehicles.json, search_index.json, categories.json.

MODO COMPLETAMENTE MOCK (sin red, sin llaves de eBay)
------------------------------------------------------
Este script SIEMPRE puede correr sin internet y sin EBAY_CLIENT_ID/SECRET:

- `fetch_ebay.search_part` ya cae a modo mock solo (fixture local) cuando no
  hay llaves en el entorno, sin tocar la red (T-B1).
- `fetch_epc_links.get_epc_links` nunca hace peticiones de red: solo
  construye URLs en memoria (T-C1).
- `fetch_vehicles.fetch_vehicle` SÍ intenta una llamada real a vPIC (es su
  diseño, T-A1, API pública sin llave). Si no hay red, lanza una excepción
  de red o un timeout, o `fetch_vehicle` devuelve un dict con `error` no
  nulo. build_vehicles() captura ambos casos y usa un **fallback offline**
  fijo (_FALLBACK_VEHICLE, mismos datos que ya usan los tests de T-A1 para
  el Outlander Sport 2020) para que el build nunca falle por falta de
  conectividad.

Uso:
    python pipeline/build_index.py

Ejecutar `pipeline/validate.py` después (o antes del commit) para confirmar
que los 4 JSON generados cumplen CONTRACTS.md.
"""

from __future__ import annotations

import glob
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fetch_ebay import search_part  # noqa: E402
from fetch_epc_links import get_epc_links  # noqa: E402
from fetch_vehicles import fetch_vehicle  # noqa: E402
from normalize import normalize_part_number  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED_DIR = os.path.join(REPO_ROOT, "data", "seed")
BUILD_DIR = os.path.join(REPO_ROOT, "data", "build")

# VIN de ejemplo: el Mitsubishi Outlander Sport 2020 real de Omar (el caso
# de prueba del proyecto, ver PLAN.md). Resuelto en vivo contra vPIC el
# 03/10/2026: Make=MITSUBISHI, Model=Outlander Sport, ModelYear=2020,
# DisplacementL=2, EngineCylinders=4, EngineHP=148, EngineModel=MIVEC.
# Antes de este cambio se usaba un VIN distinto (JA4AP3AU0LU000302, el que
# usan los tests de T-A1 en pipeline/tests/test_fetch_vehicles.py) — ese
# VIN sigue siendo válido para los tests, pero el build real debe usar el
# VIN de Omar para que el sitio publicado lo encuentre al probarlo.
EXAMPLE_VIN = "JA4AP4AU3LU023739"

# Fallback 100% offline si vPIC no responde (sin red / timeout / caído).
# Datos tomados de la resolución real conocida de este mismo VIN (ver arriba).
# Es una aproximación fija, no una llamada real a vPIC — se documenta en el
# PR como supuesto.
_FALLBACK_VEHICLE: dict[str, Any] = {
    "id": f"vin-{EXAMPLE_VIN}",
    "make": "Mitsubishi",
    "model": "Outlander Sport",
    "year": 2020,
    "trim": None,
    "engine": "2.0L 4cil Gasoline 148HP (MIVEC)",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Carga del seed
# ---------------------------------------------------------------------------

def _load_seed_parts() -> list[dict[str, Any]]:
    """Carga todas las partes de `data/seed/*.json` (puede haber más de un
    archivo seed; T-D1 puede ampliar `parts.sample.json` o agregar otros).

    Valida que cada parte tenga `id` y que no haya ids duplicados entre
    archivos, para no fallar silenciosamente más adelante en build_parts.
    """
    partes: list[dict[str, Any]] = []
    vistos: set[str] = set()

    rutas = sorted(glob.glob(os.path.join(SEED_DIR, "*.json")))
    if not rutas:
        raise FileNotFoundError(f"No se encontró ningún archivo *.json en {SEED_DIR}")

    for ruta in rutas:
        with open(ruta, "r", encoding="utf-8") as f:
            contenido = json.load(f)
        if not isinstance(contenido, list):
            raise ValueError(f"{ruta}: se esperaba una lista de partes en el seed.")
        for parte in contenido:
            if not isinstance(parte, dict):
                raise ValueError(f"{ruta}: cada parte del seed debe ser un objeto.")
            pid = parte.get("id")
            if not pid:
                raise ValueError(f"{ruta}: una parte del seed no tiene 'id'.")
            if pid in vistos:
                raise ValueError(f"{ruta}: id de parte duplicado '{pid}'.")
            vistos.add(pid)
            partes.append(parte)

    return partes


# ---------------------------------------------------------------------------
# vehicles.json (T-A1)
# ---------------------------------------------------------------------------

def build_vehicles() -> list[dict[str, Any]]:
    """Resuelve el VIN de ejemplo vía vPIC (fetch_vehicle, T-A1).

    Si vPIC no responde (sin red, timeout, HTTP error) o devuelve un VIN no
    reconocido, usa `_FALLBACK_VEHICLE` para que el build nunca falle por
    falta de conectividad (requisito de T-D1: modo completamente mock).
    """
    try:
        resultado = fetch_vehicle(EXAMPLE_VIN)
    except Exception:
        # fetch_vehicle(T-A1) está diseñado para no lanzar nunca, pero este
        # build se defiende igual por si cambia esa garantía en el futuro.
        resultado = None

    if resultado is None or resultado.get("error"):
        datos = dict(_FALLBACK_VEHICLE)
    else:
        datos = {
            "id": resultado["id"],
            "make": resultado["make"],
            "model": resultado["model"],
            "year": resultado["year"],
            "trim": resultado.get("trim"),
            "engine": resultado.get("engine"),
        }

    return [datos]


# ---------------------------------------------------------------------------
# parts.json (seed + T-B1/T-B2 + T-C1)
# ---------------------------------------------------------------------------

def _resolve_epc_link(
    parte: dict[str, Any],
    vehiculo_ejemplo: dict[str, Any],
    part_number_norm: str,
) -> dict[str, Any]:
    """Resuelve `epc_link` para una parte usando el vehículo de ejemplo del
    build (get_epc_links, T-C1).

    Supuesto documentado: como el seed todavía no trae `fitment` real por
    vehículo, todas las partes se resuelven contra el único vehículo de
    ejemplo del build (Outlander Sport 2020). Si la marca de la parte
    coincide con la del vehículo de ejemplo, se pasa también su VIN real
    para mejorar la precisión del link de Partsouq; para partes de otras
    marcas (ej. Toyota en el seed) no se asume ningún VIN, solo
    marca/modelo/categoría/número de parte — get_epc_links (T-C1) nunca
    inventa una URL sin base real, así que puede devolver una lista vacía
    (epc_link queda con `source`/`url` en null, que sigue siendo válido
    contra CONTRACTS.md).
    """
    make = parte.get("brand") or vehiculo_ejemplo.get("make")
    vin = vehiculo_ejemplo.get("vin") if make == vehiculo_ejemplo.get("make") else None

    try:
        links = get_epc_links(
            make,
            vehiculo_ejemplo.get("model"),
            vehiculo_ejemplo.get("year"),
            parte.get("category"),
            vin=vin,
            part_number_norm=part_number_norm,
        )
    except Exception:
        # get_epc_links (T-C1) no hace red y no debería lanzar, pero este
        # build nunca debe caerse por una pieza con datos raros en el seed.
        links = []

    if links:
        primero = links[0]
        return {"source": primero.get("source"), "url": primero.get("url")}
    return {"source": None, "url": None}


def _resolve_offers(part_number_norm: str) -> list[dict[str, Any]]:
    """Busca ofertas en eBay (fetch_ebay.search_part, T-B1).

    search_part ya cae a modo mock sin llaves ni red; esta capa solo se
    defiende de errores imprevistos para que una parte nunca tumbe todo el
    build.
    """
    try:
        return search_part(part_number_norm)
    except Exception:
        return []


def build_parts(vehiculo_ejemplo: dict[str, Any]) -> list[dict[str, Any]]:
    seed_partes = _load_seed_parts()
    build_time = _now_iso()

    # vehicles.json (esquema público de CONTRACTS.md) no incluye el VIN;
    # para resolver epc_link con la mejor precisión posible lo agregamos
    # aquí, solo para uso interno de este módulo.
    vehiculo_con_vin = dict(vehiculo_ejemplo)
    vehiculo_con_vin["vin"] = EXAMPLE_VIN

    resultado: list[dict[str, Any]] = []
    for parte in seed_partes:
        part_number = parte.get("part_number") or ""
        part_number_norm = normalize_part_number(part_number)

        epc_link = _resolve_epc_link(parte, vehiculo_con_vin, part_number_norm)
        offers = _resolve_offers(part_number_norm)
        imagen = parte.get("image") or {"url": None, "source": "generic", "credit": None}

        resultado.append(
            {
                "id": parte["id"],
                "part_number": part_number,
                "part_number_norm": part_number_norm,
                "type": parte.get("type", "OEM"),
                "brand": parte.get("brand", ""),
                "name": parte.get("name", ""),
                "category": parte.get("category", ""),
                "epc_link": epc_link,
                "image": imagen,
                "equivalents": parte.get("equivalents", []),
                "fitment_ids": parte.get("fitment_ids", []),
                # other_names (CONTRACTS.md, agregado 04/10/2026): opcional en
                # el seed, pero la clave SIEMPRE debe estar presente en el
                # parts.json final (mismo patrón que epc_link) -- default []
                # cuando la parte del seed no trae sinónimos.
                "other_names": parte.get("other_names", []),
                "offers": offers,
                "updated_at": build_time,
            }
        )

    return resultado


# ---------------------------------------------------------------------------
# search_index.json (derivado de parts.json)
# ---------------------------------------------------------------------------

def build_search_index(parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": parte["id"],
            "part_number_norm": parte["part_number_norm"],
            "name": parte["name"],
            "brand": parte["brand"],
        }
        for parte in parts
    ]


# ---------------------------------------------------------------------------
# categories.json (T-F1 — NO se regenera, solo se lee/valida/re-escribe igual)
# ---------------------------------------------------------------------------

def load_categories() -> list[dict[str, Any]]:
    """Lee `data/build/categories.json` (dueño: T-F1) y valida su forma
    mínima contra CONTRACTS.md. Este build NUNCA regenera categorías desde
    cero: solo las usa tal como están para dejar los 4 archivos consistentes
    en el mismo momento de build.
    """
    ruta = os.path.join(BUILD_DIR, "categories.json")
    with open(ruta, "r", encoding="utf-8") as f:
        categorias = json.load(f)

    if not isinstance(categorias, list):
        raise ValueError("categories.json (T-F1) debe ser una lista.")
    for cat in categorias:
        if not isinstance(cat, dict):
            raise ValueError(f"categories.json (T-F1): cada categoría debe ser un objeto ({cat!r}).")
        for clave in ("slug", "name_es", "svg"):
            if clave not in cat:
                raise ValueError(f"categories.json (T-F1): falta la clave '{clave}' en {cat!r}")

    return categorias


# ---------------------------------------------------------------------------
# Escritura + entrypoint
# ---------------------------------------------------------------------------

def _write_json(nombre: str, datos: Any) -> None:
    os.makedirs(BUILD_DIR, exist_ok=True)
    ruta = os.path.join(BUILD_DIR, nombre)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main() -> int:
    vehicles = build_vehicles()
    vehiculo_ejemplo = vehicles[0]

    parts = build_parts(vehiculo_ejemplo)
    search_index = build_search_index(parts)
    # categories.json es dueño de T-F1: se valida tal cual está, pero NO se
    # reescribe (ni siquiera con el mismo contenido re-serializado) para no
    # tocar el archivo de otro agente con cambios de formato sin sentido.
    categories = load_categories()

    _write_json("vehicles.json", vehicles)
    _write_json("parts.json", parts)
    _write_json("search_index.json", search_index)

    # Catálogo por fitment (T-B8): no sale de la semilla, sino de preguntarle a eBay qué le
    # queda EXACTAMENTE a cada vehículo. Va aparte a propósito, y nunca es fatal: si no hay
    # credenciales o la API falla, el build sigue y solo se avisa. Ver docs/piloto-tb7.md.
    fitment = None
    if os.environ.get("EBAY_CLIENT_ID") and os.environ.get("EBAY_CLIENT_SECRET"):
        try:
            import fetch_fitment

            fitment = fetch_fitment.build_fitment(vehicles)
            _write_json("fitment.json", fitment)
        except Exception as exc:  # red, cuota, forma inesperada: no tumba el build
            print(f"[build_index] aviso: no se construyó fitment.json ({type(exc).__name__}: {exc})")
    else:
        print("[build_index] sin credenciales de eBay: se omite fitment.json")

    # Catálogo con número de parte (T-B13): la API de AUTODOC da el número, la marca y la foto.
    # Igual que el fitment, nunca es fatal y solo corre con credenciales. OJO CON LA CUOTA: cada
    # vehículo gasta decenas de consultas, así que el plan programado NO lo corre solo (ver el
    # flujo de trabajo); aquí solo se aprovecha si RAPIDAPI_KEY está en el entorno, y con el tope
    # que fija data/seed/catalogo.vehiculos.json. Ver docs/piloto-tb10-autodoc.md.
    catalogo = None
    if os.environ.get("RAPIDAPI_KEY"):
        try:
            import fetch_autodoc

            semilla = json.loads(
                (Path(BUILD_DIR).parent / "seed" / "catalogo" / "vehiculos.json").read_text(encoding="utf-8")
            )
            cliente = fetch_autodoc.ClienteAutodoc(
                os.environ["RAPIDAPI_KEY"],
                max_consultas=int(semilla.get("max_consultas") or 30),
            )
            catalogo = fetch_autodoc.construir(semilla, cliente)
            fetch_autodoc.guardar(catalogo)
        except Exception as exc:  # red, cuota, forma inesperada: no tumba el build
            print(f"[build_index] aviso: no se construyó catalogo.json ({type(exc).__name__}: {exc})")
            catalogo = None
    else:
        print("[build_index] sin RAPIDAPI_KEY: se omite catalogo.json")

    resumen_catalogo = ""
    if catalogo:
        piezas = sum(len(c["articulos"]) for v in catalogo["vehiculos"] for c in v["categorias"])
        resumen_catalogo = (f" catalogo={len(catalogo['vehiculos'])} vehículo(s) "
                            f"[{piezas} piezas con número, {catalogo['consultas']} consultas]")

    resumen_fitment = ""
    if fitment and fitment.get("vehiculos"):
        v0 = fitment["vehiculos"][0]
        resumen_fitment = (f" fitment={len(fitment['vehiculos'])} vehículo(s) "
                           f"[{v0.get('categorias_con_ofertas')} categorías con ofertas, "
                           f"{v0.get('ofertas_totales')} ofertas]")

    print(
        f"[build_index] OK: vehicles={len(vehicles)} parts={len(parts)} "
        f"search_index={len(search_index)} categories={len(categories)} (sin reescribir, "
        f"ya existe y es válido){resumen_fitment}{resumen_catalogo} -> {BUILD_DIR}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
