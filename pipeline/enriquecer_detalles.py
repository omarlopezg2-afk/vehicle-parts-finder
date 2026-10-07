"""pipeline/enriquecer_detalles.py — T-B26 4.2: detallar las piezas que el sitio YA enseña y no tienen detalle.

POR QUÉ EXISTE
    `construir` pide el detalle (especificaciones, posición y números ORIGINALES) solo de los 3
    primeros artículos de cada categoría. En una categoría pedida por "brake pad" esos 3 a veces son
    discos, así que las pastillas que el sitio enseña salen sin posición (delantera/trasera) y sin el
    número original del fabricante (medido el 07/10/2026: 108 pastillas distintas, p. ej. las del
    Corolla 1.8). Cada detalle es 1 consulta (`articles/details/article-id/{id}`) y el `articleId` de
    TecDoc es global: una consulta sirve para todos los vehículos que comparten esa pieza.

QUÉ HACE
    Recorre el catálogo, junta los artículos que el sitio publica (`articulos_utiles`), que SON el
    producto buscado (`pieza` contiene el término, la misma regla del sitio) y no tienen detalle, y pide el
    detalle de cada `articleId` UNA sola vez. Lo escribe en todas las apariciones.

QUÉ **NO** HACE
    - No añade piezas al catálogo ni cambia cuáles se publican: solo completa las que ya salen.
    - No gasta nada sin `--ejecutar`: por defecto imprime el plan y el coste exacto (= nº de articleId).
    - No inventa: si TecDoc no devuelve detalle de una pieza, se queda como estaba.

USO (primero en seco)
    python3 pipeline/enriquecer_detalles.py --producto "brake pad"             # plan, 0 consultas
    python3 pipeline/enriquecer_detalles.py --producto "brake pad" --ejecutar   # gasta N consultas
    python3 pipeline/partir_catalogo.py                                        # 0 consultas
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_autodoc import (  # noqa: E402
    ClienteAutodoc, PresupuestoAgotado, clave_del_entorno, detalles_de_articulo, guardar,
)
from agregar_variantes import CATALOGO  # noqa: E402
from partir_catalogo import articulos_utiles  # noqa: E402


def _norm(texto) -> str:
    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return " ".join(t.lower().split())


def pendientes(catalogo: dict, productos: list[str]) -> dict:
    """{articleId: [artículo, …]}: los artículos publicados, del producto, sin detalle.

    Un artículo está sin detalle cuando no tiene especificaciones NI números originales. Los
    artículos de distintos vehículos con el mismo `articleId` se agrupan: se pide una vez.
    """
    buscados = {_norm(p) for p in productos}
    salida: dict = collections.OrderedDict()
    for v in catalogo.get("vehiculos", []):
        for cat in v.get("categorias", []):
            buscado = _norm(cat.get("buscado"))
            if buscado not in buscados:
                continue
            publicados = {id(a) for a in articulos_utiles(cat)}
            for art in cat.get("articulos", []):
                if id(art) not in publicados:
                    continue
                if art.get("especificaciones") or art.get("oem"):
                    continue
                aid = art.get("articleId")
                if not aid or buscado not in _norm(art.get("pieza")):
                    continue
                salida.setdefault(aid, []).append(art)
    return salida


def aplicar(pend: dict, cliente, *, pedir=detalles_de_articulo) -> tuple[int, bool]:
    """Pide el detalle de cada articleId pendiente y lo escribe en todas sus apariciones.

    Devuelve (cuántos se detallaron, si se cortó por presupuesto). Lo hecho antes de cortar se conserva.
    """
    hechos = 0
    for aid, apariciones in pend.items():
        try:
            det = pedir(cliente, aid)
        except PresupuestoAgotado as exc:
            print(f"[detalles] {exc}")
            return hechos, True
        if not det:
            continue
        for art in apariciones:
            art["especificaciones"] = det.get("especificaciones") or {}
            art["oem"] = det.get("oem") or []
        hechos += 1
    return hechos, False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Detalla las piezas publicadas que no tienen detalle (T-B26 4.2).")
    ap.add_argument("--producto", action="append", default=[], metavar="BUSCADO",
                    help='término con el que se pidió la categoría, p. ej. "brake pad" (repetible)')
    ap.add_argument("--ejecutar", action="store_true", help="sin esto SOLO imprime el plan")
    ap.add_argument("--max-consultas", type=int, default=None,
                    help="tope de la corrida (por defecto: exactamente las que pide el plan)")
    args = ap.parse_args(argv)

    if not args.producto:
        print('[detalles] indica al menos un --producto, p. ej. --producto "brake pad"')
        return 1
    if not CATALOGO.exists():
        print(f"[detalles] no hay catálogo en {CATALOGO}")
        return 1

    catalogo = json.loads(CATALOGO.read_text(encoding="utf-8"))
    pend = pendientes(catalogo, args.producto)
    por_vehiculo = collections.Counter()
    for apariciones in pend.values():
        por_vehiculo[len(apariciones)] += 1
    print(f"[detalles] productos {args.producto}: {len(pend)} piezas distintas sin detalle "
          f"= {len(pend)} consultas (1 por articleId; una pieza compartida se paga una vez)")
    compartidas = sum(1 for a in pend.values() if len(a) > 1)
    print(f"[detalles] {compartidas} de ellas están en más de un vehículo")

    if not args.ejecutar:
        print("\n[detalles] PLAN ONLY: no se ha gastado ni una consulta. Para hacerlo de verdad: --ejecutar")
        return 0
    if not pend:
        print("[detalles] no hay nada que detallar")
        return 0

    clave = clave_del_entorno()
    if not clave:
        print("[detalles] sin RAPIDAPI_KEY: se omite")
        return 1
    tope = args.max_consultas or len(pend)
    cliente = ClienteAutodoc(clave, max_consultas=tope)
    hechos, cortado = aplicar(pend, cliente)

    catalogo["consultas"] = int(catalogo.get("consultas") or 0) + cliente.consultas
    respaldo = CATALOGO.with_suffix(".json.respaldo")
    CATALOGO.replace(respaldo)
    try:
        guardar(catalogo, CATALOGO)
    except OSError as exc:
        respaldo.replace(CATALOGO)
        print(f"[detalles] fallo al escribir: {exc} (se restauró el respaldo)")
        return 1
    print(f"[detalles] detalladas {hechos} de {len(pend)} · consultas gastadas: {cliente.consultas}"
          + (" (CORTADO por presupuesto: vuelve a correrlo y sigue donde se quedó)" if cortado else ""))
    print(f"[detalles] escrito {CATALOGO} (respaldo: {respaldo.name})")
    print("[detalles] siguiente paso: python3 pipeline/partir_catalogo.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
