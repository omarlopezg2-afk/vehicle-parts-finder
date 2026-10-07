"""pipeline/agregar_variantes.py — T-B26: catalogar los MOTORES que le faltan a la flota.

QUÉ HACE
    La flota se armó con `variantes_por_modelo_anio: 2` y `elegidas[:tope]`: **los dos primeros motores
    que devolvía la API, sin criterio**. Medido el 07/10/2026 contra las listas completas: 79
    modelo-año del catálogo NO tienen la gasolina más potente de ese año, que en RD es la que se ve en
    la calle (el Corolla 2016/2017 quedó con 1.3 y diésel 1.4 y le falta el 1.8; el Hilux/Fortuner con
    solo diésel y le falta el 4.0 V6; al Accent le falta el 1.6 GDI).

    Este script elige esas variantes **con criterio** (acordado con el usuario el 07/10/2026: la
    gasolina de más potencia de cada modelo-año, que es la gama que se importa) y las cataloga como
    vehículos nuevos, reusando `fetch_autodoc.construir`.

QUÉ **NO** HACE
    - No vuelve a pedir las listas de variantes: están en la caché de `completar_variantes`
      (`data/raw/autodoc_variantes/`), así que **elegir cuesta 0 consultas**. Lo único que se paga es
      bajar las piezas de las variantes nuevas: ~48 consultas por vehículo (medido: 12.058 para 250).
    - No gasta nada por defecto: sin `--ejecutar` solo imprime el plan (cuántas variantes, cuáles y
      cuánto costaría).
    - No inventa: una variante que no esté en la caché no se añade, se reporta.

CÓMO SE REANUDA
    `construir` se detiene al agotar `--max-consultas`, marca el resultado como incompleto y
    `fusionar` conserva lo que ya estaba. Volver a correrlo sigue donde se quedó (lo ya bajado no se
    repaga: la caché de especificaciones viene del propio catálogo).
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_autodoc import (  # noqa: E402
    RAIZ, ClienteAutodoc, clave_del_entorno, construir, fusionar, guardar, identidad_de_variante,
)
from completar_variantes import CACHE, SEMILLA  # noqa: E402

CATALOGO = RAIZ / "data" / "build" / "catalogo.json"
COSTE_POR_VEHICULO = 48          # medido: 12.058 consultas / 250 vehículos (07/10/2026)


# --------------------------------------------------------------------------------------
# elección (lógica pura: se prueba sin red)
# --------------------------------------------------------------------------------------

def identidades(cache: Path = CACHE) -> dict:
    """{modelId: [variantes que devolvió la API]} leído de la caché. 0 consultas."""
    salida = {}
    for archivo in sorted(cache.glob("*.json")):
        try:
            datos = json.loads(archivo.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if datos.get("modelId") is not None:
            salida[int(datos["modelId"])] = datos.get("modelTypes") or []
    return salida


def _vivas(variantes, anio: str) -> list:
    """Las variantes que existían ese año (el mismo filtro que usa `expandir_flota`)."""
    return [
        v for v in variantes
        if str(v.get("constructionIntervalStart") or "0000")[:4] <= str(anio)
        <= str(v.get("constructionIntervalEnd") or "9999")[:4]
    ]


def candidatos(catalogo: dict, variantes_por_modelo: dict, *, criterio: str = "alta") -> list[dict]:
    """Las variantes que faltan, una por modelo-año, según el criterio.

    Criterio `alta` (el acordado): la **gasolina de más potencia** que existía ese año. Si ese año no
    tiene ninguna gasolina en la lista de la API, no se añade nada (no se inventa un motor).

    Devuelve una lista de candidatos listos para `semilla_de`. Se compara por `vehicleId` —la unidad
    del catálogo— y se descarta lo que ya está catalogado.
    """
    if criterio != "alta":
        raise ValueError(f"criterio no soportado: {criterio}")

    # Lo que ya está y cómo se llama cada modelo (de las propias entradas del catálogo).
    ya = set()
    nombre = {}
    for v in catalogo.get("vehiculos", []):
        ids = v.get("autodoc") or {}
        if ids.get("modelId") is not None and ids.get("vehicleId") is not None:
            ya.add((int(ids["modelId"]), int(ids["vehicleId"])))
        vehiculo = v.get("vehiculo") or {}
        if ids.get("modelId") is not None and vehiculo.get("make"):
            nombre[int(ids["modelId"])] = (vehiculo.get("make"), vehiculo.get("model"),
                                           int(ids.get("manufacturerId") or 0))

    # Los años que el catálogo cubre de cada modelo: ahí es donde hay un hueco que tapar.
    anios_por_modelo = collections.defaultdict(set)
    for v in catalogo.get("vehiculos", []):
        ids = v.get("autodoc") or {}
        anio = str((v.get("vehiculo") or {}).get("year") or "")
        if ids.get("modelId") is not None and anio:
            anios_por_modelo[int(ids["modelId"])].add(anio)

    salida = []
    for model_id, anios in sorted(anios_por_modelo.items()):
        variantes = variantes_por_modelo.get(model_id)
        if not variantes or model_id not in nombre:
            continue
        make, model, fabricante = nombre[model_id]
        vistos = set()
        for anio in sorted(anios):
            gasolinas = [
                v for v in _vivas(variantes, anio)
                if (v.get("fuelType") or "").strip() == "Petrol"
            ]
            if not gasolinas:
                continue
            elegida = max(gasolinas, key=lambda v: float(v.get("powerPs") or 0))
            if elegida.get("vehicleId") is None:
                continue
            clave = (model_id, int(elegida["vehicleId"]))
            if clave in ya or clave in vistos:
                continue
            vistos.add(clave)
            salida.append({
                "manufacturerId": fabricante,
                "modelId": model_id,
                "vehicleId": int(elegida["vehicleId"]),
                "make": make,
                "model": model,
                "anio": anio,
                "identidad": identidad_de_variante(elegida),
                "criterio": f"gama-alta-{criterio}",
            })
    return salida


def semilla_de(candidatos_: list[dict], base: dict, *, max_consultas: int) -> dict:
    """La semilla que espera `construir`: vehículos CONCRETOS con sus ids, sin `flota`.

    Los ids se dan ya resueltos (los dejó la caché), así que el recorrido no gasta ni una consulta en
    resolver fabricante/modelo/variante. Sin `flota`: nada se expande por su cuenta.
    """
    return {
        "pais": base.get("pais", 67),
        "max_consultas": max_consultas,
        "vehiculos": [
            {
                "etiqueta": f"{c['make']} {c['model']} {c['anio']} "
                            f"{c['identidad'].get('variante') or ''}".strip(),
                "vin": None,
                "autodoc": {
                    "manufacturerId": c["manufacturerId"],
                    "modelId": c["modelId"],
                    "vehicleId": c["vehicleId"],
                },
                # La identidad ya se conoce (viene de la caché): el bloque `vehiculo` se escribe sin
                # gastar y el combustible no vuelve a faltar (T-B25).
                "_make": c["make"],
                "_model": c["model"],
                "_anio": c["anio"],
                "_variante_datos": c["identidad"],
                "criterio": c["criterio"],
            }
            for c in candidatos_
        ],
        "categorias_buscadas": base.get("categorias_buscadas") or [],
        "productos_oem": base.get("productos_oem") or [],
        "equivalentes_por_producto": base.get("equivalentes_por_producto") or 0,
        "detalles_por_categoria": base.get("detalles_por_categoria") or 0,
        "max_categorias": base.get("max_categorias") or 10,
    }


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Cataloga los motores que le faltan a la flota (T-B26).")
    ap.add_argument("--criterio", default="alta", choices=["alta"],
                    help="qué variante se añade por modelo-año (por defecto: la gasolina de más potencia)")
    ap.add_argument("--max-consultas", type=int, default=None,
                    help="tope de la corrida (por defecto: lo que estime el plan + 20%%)")
    ap.add_argument("--ejecutar", action="store_true", help="sin esto SOLO imprime el plan")
    ap.add_argument("--lote", type=int, default=0,
                    help="como máximo N variantes en esta corrida (0 = todas). Pensado para ir por "
                         "lotes: cada corrida escribe el catálogo, así que si una se corta no se "
                         "pierde lo que ya se bajó, y la siguiente sigue por donde iba")
    ap.add_argument("--listar", action="store_true", help="imprime la lista completa de candidatos")
    ap.add_argument("--sin-limite", action="store_true",
                    help="no corta al llegar al plan (para una corrida larga a propósito)")
    args = ap.parse_args(argv)

    if not CATALOGO.exists():
        print(f"[agregar] no hay catálogo en {CATALOGO}")
        return 1
    base = json.loads(SEMILLA.read_text(encoding="utf-8")) if SEMILLA.exists() else {}
    catalogo = json.loads(CATALOGO.read_text(encoding="utf-8"))
    variantes = identidades()
    if not variantes:
        print(f"[agregar] no hay caché de variantes en {CACHE}: corre antes completar_variantes.py")
        return 1

    lista = candidatos(catalogo, variantes, criterio=args.criterio)
    coste = len(lista) * COSTE_POR_VEHICULO
    if args.lote and args.lote > 0:
        lista = lista[:args.lote]
        coste = len(lista) * COSTE_POR_VEHICULO
    print(f"[agregar] criterio '{args.criterio}': {len(lista)} variantes nuevas en "
          f"{len({c['modelId'] for c in lista})} modelos ≈ {coste} consultas "
          f"({COSTE_POR_VEHICULO} por vehículo, medido)")
    por_modelo = collections.Counter(f"{c['make']} {c['model']}" for c in lista)
    print("[agregar] modelos con más huecos: "
          + ", ".join(f"{m} ({n})" for m, n in por_modelo.most_common(8)))
    if args.listar or not args.ejecutar:
        for c in lista:
            ident = c["identidad"]
            print(f"    {c['make']} {c['model']} {c['anio']:<5} {ident.get('variante'):32} "
                  f"{ident.get('combustible'):10} {ident.get('potencia_ps')} PS  "
                  f"motor {ident.get('motor')}  (vehicleId {c['vehicleId']})")

    if not args.ejecutar:
        print("\n[agregar] PLAN ONLY: no se ha gastado ni una consulta. "
              "Para hacerlo de verdad: --ejecutar")
        return 0
    if not lista:
        print("[agregar] no hay nada que añadir")
        return 0

    clave = clave_del_entorno()
    if not clave:
        print("[agregar] sin RAPIDAPI_KEY: se omite")
        return 1

    tope = args.max_consultas or (0 if args.sin_limite else int(coste * 1.2) + 1)
    if not tope:
        print("[agregar] --sin-limite: una corrida así puede gastar mucho más que el plan; "
              "asegúrate de que es lo que quieres")
    cliente = ClienteAutodoc(clave, max_consultas=tope)
    semilla = semilla_de(lista, base, max_consultas=tope)

    # La caché de especificaciones sale del catálogo anterior: lo ya pagado no se repaga.
    cache_detalles = {}
    for v in catalogo.get("vehiculos", []):
        for cat in v.get("categorias", []):
            for art in cat.get("articulos", []):
                if art.get("articleId") and art.get("especificaciones"):
                    cache_detalles[str(art["articleId"])] = {
                        "especificaciones": art["especificaciones"], "oem": art.get("oem") or [],
                    }
    print(f"[agregar] caché de especificaciones: {len(cache_detalles)} artículos conocidos (0 consultas)")

    resultado = construir(semilla, cliente, cache_detalles=cache_detalles)
    resultado["pais_filtro"] = catalogo.get("pais_filtro", base.get("pais"))
    resultado = fusionar(catalogo, resultado)

    respaldo = CATALOGO.with_suffix(".json.respaldo")
    CATALOGO.replace(respaldo)
    try:
        guardar(resultado, CATALOGO)
    except OSError as exc:
        respaldo.replace(CATALOGO)
        print(f"[agregar] fallo al escribir: {exc} (se restauró el respaldo)")
        return 1
    print(f"[agregar] consultas gastadas: {cliente.consultas} · vehículos en el catálogo: "
          f"{len(resultado['vehiculos'])}" + (" (INCOMPLETO: se agotó el presupuesto, "
          "vuelve a correrlo y sigue donde se quedó)" if resultado.get("incompleto") else ""))
    print(f"[agregar] escrito {CATALOGO} (respaldo: {respaldo.name})")
    print("[agregar] siguiente paso: python3 pipeline/partir_catalogo.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
