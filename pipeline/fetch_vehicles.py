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
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Optional

VPIC_BASE_URL = "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues"
VPIC_API_ROOT = "https://vpic.nhtsa.dot.gov/api/vehicles"
DEFAULT_TIMEOUT_S = 10

# vPIC empezó a devolver HTTP 403 para peticiones sin User-Agent (verificado en
# vivo 04/10/2026: el default de urllib -- sin header -- recibe 403 de forma
# consistente; con este header, 200). No es específico de T-A4: afecta
# fetch_vehicle igual que get_all_makes/get_models_for_make_year, así que se
# corrige una sola vez aquí y se usa en todas las peticiones del módulo.
_HTTP_HEADERS = {"User-Agent": "PartExact-pipeline/1.0 (+https://github.com/omarlopezg2-afk/vehicle-parts-finder)"}

# Caché en disco de respuestas de vPIC (T-A4). Vive en data/raw/ (ya ignorado por
# git, ver .gitignore) para no depender de la red en cada build: la primera
# ejecución que SÍ tiene red deja un snapshot; ejecuciones posteriores sin red
# reusan ese snapshot en vez de fallar. Mismo espíritu que _FALLBACK_VEHICLE en
# build_index.py, pero automático y por endpoint en vez de un único dict fijo.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VPIC_CACHE_DIR = os.path.join(_REPO_ROOT, "data", "raw", "vpic_cache")


def _cache_path(cache_key: str) -> str:
    nombre_archivo = re.sub(r"[^A-Za-z0-9_-]", "_", cache_key) + ".json"
    return os.path.join(_VPIC_CACHE_DIR, nombre_archivo)


