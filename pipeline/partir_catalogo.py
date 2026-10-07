"""pipeline/partir_catalogo.py — T-B19: partir el catálogo y quedarse con lo útil.

QUÉ HACE
    Toma `data/build/catalogo.json` (un solo archivo con TODO) y escribe:
      - `data/build/catalogo/index.json`        -> índice pequeño: qué vehículos hay y qué
                                                    categorías tienen datos (para el sitio).
      - `data/build/catalogo/<clave>/<slug>.json` -> un archivo por vehículo y categoría, con lo
                                                    que de verdad sirve.

POR QUÉ (medido el 07/10/2026)
    El archivo único pesaba 10,3 MB con SOLO 8 vehículos (~1,3 MB por vehículo). Con los ~284
    vehículos del bloque de flota serían unos 350 MB: imposible de descargar por un visitante.

    Y la causa no era solo el tamaño: de cada categoría se guardaban CIENTOS de artículos de
    marcas distintas (una variante del Corolla 2016 llegó a 5.232 piezas). Eso es exactamente lo
    que el usuario rechazó con razón —"eso no es exactitud, es un volcado de marcas"—. El catálogo
    útil es **el número original del fabricante, sus equivalentes y las especificaciones que
    distinguen** (posición, medida), no las 400 marcas de filtro.

QUÉ SE CONSERVA (y qué se tira)
    - Por cada categoría: los artículos QUE TIENEN especificaciones (los que el pipeline detalló),
      con su número, marca, nombre, foto, especificaciones y números originales.
    - Los números ORIGINALES del fabricante por producto (bloque `oem`), que es lo que la gente
      reconoce y lo que pide en la tienda.
    - Se descarta el resto del volcado de marcas (se puede volver a pedir cuando interese: los
      `articleId` de TecDoc no cambian y el caché del pipeline los recuerda).

NO GASTA CUOTA: es puro reordenar lo que ya está descargado.
"""
from __future__ import annotations

import json
import re
import shutil
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ORIGEN = RAIZ / "data" / "build" / "catalogo.json"
DESTINO = RAIZ / "data" / "build" / "catalogo"


def clave_vehiculo(vehiculo: dict) -> str:
    """Nombre de carpeta estable y legible: el vehicleId de AUTODOC, que no cambia nunca."""
    aid = (vehiculo.get("autodoc") or {}).get("vehicleId")
    if aid:
        return f"v{aid}"
    return re.sub(r"[^a-z0-9]+", "-", str(vehiculo.get("etiqueta", "?")).lower()).strip("-")


def slug_de(nombre: str) -> str:
    t = unicodedata.normalize("NFKD", str(nombre or "")).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t.lower())
    return t.strip("-") or "categoria"


def partir() -> dict:
    datos = json.loads(ORIGEN.read_text(encoding="utf-8"))
    if DESTINO.exists():
        shutil.rmtree(DESTINO)
    DESTINO.mkdir(parents=True, exist_ok=True)

    indice = {
        "fuente": datos.get("fuente"),
        "generado_en": datos.get("generado_en"),
        "consultas": datos.get("consultas"),
        "vehiculos": [],
    }
    resumen = []

    for v in datos.get("vehiculos", []):
        clave = clave_vehiculo(v)
        carpeta = DESTINO / clave
        carpeta.mkdir(parents=True, exist_ok=True)

        # Los originales del fabricante, por producto ("brake pad", "oil filter"...). Van en el
        # índice del vehículo porque son pocos y el sitio los necesita al pintar la categoría.
        originales = []
        for bloque in v.get("oem", []):
            numeros = [n for n in (bloque.get("numeros") or []) if n.get("numero")]
            if numeros:
                originales.append({"buscado": bloque.get("buscado"), "numeros": numeros})

        categorias = []
        for cat in v.get("categorias", []):
            # SOLO lo detallado: lo que trae especificaciones o números originales.
            utiles = [
                a for a in (cat.get("articulos") or [])
                if a.get("especificaciones") or a.get("oem")
            ]
            if not utiles:
                continue
            slug = slug_de(cat.get("nombre"))
            cuerpo = {
                "nombre": cat.get("nombre"),
                "ruta": cat.get("ruta"),
                "buscado": cat.get("buscado"),
                "categoryId": cat.get("categoryId"),
                "articulos": utiles,
            }
            (carpeta / f"{slug}.json").write_text(
                json.dumps(cuerpo, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8"
            )
            categorias.append({
                "slug": slug,
                "nombre": cat.get("nombre"),
                # `buscado` es la clave para emparejar: el nombre de la categoría de AUTODOC es un
                # grupo y engaña (los filtros de aceite viven en "Lubrication"), mientras que el
                # término con el que se pidió ("oil filter") sí dice qué hay dentro.
                "buscado": cat.get("buscado"),
                "ruta": cat.get("ruta"),
                # Los nombres de las piezas que hay dentro. Junto con `buscado` son la señal fiable
                # para emparejar: una categoría puede servir a varias del sitio ("Disc Brake" tiene
                # pastillas Y discos), y el nombre de la categoría no lo dice.
                "productos": sorted({a.get("pieza") for a in utiles if a.get("pieza")}),
                "articulos": len(utiles),
                "archivo": f"catalogo/{clave}/{slug}.json",
            })

        # Los números originales NO van en el índice: son 100-160 por vehículo y multiplicarían su
        # tamaño (medido: 2,4 MB con solo 8 vehículos). Van en su propio archivo por vehículo, que
        # el sitio descarga solo si hace falta.
        if originales:
            (carpeta / "originales.json").write_text(
                json.dumps({"originales": originales}, ensure_ascii=False, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )

        entrada = {
            "clave": clave,
            "etiqueta": v.get("etiqueta"),
            "vin": v.get("vin"),
            "vehiculo": v.get("vehiculo") or {},
            "autodoc": {k: val for k, val in (v.get("autodoc") or {}).items() if not k.startswith("_")},
            "nombres": v.get("nombres") or {},
            "originales": {"archivo": f"catalogo/{clave}/originales.json", "productos": len(originales)},
            "categorias": categorias,
        }
        indice["vehiculos"].append(entrada)

        tam_cat = sum((carpeta / f"{c['slug']}.json").stat().st_size for c in categorias)
        resumen.append((v.get("etiqueta", "?"), len(categorias), sum(c["articulos"] for c in categorias), tam_cat))

    (DESTINO / "index.json").write_text(
        json.dumps(indice, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8"
    )

    print(f"{'vehículo':<48} {'categorías':>10} {'piezas':>8} {'tamaño':>10}")
    for etiqueta, ncat, nart, tam in resumen:
        print(f"{etiqueta[:47]:<48} {ncat:>10} {nart:>8} {tam/1024:>8.0f} KB")
    total_cat = sum(len(v["categorias"]) for v in indice["vehiculos"])
    print(f"\níndice: {(DESTINO / 'index.json').stat().st_size/1024:.0f} KB para "
          f"{len(indice['vehiculos'])} vehículos y {total_cat} categorías")
    if total_cat:
        tam = sum(f.stat().st_size for f in DESTINO.rglob("*.json") if f.name != "index.json")
        print(f"tamaño medio por categoría: {tam/total_cat/1024:.1f} KB "
              f"(antes: ~130 KB por categoría en el archivo único)")
    return indice


if __name__ == "__main__":
    partir()
