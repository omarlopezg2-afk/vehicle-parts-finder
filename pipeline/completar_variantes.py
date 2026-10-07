"""pipeline/completar_variantes.py — T-B25: poner el COMBUSTIBLE (y la cilindrada y la potencia) en las variantes.

QUÉ HACE
    Toma el catálogo que ya está descargado (`data/build/catalogo.json`), saca las parejas
    (fabricante, modelo) que tienen vehículos y pide UNA vez por pareja la lista de variantes
    (`/api/types/type-id/1/list-vehicles-types/{modelId}`). De esa respuesta toma el combustible
    (`fuelType`), la cilindrada (`capacityLt`), la potencia (`powerPs`) y el código de motor
    (`engineCodes`) y los escribe en el bloque `vehiculo` de cada entrada que falte.

POR QUÉ EXISTE
    La cuarta capa del sitio (T-B25) tiene que decir de qué mercado, de qué motor y de qué
    COMBUSTIBLE es cada número, y el catálogo solo lo traía en las 2 entradas que entraron por VIN
    (medido el 07/10/2026: **248 de 250 sin combustible**). En el nombre de la variante tampoco se
    puede leer: 219 de las 250 no traen ninguna señal (27 diésel, 4 híbridos, y el resto calla).
    Y la causa es esta: `expandir_flota` **ya recibe** esos campos en la misma respuesta que paga
    resolver el modelo (los usa para filtrar por año) y no los guardaba. Se pagó una vez y se tiró.
    Este script los recupera; `fetch_autodoc.expandir_flota` se arregló en el mismo cambio para que
    no vuelva a perderse.

COSTE (medido ANTES de escribirlo, 07/10/2026)
    250 entradas -> 50 parejas (fabricante, modelo) distintas -> **50 consultas**. Nada más: ni una
    por vehículo, ni una por categoría. El script imprime cuántas gastó y con `--max-consultas`
    nunca puede pasarse (misma guarda `PresupuestoAgotado` que el resto del pipeline).

DÓNDE VA LA CLAVE
    En el entorno (`RAPIDAPI_KEY`) o en el `.env` del repo. Nunca se imprime.

CACHÉ (importante)
    Cada respuesta se guarda en `data/raw/autodoc_variantes/`. El dato en sí ya queda escrito en el
    catálogo (que sí va a git); la caché es para NO volver a pagar la respuesta si hubiera que
    reconstruir el catálogo. Con la caché puesta, repetir este script cuesta 0 consultas.

NO INVENTA
    Una entrada cuyo `vehicleId` no aparezca en la lista de su modelo se queda sin combustible y se
    **reporta** al final. No se rellena con "si es un Corolla, será gasolina": un número exacto para
    la variante equivocada es peor que no dar número (regla del proyecto).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_autodoc import (  # noqa: E402
    LANG, RAIZ, TIPO_TURISMO, ClienteAutodoc, PresupuestoAgotado, clave_del_entorno,
    identidad_de_variante,
)
from partir_catalogo import vehiculo_completo  # noqa: E402

CATALOGO = RAIZ / "data" / "build" / "catalogo.json"
SEMILLA = RAIZ / "data" / "seed" / "catalogo" / "vehiculos.json"
CACHE = RAIZ / "data" / "raw" / "autodoc_variantes"

# Orden de las claves al escribir el bloque `vehiculo`: primero lo que identifica al coche, después
# su identidad técnica. Es el orden en el que se lee y en el que se pinta.
ORDEN_VEHICULO = (
    "make", "model", "year", "market",
    "cilindrada_l", "potencia_ps", "potencia_hp", "combustible", "motor",
    "variante", "origen", "vin", "valido",
)


# --------------------------------------------------------------------------------------
# lectura de la respuesta (lógica pura: se prueba sin red)
# --------------------------------------------------------------------------------------

def datos_de_variante(v: dict | None) -> dict:
    """Alias de `fetch_autodoc.identidad_de_variante`: la identidad de una variante de TecDoc."""
    return identidad_de_variante(v)


def mapa_de_variantes(model_types: list | None) -> tuple[dict, list, dict]:
    """{vehicleId: identidad de la variante}. Devuelve también lo dudoso, separado por gravedad.

    - `ambiguos`: el mismo `vehicleId` con más de una identidad. Es NORMAL en TecDoc (un vehículo
      puede venir con varios códigos de motor) y se conserva la primera, como hace `expandir_flota`.
    - `choques`: el mismo `vehicleId` con COMBUSTIBLE DISTINTO. Eso sí es una alarma: el combustible
      es uno de los tres datos que no se pueden callar y no se elige a dedo, así que esas variantes
      se quedan SIN rellenar y se reportan.
    """
    mapa: dict[str, dict] = {}
    ambiguos: list[str] = []
    choques: dict[str, list[str]] = {}
    for v in model_types or []:
        if not isinstance(v, dict):
            continue
        vid = v.get("vehicleId")
        if vid is None:
            continue
        identidad = datos_de_variante(v)
        if not identidad:
            continue
        clave = str(vid)
        previo = mapa.get(clave)
        if previo is not None:
            if previo != identidad:
                ambiguos.append(clave)
            if (previo.get("combustible") or "") != (identidad.get("combustible") or ""):
                choques.setdefault(clave, sorted({previo.get("combustible") or "",
                                                  identidad.get("combustible") or ""}))
            continue
        mapa[clave] = identidad

    for clave in choques:                        # ante la duda, no se rellena nada
        mapa.pop(clave, None)
    return mapa, ambiguos, choques


def completar(entradas: list[dict], mapa: dict[str, dict], flota: list[dict]) -> dict:
    """Rellena el bloque `vehiculo` de cada entrada. Solo añade lo que falta; nunca sobreescribe.

    Devuelve el informe: cuántas se rellenaron, cuántas ya tenían combustible, cuántas no tienen
    dato (con su etiqueta, para poder reportarlas) y cuántas no tienen `vehicleId`.
    """
    informe = {"rellenadas": 0, "ya_completas": 0, "sin_dato": [], "sin_id": [], "claves": {}}
    for entrada in entradas:
        if not isinstance(entrada, dict):
            continue
        actual = entrada.get("vehiculo") or {}
        if actual.get("combustible"):
            informe["ya_completas"] += 1
            continue

        vid = (entrada.get("autodoc") or {}).get("vehicleId")
        if vid is None:
            informe["sin_id"].append(str(entrada.get("etiqueta") or "?"))
            continue

        identidad = mapa.get(str(vid))
        if not identidad:
            informe["sin_dato"].append(str(entrada.get("etiqueta") or "?"))
            continue

        # La marca/modelo/año vienen de la semilla + la etiqueta (0 consultas) y el resto de la API.
        bloque = vehiculo_completo(entrada, flota)
        for clave, valor in identidad.items():
            if not bloque.get(clave):
                bloque[clave] = valor

        entrada["vehiculo"] = _ordenar(bloque)
        informe["rellenadas"] += 1
        informe["claves"][str(bloque.get("combustible") or "(vacío)")] = (
            informe["claves"].get(str(bloque.get("combustible") or "(vacío)"), 0) + 1
        )
    return informe


def _ordenar(bloque: dict) -> dict:
    """El bloque con las claves en el orden de lectura; lo desconocido va al final."""
    ordenado = {k: bloque[k] for k in ORDEN_VEHICULO if k in bloque}
    for k, v in bloque.items():
        if k not in ordenado:
            ordenado[k] = v
    return ordenado


def pares_pendientes(entradas: list[dict]) -> list[tuple[int, int]]:
    """Parejas (fabricante, modelo) distintas que tienen alguna entrada sin combustible."""
    pares = {
        (int((e.get("autodoc") or {})["manufacturerId"]), int((e.get("autodoc") or {})["modelId"]))
        for e in entradas
        if isinstance(e, dict)
        and not (e.get("vehiculo") or {}).get("combustible")
        and (e.get("autodoc") or {}).get("manufacturerId")
        and (e.get("autodoc") or {}).get("modelId")
    }
    return sorted(pares)


# --------------------------------------------------------------------------------------
# red (con caché en disco)
# --------------------------------------------------------------------------------------

def variantes_del_modelo(cliente: ClienteAutodoc | None, model_id: int, pais: int,
                         *, cache: Path = CACHE) -> list | None:
    """La lista de variantes de un modelo, de la caché o de la API. None si no se pudo obtener.

    Se cachea incluso la lista vacía: lo que se paga una vez no se vuelve a pagar nunca.
    """
    cache.mkdir(parents=True, exist_ok=True)
    archivo = cache / f"country-{pais}-modelo-{model_id}.json"
    if archivo.exists():
        try:
            return json.loads(archivo.read_text(encoding="utf-8")).get("modelTypes") or []
        except (OSError, json.JSONDecodeError):
            print(f"  [!] caché ilegible: {archivo.name} (se vuelve a pedir)")

    if cliente is None:
        return None

    datos = cliente.pedir(
        f"/api/types/type-id/{TIPO_TURISMO}/list-vehicles-types/{model_id}"
        f"/lang-id/{LANG}/country-filter-id/{pais}"
    )
    if not isinstance(datos, dict):
        return None
    variantes = datos.get("modelTypes")
    if not isinstance(variantes, list):
        return None
    archivo.write_text(
        json.dumps({"modelId": model_id, "pais": pais, "traido_en": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "modelTypes": variantes}, ensure_ascii=False),
        encoding="utf-8",
    )
    return variantes


def auditar_cache(*, cache: Path = CACHE) -> tuple[int, dict[str, list[str]]]:
    """Repasa TODA la caché buscando un `vehicleId` con dos combustibles distintos.

    Es la comprobación de que el combustible rellenado no se eligió a dedo: TecDoc lista a veces el
    mismo vehículo con varios motores, y si alguno de esos motores fuese de otro combustible, la
    etiqueta "Combustible: ..." sería una suposición. Cuesta 0 consultas (lee la caché) y por eso se
    puede repetir siempre.
    """
    por_vid: dict[str, set[str]] = {}
    for archivo in sorted(cache.glob("*.json")):
        try:
            variantes = json.loads(archivo.read_text(encoding="utf-8")).get("modelTypes") or []
        except (OSError, json.JSONDecodeError):
            continue
        for v in variantes:
            if not isinstance(v, dict) or v.get("vehicleId") is None:
                continue
            por_vid.setdefault(str(v["vehicleId"]), set()).add(str(v.get("fuelType") or "").strip())
    choques = {k: sorted(s) for k, s in por_vid.items() if len(s) > 1}
    return len(por_vid), choques


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Rellena combustible/cilindrada/potencia de las variantes.")
    ap.add_argument("--max-consultas", type=int, default=60,
                    help="tope de consultas de la corrida (por defecto 60; hacen falta 50)")
    ap.add_argument("--pais", type=int, default=None,
                    help="filtro de país (por defecto, el de la semilla y el del catálogo)")
    ap.add_argument("--sin-red", action="store_true",
                    help="solo caché: no gasta ni una consulta (para probar sin clave)")
    ap.add_argument("--dry-run", action="store_true", help="no escribe el catálogo")
    args = ap.parse_args(argv)

    if not CATALOGO.exists():
        print(f"[variantes] no hay catálogo en {CATALOGO}")
        return 0

    datos = json.loads(CATALOGO.read_text(encoding="utf-8"))
    entradas = datos.get("vehiculos") or []
    pais = args.pais or int((json.loads(SEMILLA.read_text(encoding="utf-8")) if SEMILLA.exists() else {}).get("pais") or 261)
    flota = (json.loads(SEMILLA.read_text(encoding="utf-8")) if SEMILLA.exists() else {}).get("flota") or []

    pendientes = pares_pendientes(entradas)
    print(f"[variantes] catálogo con {len(entradas)} entradas, país {pais}, "
          f"{len(pendientes)} parejas (fabricante, modelo) sin combustible")

    clave = "" if args.sin_red else clave_del_entorno()
    if not args.sin_red and not clave:
        print("[variantes] sin RAPIDAPI_KEY: se omite")
        return 0
    cliente = None if args.sin_red else ClienteAutodoc(clave, max_consultas=args.max_consultas)

    mapa: dict[str, dict] = {}
    ambiguos: list[str] = []
    choques: dict[str, list[str]] = {}
    sin_respuesta: list[int] = []
    for i, (fab, modelo) in enumerate(pendientes, 1):
        try:
            variantes = variantes_del_modelo(cliente, modelo, pais)
        except PresupuestoAgotado as e:
            print(f"  [!] {e}: quedan {len(pendientes) - i + 1} parejas sin pedir")
            break
        if variantes is None:
            sin_respuesta.append(modelo)
            continue
        m, amb, cho = mapa_de_variantes(variantes)
        mapa.update({k: v for k, v in m.items() if k not in mapa})
        ambiguos += amb
        choques.update(cho)
        print(f"  [{i}/{len(pendientes)}] fabricante {fab} modelo {modelo}: "
              f"{len(variantes)} variantes -> {len(m)} con identidad")

    informe = completar(entradas, mapa, flota)
    auditados, choques_cache = auditar_cache()
    print(f"\n[variantes] consultas gastadas: {cliente.consultas if cliente else 0} "
          f"(caché en {CACHE.relative_to(RAIZ)})")
    print(f"[variantes] cache: {auditados} vehicleId revisados, "
          f"{len(choques_cache)} con combustible contradictorio"
          + ("" if not choques_cache else f" -> {list(choques_cache.items())[:5]}"))
    print(f"[variantes] rellenadas: {informe['rellenadas']} · ya estaban: {informe['ya_completas']} "
          f"· sin dato: {len(informe['sin_dato'])} · sin vehicleId: {len(informe['sin_id'])}")
    print(f"[variantes] combustibles: {informe['claves']}")
    if ambiguos:
        print(f"[variantes] {len(ambiguos)} vehicleId con más de un motor en la lista de TecDoc "
              f"(normal: se conserva el primero, como hace expandir_flota)")
    if choques:
        print(f"  [!] ALARMA: {len(choques)} vehicleId con combustible CONTRADICTORIO "
              f"(se quedan sin rellenar): {list(choques.items())[:5]}")
    if sin_respuesta:
        print(f"  [!] modelos sin respuesta de la API ({len(sin_respuesta)}): {sin_respuesta[:5]}")
    if informe["sin_dato"]:
        print(f"  [!] entradas sin dato ({len(informe['sin_dato'])}): {informe['sin_dato'][:5]}")

    if args.dry_run:
        print("[variantes] --dry-run: no se escribe el catálogo")
        return 0
    if not informe["rellenadas"]:
        print("[variantes] nada que escribir")
        return 0

    datos["variantes_completadas_en"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    respaldo = CATALOGO.with_suffix(".json.respaldo")
    CATALOGO.replace(respaldo)                       # el árbol nunca se queda a medias
    try:
        CATALOGO.write_text(json.dumps(datos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    except OSError as exc:
        respaldo.replace(CATALOGO)                   # devolver el original si no se pudo escribir
        print(f"[variantes] fallo al escribir: {exc} (se restauró el respaldo)")
        return 1
    print(f"[variantes] escrito {CATALOGO} (respaldo: {respaldo.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