def _cache_read(cache_key: str) -> Optional[Any]:
    try:
        with open(_cache_path(cache_key), "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _cache_write(cache_key: str, datos: Any) -> None:
    try:
        os.makedirs(_VPIC_CACHE_DIR, exist_ok=True)
        with open(_cache_path(cache_key), "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False)
    except OSError:
        pass  # el caché es una optimización; nunca debe tumbar el pipeline.

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

# --- T-A4: criterio de datos para "fabricante-cascarón" ---------------------
#
# Investigación en vivo (04/10/2026) contra GetModelsForMake/<marca> (CUALQUIER
# año/tipo, no solo 2020) mostró que el criterio propuesto originalmente
# ("¿tiene ≥1 modelo bajo car/mpv en 2020?") EXCLUYE marcas de consumo reales
# que no tienen catálogo justo en 2020: Byd (último modelo car/mpv en vPIC es
# 2015), Sprinter (Dodge Or Freightliner) (2003-2005), Morgan (su único
# registro car/mpv es 1985-2015, el resto de su catálogo es bajo "Motorcycle"/
# "Trailer"), Sterling Motor Car (1987-1991). Probar también con años fijos
# alternativos (1990, 2000, 2025...) tiene el mismo problema: siempre hay
# alguna marca real cuyo único año con datos cae fuera de la muestra.
#
# Criterio adoptado en su lugar (más fuerte, verificable igual contra la API
# real, sin depender de qué año se mire): una marca es "cascarón" si su
# catálogo COMPLETO en vPIC (GetModelsForMake, todos los años y tipos juntos)
# tiene ≤2 modelos distintos Y al menos uno de ellos es, normalizado, el mismo
# texto que el nombre de la marca (ignorando mayúsculas, puntuación y sufijos
# corporativos como Inc/Ltd/Corp/Co). Es el patrón de un registro NHTSA de un
# solo ensamblador/carrocero de bajísimo volumen que nunca metió un "modelo"
# real -- confirmado a mano contra los 5 casos pedidos en TASKS.md:
#   Autocar Ltd       -> 1 modelo, se llama "Autocar Ltd"       -> cascarón
#   Execucoach Inc    -> 1 modelo, se llama "Execucoach"        -> cascarón
#   Creative Coachworks -> 2 modelos, uno se llama "Creative Coachworks" -> cascarón
# y NO atrapa a ninguna marca de consumo real probada (Toyota, Mitsubishi,
# Honda, Bmw, Byd, Sprinter (Dodge Or Freightliner), Morgan, Sterling Motor
# Car: todas tienen >2 modelos distintos en su catálogo completo).
#
# Ejecutado contra las 244 marcas que devolvía get_all_makes antes de T-A4,
# este criterio automático excluye 20. Quedan 2 casos pedidos en TASKS.md que
# el patrón automático NO agarra porque su único modelo NO se llama igual que
# la marca (Daytona Coach Builders -> su único modelo es "Daytona Midgie-2";
# Londoncoach Inc -> su único modelo es "London Taxi", un taxi londinense
# reconvertido que nunca se vendió como auto de consumo en EE. UU.). Se
# agregan a mano como defensa en profundidad, mismo patrón que
# _MARCAS_INDUSTRIALES_EXCLUIDAS de arriba (lista explícita, auditable, no
# heurística frágil).
_FABRICANTES_CASCARON_RESIDUALES = frozenset({"DAYTONA COACH BUILDERS", "LONDONCOACH INC"})

# Snapshot estático (04/10/2026) de las marcas que _es_fabricante_cascaron
# detectó en vivo al momento de escribir esto. Se usa SOLO como último
# recurso cuando no hay red NI caché en disco para verificar una marca
# puntual (build en una máquina sin ninguna ejecución previa y sin
# conectividad) -- no reemplaza la consulta en vivo ni el caché: en cuanto
# hay uno de los dos, esos ganan. Limitación conocida: una marca-cascarón
# NUEVA que aparezca en vPIC después de esta fecha no se detecta en ese
# escenario extremo (sin red Y sin caché); si hay red o caché, sí.
_FABRICANTES_CASCARON_SNAPSHOT_OFFLINE = frozenset(
    {
        "1955 CUSTOM BELAIR",
        "AMPHI-RANGER",
        "AUTOCAR LTD",
        "AUTODELTA USA INC",
        "BAKKURA MOBILITY",
        "CODA",
        "CREATIVE COACHWORKS",
        "CX AUTOMOTIVE",
        "ELECTRIC MOBILE CARS",
        "EXECUCOACH INC",
        "GRUPPE B",
        "HUNTER DESIGN GROUP, LLC",
        "LA EXOTICS",
        "LITE CAR",
        "MATRIX MOTOR COMPANY",
        "PHOENIX CRUISER",
        "PHOENIX MOTORCARS",
        "PHOENIX TRX",
        "WORLD TRANSPORT AUTHORITY",
        "ZOOX",
    }
)

_SUFIJOS_CORPORATIVOS = (
    " incorporated",
    " inc",
    " ltd",
    " llc",
    " corp",
    " corporation",
    " co",
    " company",
)

_FIXTURE_MARCAS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "fixtures", "vpic_makes.sample.json"
)


def _cargar_fixture_marcas() -> list[dict[str, Any]]:
    """Carga el fixture commiteado `fixtures/vpic_makes.sample.json` (snapshot
    fijo de get_all_makes(), ya filtrado), para el caso extremo en que
    get_all_makes no tiene ni red ni ningún caché en disco."""
    try:
        with open(_FIXTURE_MARCAS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []


def _normalizar_nombre_marca(nombre: str) -> str:
    """Normaliza para comparar 'nombre de marca' vs. 'nombre de modelo':
    minúsculas, sin puntos/comas, sin sufijos corporativos comunes. Ej.:
    'Execucoach Inc' y 'Execucoach' normalizan al mismo texto."""
    limpio = re.sub(r"[.,]", "", (nombre or "").strip().lower())
    for sufijo in _SUFIJOS_CORPORATIVOS:
        if limpio.endswith(sufijo):
            limpio = limpio[: -len(sufijo)]
            break
    return limpio.strip()


def _es_fabricante_cascaron(nombre_marca: str, make_id: int, timeout: int) -> Optional[bool]:
    """True si el catálogo COMPLETO de `nombre_marca` en vPIC (cualquier año o
    tipo de vehículo, vía GetModelsForMake) tiene ≤2 modelos distintos y al
    menos uno normaliza igual al nombre de la marca (ver constantes de arriba
    para el razonamiento completo).

    Devuelve None (no True ni False) si no se pudo determinar ni con la API
    en vivo ni con caché en disco -- el llamador decide qué hacer con None
    (ver _FABRICANTES_CASCARON_SNAPSHOT_OFFLINE)."""
    url = f"{VPIC_API_ROOT}/GetModelsForMake/{urllib.parse.quote(nombre_marca)}?format=json"
    datos = _vpic_get_json_cached(url, cache_key=f"models_for_make__{make_id}", timeout=timeout)
    if datos is None:
        return None
    resultados = datos.get("Results") if isinstance(datos, dict) else None
    if not resultados:
        return None
    nombres_modelo = {
        (r.get("Model_Name") or "").strip() for r in resultados if r.get("Model_Name")
    }
    if not nombres_modelo or len(nombres_modelo) > 2:
        return False
    marca_norm = _normalizar_nombre_marca(nombre_marca)
    return any(_normalizar_nombre_marca(modelo) == marca_norm for modelo in nombres_modelo)


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
        cuerpo = _http_get_with_retry(url, timeout=timeout)
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


def _http_get_with_retry(url: str, timeout: int, max_reintentos: int = 2) -> bytes:
    """GET con reintento corto para HTTP 403/429 (verificado en vivo: vPIC
    aplica un rate-limit que a veces devuelve 403 de forma transitoria -- la
    MISMA url responde 200 segundos después sin cambiar nada). No es
    específico de T-A4: afecta tanto fetch_vehicle como get_all_makes/
    get_models_for_make_year, así que se centraliza aquí. Reintenta solo
    403/429 (no otros códigos HTTP, que sí son errores reales); backoff fijo
    corto porque esto corre en un pipeline con timeout de proceso acotado
    (GitHub Actions), no puede esperar minutos.

    Lanza la excepción tal cual si se agotan los reintentos, para que el
    llamador (_vpic_get_json / fetch_vehicle) la capture con su manejo
    habitual.
    """
    ultimo_error: Optional[Exception] = None
    for intento in range(max_reintentos + 1):
        try:
            req = urllib.request.Request(url, headers=_HTTP_HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            ultimo_error = exc
            if exc.code not in (403, 429) or intento == max_reintentos:
                raise
            time.sleep(2 * (intento + 1))
    assert ultimo_error is not None
    raise ultimo_error


def _vpic_get_json(url: str, timeout: int) -> Optional[dict[str, Any]]:
    """Helper interno compartido por get_all_makes/get_models_for_make_year.

    Mismo patrón defensivo que fetch_vehicle: nunca lanza excepción. Si algo
    sale mal (red, HTTP, JSON), avisa por stderr y devuelve None (el llamador
    lo traduce en lista vacía).
    """
    try:
        cuerpo = _http_get_with_retry(url, timeout=timeout)
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


def _vpic_get_json_cached(url: str, cache_key: str, timeout: int) -> Optional[dict[str, Any]]:
    """Como `_vpic_get_json`, pero con caché en disco en `data/raw/vpic_cache/`
    (T-A4): intenta la red primero; si la llamada falla (sin red, timeout,
    HTTP error), cae al último snapshot guardado para esa `cache_key`, si
    existe. Si la llamada SÍ tiene éxito, actualiza el snapshot. Así el
    pipeline tolera fallos de red después de la primera ejecución exitosa,
    sin inventar datos: solo reusa una respuesta real previa de vPIC."""
    datos = _vpic_get_json(url, timeout=timeout)
    if datos is not None:
        _cache_write(cache_key, datos)
        return datos
    return _cache_read(cache_key)


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

    FILTRO 2 (T-A3): la unión car+MPV por sí sola deja colar algunos
    fabricantes 100% industriales (camiones pesados/buses comerciales) que
    vPIC también cataloga bajo esos tipos — confirmado contra la API real:
    FREIGHTLINER, BLUE BIRD y ORION BUS aparecen en car/MPV junto a
    Toyota/BMW/Mitsubishi. Por eso, después de la unión, se excluyen por
    nombre exacto las marcas en `_MARCAS_INDUSTRIALES_EXCLUIDAS` (lista
    explícita y auditable, no heurística — ver el comentario junto a esa
    constante para el razonamiento completo y las marcas límite que se
    decidió mantener, ej. Isuzu).

    FILTRO 3 — CRITERIO BASADO EN DATOS (T-A4, agregado 04/10/2026): los
    filtros 1 y 2 de arriba (car+MPV menos lista de camiones/buses pesados)
    seguían dejando pasar una cola de ~20-22 "fabricantes" que son en realidad
    un único carrocero/ensamblador de muy bajo volumen (limusinas, coches
    fúnebres, kit-cars, conversiones) sin modelos reales de consumo — ej.
    Autocar Ltd, Execucoach Inc, Londoncoach Inc, Daytona Coach Builders,
    Creative Coachworks. Se probó primero el criterio "¿tiene ≥1 modelo bajo
    car/mpv en el año 2020?" pero se DESCARTÓ: excluía marcas de consumo
    reales cuyo catálogo car/mpv en vPIC no cae justo en 2020 (Byd: último
    registro 2015; Sprinter (Dodge Or Freightliner): 2003-2005; Morgan:
    1985-2015; Sterling Motor Car: 1987-1991) — cualquier año fijo tiene el
    mismo problema con alguna marca real.

    Criterio final adoptado: una marca se considera "fabricante-cascarón" (y
    se excluye) si su catálogo COMPLETO en vPIC (`GetModelsForMake`, sin
    filtrar por año ni tipo) tiene ≤2 modelos distintos Y al menos uno de esos
    "modelos" es, normalizado (minúsculas, sin puntuación/sufijos Inc-Ltd-
    Corp-Co), el mismo texto que el nombre de la marca — el patrón típico de
    un registro NHTSA que nunca metió un modelo real, solo repitió su propio
    nombre. Implementado en `_es_fabricante_cascaron`; ver el bloque de
    comentarios junto a `_FABRICANTES_CASCARON_RESIDUALES` para el detalle
    completo, los 2 casos residuales que necesitaron lista explícita (Daytona
    Coach Builders, Londoncoach Inc — su único modelo no repite el nombre de
    la marca) y las limitaciones conocidas.

    CONTEO (verificado en vivo el 04/10/2026, snapshot en
    data/raw/vpic_cache/ para reproducir sin red): antes de T-A4 (solo
    filtros 1+2), get_all_makes devolvía **244** marcas. Con el filtro 3
    (T-A4) se excluyen **22** adicionales (20 detectadas por el criterio
    automático + 2 residuales por nombre exacto), quedando **222** marcas.
    Las 8 marcas de consumo usadas como ancla en las pruebas (Toyota,
    Mitsubishi, Honda, Bmw, Byd, Sprinter (Dodge Or Freightliner), Morgan,
    Sterling Motor Car) se verificaron una por una y NINGUNA cae en el
    filtro 3.

    TOLERANCIA A FALLOS (T-A4), 3 niveles: (1) tanto `GetMakesForVehicleType`
    (filtro 1) como `GetModelsForMake` por marca (filtro 3) pasan por
    `_vpic_get_json_cached`, que cachea cada respuesta real en
    `data/raw/vpic_cache/*.json` (carpeta ya cubierta por `.gitignore`) y
    reusa el último snapshot si la red falla; (2) si una marca puntual no
    tiene ni red ni snapshot en caché para resolver el filtro 3, se usa
    `_FABRICANTES_CASCARON_SNAPSHOT_OFFLINE` (snapshot fijo de qué marcas se
    consideraron cascarón al momento de escribir esto); (3) si NO hay ni red
    ni ningún caché en disco (checkout limpio sin ejecución previa y sin
    conectividad, el caso que rompería un build), se usa el fixture
    commiteado `pipeline/fixtures/vpic_makes.sample.json` (snapshot completo
    de las 222 marcas ya filtradas) — mismo espíritu que `_FALLBACK_VEHICLE`
    en build_index.py, así el pipeline nunca devuelve una lista vacía solo
    por falta de conectividad.

    LIMITACIONES CONOCIDAS: (a) el umbral "≤2 modelos" es una heurística
    razonable, no una regla NHTSA — una marca de consumo real con solo 1 o 2
    modelos publicados Y que además comparta nombre con uno de ellos (caso
    límite no observado en los datos reales de hoy) se excluiría por error;
    (b) el filtro 3 agrega hasta 244 llamadas de red adicionales
    (`GetModelsForMake` por marca) la primera vez que no hay caché — se
    paralelizan con un pool de hilos para que no sea prohibitivo, pero sigue
    siendo más lento que antes de T-A4; ejecuciones siguientes reusan el
    caché y son instantáneas; (c) si `_FABRICANTES_CASCARON_SNAPSHOT_OFFLINE`
    queda desactualizado, un fabricante-cascarón nuevo después de esta fecha
    solo se detecta cuando SÍ hay red o caché (ver arriba).
    """
    marcas_por_nombre: dict[str, int] = {}
    for tipo in _TIPOS_VEHICULO_AUTO:
        url = f"{VPIC_API_ROOT}/GetMakesForVehicleType/{urllib.parse.quote(tipo)}?format=json"
        datos = _vpic_get_json_cached(url, cache_key=f"makes_for_vehicletype__{tipo}", timeout=timeout)
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

    # Filtro 3 (T-A4): consulta GetModelsForMake por cada marca candidata, en
    # paralelo (puede ser ~200+ llamadas la primera vez sin caché).
    def _evaluar(nombre_id: tuple[str, int]) -> tuple[str, Optional[bool]]:
        nombre, make_id = nombre_id
        return nombre, _es_fabricante_cascaron(nombre, make_id, timeout=timeout)

    candidatos = list(marcas_por_nombre.items())
    veredictos: dict[str, Optional[bool]] = {}
    if candidatos:
        with ThreadPoolExecutor(max_workers=16) as pool:
            for nombre, veredicto in pool.map(_evaluar, candidatos):
                veredictos[nombre] = veredicto

    marcas_finales: dict[str, int] = {}
    for nombre, make_id in marcas_por_nombre.items():
        if nombre.upper() in _FABRICANTES_CASCARON_RESIDUALES:
            continue
        veredicto = veredictos.get(nombre)
        if veredicto is None:
            # Sin red ni caché para esta marca puntual: último recurso, el
            # snapshot offline fijo (ver su docstring para limitaciones).
            veredicto = nombre.upper() in _FABRICANTES_CASCARON_SNAPSHOT_OFFLINE
        if veredicto:
            continue
        marcas_finales[nombre] = make_id

    if not marcas_finales:
        # Caso extremo: ni red ni caché de disco (ej. checkout limpio sin
        # ejecución previa, corriendo sin conectividad). Último recurso: el
        # fixture fijo pipeline/fixtures/vpic_makes.sample.json, snapshot
        # completo (ya filtrado por los 3 filtros) tomado el 04/10/2026. Se
        # commitea al repo (a diferencia de data/raw/vpic_cache/, que está en
        # .gitignore) justamente para cubrir este escenario: el pipeline
        # nunca debe devolver 0 marcas solo por falta de red.
        marcas_finales = {m["name"]: m["id"] for m in _cargar_fixture_marcas()}

    return [
        {"id": marcas_finales[nombre], "name": nombre}
        for nombre in sorted(marcas_finales, key=str.casefold)
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
