"""Cliente vPIC (NHTSA) para resolver un VIN a los campos de `vehicles.json`, y para el
camino alterno de selección sin VIN (drill-down marca → modelo → año, ver PLAN.md línea
~58: "VIN, o marca/modelo/año/versión" son las dos formas de entrar al buscador).

APIs usadas (todas públicas, sin llave):
    GET https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/<VIN>?format=json
    GET https://vpic.nhtsa.dot.gov/api/vehicles/GetMakesForVehicleType/<tipo>?format=json
    GET https://vpic.nhtsa.dot.gov/api/vehicles/GetModelsForMakeYear/make/<marca>/modelyear/<año>?format=json

Uso típico (VIN):
    from pipeline.fetch_vehicles import fetch_vehicle
    vehiculo = fetch_vehicle("JA4AP3AU0LU000302")
    if vehiculo["error"] is None:
        ...  # vehiculo cumple el esquema de CONTRACTS.md (vehicles.json)
    else:
        ...  # VIN inválido / problema de red: manejar sin tumbar el pipeline

Uso típico (drill-down sin VIN):
    from pipeline.fetch_vehicles import get_all_makes, get_models_for_make_year
    marcas = get_all_makes()                              # [{"id": 481, "name": "Mitsubishi"}, ...]
    modelos = get_models_for_make_year("Mitsubishi", 2020)  # [{"id": 13867, "name": "Outlander Sport"}, ...]

Ejecutado directamente (`python pipeline/fetch_vehicles.py VIN1 VIN2 ...`) imprime un
JSON con la lista de resultados (uno por VIN), útil para pruebas manuales rápidas.

Diseño de errores (ver T-A1 en TASKS.md: "VIN inválido no rompe el pipeline"):
- `fetch_vehicle` NUNCA deja escapar una excepción. Captura errores de red,
  timeouts, JSON malformado y VINes inválidos/no reconocidos por NHTSA.
- El dict devuelto SIEMPRE tiene las mismas claves. Si algo salió mal,
  `error` trae un mensaje legible en español y los campos de datos quedan en
  `None`. El pipeline (build_index.py u otro consumidor) debe filtrar por
  `error is None` antes de escribir `data/build/vehicles.json`, ya que ese
  esquema (CONTRACTS.md) no incluye la clave `error`.
- `get_all_makes` y `get_models_for_make_year` siguen el MISMO patrón defensivo
  (nunca lanzan excepción), pero como devuelven `list[dict]` en vez de un dict con
  clave `error`, cualquier problema de red/HTTP/JSON se traduce en **lista vacía**
  más un aviso por `sys.stderr` (no hay forma de distinguir "0 resultados legítimos"
  de "falló la llamada" solo con la lista; si el llamador necesita esa distinción,
  debe revisar stderr o se puede extender después agregando un modo que devuelva
  también el error, igual que `fetch_vehicle`).
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

VPIC_BASE_URL = "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues"
VPIC_API_ROOT = "https://vpic.nhtsa.dot.gov/api/vehicles"
DEFAULT_TIMEOUT_S = 10

# Tipos de vehículo vPIC que se consideran "auto/SUV" para el drill-down sin VIN
# (ver get_all_makes). vPIC no tiene un único tipo "Car" que cubra SUVs/crossovers:
# los pickups/SUV grandes (ej. Mitsubishi Outlander Sport) caen bajo "Multipurpose
# Passenger Vehicle (MPV)", no bajo "Passenger Car". Por eso se pide la unión de
# ambos tipos. Ver docstring de get_all_makes() para el detalle de qué tan limpio
# queda este filtro.
_TIPOS_VEHICULO_AUTO = ("car", "multipurpose passenger vehicle (mpv)")

# T-A3 — MISMO CRITERIO REPLICADO EN site/js/vpicClient.js (función
# `MARCAS_INDUSTRIALES_EXCLUIDAS` / `getAllMakes`). Si se cambia esta lista,
# cambiar la de allá IDÉNTICA, o Python y JS mostrarán marcas distintas para
# el mismo usuario (camino VIN vs camino drill-down).
#
# POR QUÉ EXISTE ESTA LISTA (investigación contra la API real de vPIC, no
# asumida — ver PR de T-A3 para el detalle completo):
# La unión car+MPV (arriba) ya filtra la enorme mayoría de fabricantes
# industriales: de ~207 marcas que vPIC devuelve bajo el tipo "truck", solo
# 3 "se cuelan" también en car+MPV al momento de escribir esto (verificado a
# mano contra GetMakesForVehicleType/car, .../multipurpose%20passenger...,
# y .../truck): FREIGHTLINER, BLUE BIRD y ORION BUS. Las ~204 restantes
# (Peterbilt, Kenworth, Mack, International, Western Star, Autocar, Capacity
# Trucks, Thomas Built, Oshkosh, Navistar, Hino, etc.) NUNCA aparecen en
# car/MPV y ya quedan fuera solo con el filtro de tipos — no necesitan estar
# en esta lista para que el resultado hoy sea correcto, pero se agregan
# igual como lista de exclusión EXPLÍCITA (no heurística) para no depender
# de que vPIC nunca reclasifique una marca de camión/bus hacia car/MPV en el
# futuro; es más fácil de auditar y de extender a mano que inventar una
# regla automática (ej. "solo aparece bajo truck" ya es cierto para casi
# todas sin necesidad de código, así que no hay heurística frágil que
# mantener).
#
# Fuente de la lista: fabricantes de camiones pesados/semirremolques/buses
# comerciales ampliamente conocidos (dominio público, ninguno vende autos ni
# SUV de consumo), más los 3 confirmados arriba que sí aparecen en car/MPV
# hoy. Comparación exacta por nombre en MAYÚSCULAS tal como lo devuelve
# vPIC (NO por substring, para no atrapar por accidente nombres legítimos
# que contienen la palabra, ej. "SPRINTER (DODGE OR FREIGHTLINER)" es una
# van MPV real de Mercedes-Benz/Dodge y debe quedarse).
#
# MARCAS LÍMITE que se decidió NO excluir (ver razonamiento en el PR):
# - ISUZU: vPIC la clasifica bajo car Y bajo MPV (no solo truck), y vendió
#   SUVs de consumo en EE. UU. por décadas (Trooper, Rodeo, Axiom, Ascender)
#   hasta 2009. Aunque hoy en EE. UU. solo vende camiones medianos
#   comerciales, el filtro aquí es sobre el catálogo vPIC (que incluye
#   histórico), así que se mantiene DENTRO.
_MARCAS_INDUSTRIALES_EXCLUIDAS = frozenset(
    {
        # Confirmadas: aparecen en car/MPV hoy pero son 100% industriales.
        "FREIGHTLINER",
        "BLUE BIRD",
        "ORION BUS",
        # Defensa en profundidad: fabricantes de camiones pesados/buses
        # ampliamente conocidos que hoy NO aparecen en car/MPV (confirmado
        # contra la API real), pero se excluyen explícitamente por si vPIC
        # cambia su clasificación más adelante.
        "PETERBILT",
        "KENWORTH",
        "MACK",
        "INTERNATIONAL",
        "WESTERN STAR",
        "AUTOCAR",
        "AUTOCAR INDUSTRIES",
        "CAPACITY TRUCKS",
        "THOMAS BUILT",
        "OSHKOSH",
        "NAVISTAR",
        "HINO",
        "SPARTAN MOTORS",
        "PIERCE MANUFACTURING",
        "CRANE CARRIER COMPANY (CCC)",
        "E-ONE",
        "KALMAR",
        "DENNIS EAGLE",
    }
)

# Un VIN válido: 17 caracteres alfanuméricos, sin I, O ni Q (se confunden con 1 y 0).
_VIN_RE = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$", re.IGNORECASE)

# Códigos de error de vPIC que indican que el VIN NO se pudo decodificar de forma
# confiable (lista no exhaustiva, basada en la documentación pública de vPIC).
# El código "0" siempre significa "decodificado limpio" y puede venir combinado
# con códigos de advertencia (ej. "0,12") que SÍ dejan datos utilizables.
# Nota: el código "1" (dígito verificador no calcula) se trata como advertencia,
# no como fatal, porque vPIC puede seguir devolviendo make/model/year correctos
# para VINs de ejemplo/documentación cuyo check digit no es válido; en ese caso
# igual exigimos abajo que `make` y `model` vengan no vacíos para aceptar el VIN.
_FATAL_ERROR_CODES = {"6", "7", "8", "9", "11", "400"}


def _vehicle_result_template(vin: str) -> dict[str, Any]:
    """Esqueleto común para éxito y error: mismas claves siempre."""
    return {
        "id": None,
        "make": None,
        "model": None,
        "year": None,
        "trim": None,
        "engine": None,
        "vin": vin,
        "error": None,
    }


def _build_engine_string(result: dict[str, Any]) -> Optional[str]:
    """Arma una descripción legible del motor a partir de los campos de vPIC.

    vPIC separa el motor en varios campos (cilindrada, cilindros, combustible,
    modelo de motor, caballos de fuerza). Como `vehicles.json` solo tiene un
    campo `engine` (string|null), los combinamos en una sola descripción.
    """
    partes: list[str] = []

    displacement = (result.get("DisplacementL") or "").strip()
    if displacement:
        try:
            partes.append(f"{float(displacement):.1f}L")
        except ValueError:
            partes.append(f"{displacement}L")

    cylinders = (result.get("EngineCylinders") or "").strip()
    if cylinders:
        partes.append(f"{cylinders}cil")

    fuel = (result.get("FuelTypePrimary") or "").strip()
    if fuel:
        partes.append(fuel)

    hp = (result.get("EngineHP") or "").strip()
    if hp:
        partes.append(f"{hp}HP")

    engine_model = (result.get("EngineModel") or "").strip()
    if engine_model:
        partes.append(f"({engine_model})")

    if not partes:
        return None
    return " ".join(partes)


def _extract_trim(result: dict[str, Any]) -> Optional[str]:
    trim = (result.get("Trim") or "").strip()
    if trim:
        return trim
    trim2 = (result.get("Trim2") or "").strip()
    if trim2:
        return trim2
    series = (result.get("Series") or "").strip()
    if series:
        return series
    return None


def fetch_vehicle(vin: str, timeout: int = DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    """Resuelve un VIN contra vPIC y devuelve un dict con el esquema de
    `vehicles.json` (id, make, model, year, trim, engine) más `vin` y `error`.

    Nunca lanza una excepción: cualquier problema (VIN mal formado, timeout,
    error de red, respuesta inesperada) se captura y se reporta en la clave
    `error` del dict devuelto, dejando el resto de campos en `None`.
    """
    vin_normalizado = (vin or "").strip().upper()
    salida = _vehicle_result_template(vin_normalizado)

    if not vin_normalizado:
        salida["error"] = "VIN vacío."
        return salida

    if not _VIN_RE.match(vin_normalizado):
        salida["error"] = (
            f"VIN '{vin_normalizado}' no tiene el formato esperado "
            "(17 caracteres alfanuméricos, sin I/O/Q)."
        )
        return salida

    url = f"{VPIC_BASE_URL}/{urllib.parse.quote(vin_normalizado)}?format=json"

    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            cuerpo = resp.read()
    except urllib.error.HTTPError as exc:
        salida["error"] = f"vPIC devolvió HTTP {exc.code} para VIN {vin_normalizado}."
        return salida
    except urllib.error.URLError as exc:
        salida["error"] = f"No se pudo contactar vPIC ({exc.reason})."
        return salida
    except TimeoutError:
        salida["error"] = f"Timeout consultando vPIC para VIN {vin_normalizado}."
        return salida
    except Exception as exc:  # defensivo: nunca debe tumbar el pipeline
        salida["error"] = f"Error de red inesperado consultando vPIC: {exc}"
        return salida

    try:
        datos = json.loads(cuerpo)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        salida["error"] = f"Respuesta de vPIC no es JSON válido: {exc}"
        return salida

    resultados = datos.get("Results") if isinstance(datos, dict) else None
    if not resultados:
        salida["error"] = "vPIC no devolvió resultados para este VIN."
        return salida

    result = resultados[0]

    error_code_raw = (result.get("ErrorCode") or "").strip()
    codigos = {c.strip() for c in error_code_raw.split(",") if c.strip()}
    codigos_fatales = codigos & _FATAL_ERROR_CODES

    make = (result.get("Make") or "").strip()
    model = (result.get("Model") or "").strip()
    year_raw = (result.get("ModelYear") or "").strip()

    if codigos_fatales or not make or not model:
        error_text = (result.get("ErrorText") or "").strip()
        mensaje = error_text or "vPIC no pudo decodificar este VIN."
        salida["error"] = f"VIN inválido o no reconocido: {mensaje}"
        return salida

    try:
        year = int(year_raw) if year_raw else None
    except ValueError:
        year = None

    salida["id"] = f"vin-{vin_normalizado}"
    salida["make"] = make.title() if make.isupper() else make
    salida["model"] = model
    salida["year"] = year
    salida["trim"] = _extract_trim(result)
    salida["engine"] = _build_engine_string(result)
    salida["error"] = None
    return salida


def fetch_vehicles(vins: list[str], timeout: int = DEFAULT_TIMEOUT_S) -> list[dict[str, Any]]:
    """Resuelve una lista de VINs, uno por uno. Un VIN con error no detiene
    la resolución de los demás (cada llamada a fetch_vehicle ya es segura)."""
    return [fetch_vehicle(vin, timeout=timeout) for vin in vins]


def _vpic_get_json(url: str, timeout: int) -> Optional[dict[str, Any]]:
    """Helper interno compartido por get_all_makes/get_models_for_make_year.

    Mismo patrón defensivo que fetch_vehicle: nunca lanza excepción. Si algo
    sale mal (red, HTTP, JSON), avisa por stderr y devuelve None (el llamador
    lo traduce en lista vacía).
    """
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            cuerpo = resp.read()
    except urllib.error.HTTPError as exc:
        print(f"vPIC devolvió HTTP {exc.code} para {url}.", file=sys.stderr)
        return None
    except urllib.error.URLError as exc:
        print(f"No se pudo contactar vPIC ({exc.reason}) para {url}.", file=sys.stderr)
        return None
    except TimeoutError:
        print(f"Timeout consultando vPIC: {url}.", file=sys.stderr)
        return None
    except Exception as exc:  # defensivo: nunca debe tumbar el pipeline
        print(f"Error de red inesperado consultando vPIC ({url}): {exc}", file=sys.stderr)
        return None

    try:
        return json.loads(cuerpo)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"Respuesta de vPIC no es JSON válido ({url}): {exc}", file=sys.stderr)
        return None


def get_all_makes(timeout: int = DEFAULT_TIMEOUT_S) -> list[dict[str, Any]]:
    """Devuelve la lista de marcas de auto/SUV disponibles en vPIC, para el
    drill-down "marca → modelo → año" (camino alterno al VIN, ver PLAN.md).

    Cada elemento: {"id": int, "name": str} (nombre con capitalización "Title
    Case" en vez del MAYÚSCULAS que devuelve vPIC crudo, igual que fetch_vehicle
    hace con `make`). Lista ordenada alfabéticamente por `name`.

    SOBRE EL FILTRADO (documentado como pide la tarea, porque NO quedó perfecto):
    vPIC's `GetAllMakes` devuelve ~12,000 "marcas" (incluye fabricantes de
    remolques, carrocerías de buses, golf carts, motos, camiones pesados, etc. —
    cualquier entidad que haya registrado un VIN con NHTSA). No hay un endpoint
    `GetAllMakes` con parámetro de filtro por tipo. Lo que SÍ existe es
    `GetMakesForVehicleType/<tipo>`, así que esta función pide la UNIÓN de los
    tipos "car" (Passenger Car) y "multipurpose passenger vehicle (mpv)" (donde
    caen SUVs/crossovers como el Outlander Sport) y deduplica por nombre.
    Verificado a mano: "MITSUBISHI" aparece en ambos tipos; "HARLEY-DAVIDSON"
    (moto) NO aparece en ninguno de los dos — el filtro funciona para el caso
    moto. No se filtró también por "truck" a propósito (pickups ligeras como
    F-150/Silverado caen bajo "truck" en vPIC, no bajo car/mpv) — si el
    frontend más adelante quiere incluir pickups, se puede ampliar
    `_TIPOS_VEHICULO_AUTO` agregando "truck", pero eso metería de vuelta
    fabricantes de camiones pesados/remolques (varias decenas de marcas
    industriales), así que se dejó fuera por ahora y se deja esta nota para
    quien integre el frontend: "si faltan pickups comunes (F-150, Silverado,
    Ram, Tacoma) en el selector, es por este filtro, no por un bug."

    FILTRO ADICIONAL (T-A3): la unión car+MPV por sí sola deja colar algunos
    fabricantes 100% industriales (camiones pesados/buses comerciales) que
    vPIC también cataloga bajo esos tipos — confirmado contra la API real:
    FREIGHTLINER, BLUE BIRD y ORION BUS aparecen en car/MPV junto a
    Toyota/BMW/Mitsubishi. Por eso, después de la unión, se excluyen por
    nombre exacto las marcas en `_MARCAS_INDUSTRIALES_EXCLUIDAS` (lista
    explícita y auditable, no heurística — ver el comentario junto a esa
    constante para el razonamiento completo y las marcas límite que se
    decidió mantener, ej. Isuzu).
    """
    marcas_por_nombre: dict[str, int] = {}
    for tipo in _TIPOS_VEHICULO_AUTO:
        url = f"{VPIC_API_ROOT}/GetMakesForVehicleType/{urllib.parse.quote(tipo)}?format=json"
        datos = _vpic_get_json(url, timeout=timeout)
        if not datos:
            continue
        resultados = datos.get("Results") if isinstance(datos, dict) else None
        if not resultados:
            continue
        for item in resultados:
            nombre_crudo = (item.get("MakeName") or "").strip()
            id_crudo = item.get("MakeId")
            if not nombre_crudo or id_crudo is None:
                continue
            if nombre_crudo.upper() in _MARCAS_INDUSTRIALES_EXCLUIDAS:
                continue
            nombre = nombre_crudo.title() if nombre_crudo.isupper() else nombre_crudo
            # Si la misma marca aparece en ambos tipos, se queda con el primer id visto.
            marcas_por_nombre.setdefault(nombre, id_crudo)

    return [
        {"id": marcas_por_nombre[nombre], "name": nombre}
        for nombre in sorted(marcas_por_nombre, key=str.casefold)
    ]


def get_models_for_make_year(
    make: str, year: int, timeout: int = DEFAULT_TIMEOUT_S
) -> list[dict[str, Any]]:
    """Devuelve los modelos de `make` para el año `year` según vPIC, para el
    paso siguiente del drill-down "marca → modelo → año".

    Cada elemento: {"id": int, "name": str}. Lista ordenada alfabéticamente por
    `name`. `make` acepta cualquier capitalización (vPIC no distingue
    mayúsculas/minúsculas para este endpoint). Si `make`/`year` no existen o no
    hay modelos para esa combinación, o si hay un problema de red/HTTP/JSON,
    se devuelve lista vacía (mismo patrón defensivo que get_all_makes/
    fetch_vehicle: nunca lanza excepción).

    PROBLEMA CONOCIDO (documentado, no se resolvió acá): vPIC no hace match
    exacto por marca en este endpoint. `get_models_for_make_year("Mitsubishi",
    2020)` devuelve también los modelos de camiones "Mitsubishi Fuso" (otra
    marca con su propio Make_ID en vPIC) mezclados con los del Mitsubishi de
    pasajeros, porque vPIC compara por substring/prefijo de nombre de marca,
    no por igualdad exacta. Esta función NO filtra eso (se mantiene fiel a lo
    que devuelve vPIC para no introducir falsos negativos con otras marcas
    cuyo nombre varía), así que quien integre el frontend debe saber que la
    lista de modelos puede incluir series de otra sub-marca con nombre similar.
    """
    marca = (make or "").strip()
    if not marca:
        print("get_models_for_make_year: 'make' vacío.", file=sys.stderr)
        return []
    try:
        anio = int(year)
    except (TypeError, ValueError):
        print(f"get_models_for_make_year: año inválido: {year!r}.", file=sys.stderr)
        return []

    url = (
        f"{VPIC_API_ROOT}/GetModelsForMakeYear/make/{urllib.parse.quote(marca)}"
        f"/modelyear/{anio}?format=json"
    )
    datos = _vpic_get_json(url, timeout=timeout)
    if not datos:
        return []
    resultados = datos.get("Results") if isinstance(datos, dict) else None
    if not resultados:
        return []

    modelos_por_nombre: dict[str, int] = {}
    for item in resultados:
        nombre = (item.get("Model_Name") or "").strip()
        id_crudo = item.get("Model_ID")
        if not nombre or id_crudo is None:
            continue
        modelos_por_nombre.setdefault(nombre, id_crudo)

    return [
        {"id": modelos_por_nombre[nombre], "name": nombre}
        for nombre in sorted(modelos_por_nombre, key=str.casefold)
    ]


def _main(argv: list[str]) -> int:
    if not argv:
        print("Uso: python pipeline/fetch_vehicles.py VIN1 [VIN2 ...]", file=sys.stderr)
        return 1
    resultados = fetch_vehicles(argv)
    print(json.dumps(resultados, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
