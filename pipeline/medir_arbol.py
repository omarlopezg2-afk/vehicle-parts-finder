"""pipeline/medir_arbol.py — cuántas piezas distintas tiene un vehículo en TecDoc y cuántas cubre el catálogo.

POR QUÉ EXISTE
    Omar preguntó (07/10/2026) qué porcentaje de las piezas de un carro cubre PartExact. El repo no
    tenía el denominador medido: solo el árbol del Lancer 2.0 (≈527 nodos). Esto lo mide para CUALQUIER
    vehículo con 1 consulta (el árbol de categorías) y lo guarda en `data/raw/` para no volver a pagarlo.

USO (primero en seco)
    python3 pipeline/medir_arbol.py --vehicle-id 109621              # 0 consultas: dice el coste
    python3 pipeline/medir_arbol.py --vehicle-id 109621 --ejecutar   # 1 consulta
    python3 pipeline/medir_arbol.py --vehicle-id 109621              # después: lee la caché, 0 consultas
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_autodoc import (  # noqa: E402
    ClienteAutodoc, LANG, RAIZ, TIPO_TURISMO, clave_del_entorno,
)

RAW = RAIZ / "data" / "raw"
CATALOGO_PARTIDO = RAIZ / "data" / "build" / "catalogo"


def ruta_cache(vehicle_id: int) -> Path:
    return RAW / f"arbol_v{int(vehicle_id)}.json"


def _hoja(nodo: dict):
    """(id, nombres) del nivel más profundo con id de un nodo del árbol."""
    for n in (4, 3, 2, 1):
        if nodo.get(f"categoryId{n}"):
            nombres = [nodo.get(f"categoryName{i}") for i in range(1, n + 1) if nodo.get(f"categoryName{i}")]
            return nodo[f"categoryId{n}"], nombres
    return None, []


def resumen(nodos: list[dict]) -> dict:
    """Cuenta el árbol: nodos, hojas distintas (lo más parecido a 'piezas distintas') y grupos de nivel 1."""
    hojas: dict = {}
    grupos = collections.defaultdict(set)
    for nodo in nodos:
        hid, nombres = _hoja(nodo)
        if hid is None:
            continue
        hojas[hid] = " / ".join(nombres)
        if nombres:
            grupos[nombres[0]].add(hid)
    return {
        "nodos": len(nodos),
        "hojas": len(hojas),
        "con_categoryId2": sum(1 for n in nodos if n.get("categoryId2")),
        "grupos": {g: len(ids) for g, ids in sorted(grupos.items(), key=lambda kv: -len(kv[1]))},
        "hojas_por_id": hojas,
    }


def categorias_publicadas(vehicle_id: int) -> list[str]:
    """Nombres de las categorías TecDoc con piezas publicadas para ese vehículo (lee el catálogo partido)."""
    carpeta = CATALOGO_PARTIDO / f"v{int(vehicle_id)}"
    out = []
    if carpeta.is_dir():
        for f in sorted(carpeta.glob("*.json")):
            if f.name == "originales.json":
                continue
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            out.append(d.get("ruta") or d.get("categoria") or d.get("nombre") or f.stem)
    return out


def pedir_arbol(cliente: ClienteAutodoc, vehicle_id: int) -> list[dict] | None:
    datos = cliente.pedir(
        f"/api/category/type-id/{TIPO_TURISMO}/products-groups-variant-1/{int(vehicle_id)}/lang-id/{LANG}"
    )
    lista = (datos or {}).get("categories") if isinstance(datos, dict) else None
    return lista if isinstance(lista, list) else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Mide el árbol de categorías de un vehículo (1 consulta).")
    ap.add_argument("--vehicle-id", type=int, required=True)
    ap.add_argument("--ejecutar", action="store_true", help="sin esto no se gasta nada")
    args = ap.parse_args(argv)

    cache = ruta_cache(args.vehicle_id)
    if cache.exists():
        nodos = json.loads(cache.read_text(encoding="utf-8"))
        print(f"[arbol] v{args.vehicle_id}: leído de la caché {cache.name} (0 consultas)")
    elif not args.ejecutar:
        print(f"[arbol] v{args.vehicle_id}: no está en caché. Costaría 1 consulta. PLAN ONLY: añade --ejecutar.")
        return 0
    else:
        clave = clave_del_entorno()
        if not clave:
            print("[arbol] sin RAPIDAPI_KEY: se omite")
            return 1
        cliente = ClienteAutodoc(clave, max_consultas=1)
        nodos = pedir_arbol(cliente, args.vehicle_id)
        if nodos is None:
            print("[arbol] TecDoc no devolvió el árbol (1 consulta gastada)")
            return 1
        RAW.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(nodos, ensure_ascii=False), encoding="utf-8")
        print(f"[arbol] v{args.vehicle_id}: árbol guardado en {cache.name} (1 consulta gastada)")

    r = resumen(nodos)
    pub = categorias_publicadas(args.vehicle_id)
    print(f"[arbol] nodos: {r['nodos']} · hojas distintas: {r['hojas']} · con categoryId2: {r['con_categoryId2']}")
    print(f"[arbol] categorías TecDoc con piezas publicadas para v{args.vehicle_id}: {len(pub)}")
    if r["hojas"]:
        print(f"[arbol] cobertura sobre hojas: {len(pub)}/{r['hojas']} = {100 * len(pub) / r['hojas']:.1f} %")
    print("[arbol] grupos de nivel 1 (hojas):")
    for g, n in r["grupos"].items():
        print(f"    {n:4d}  {g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
