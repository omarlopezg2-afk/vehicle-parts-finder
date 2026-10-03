"""Cliente vPIC (NHTSA) para resolver un VIN a los campos de `vehicles.json`.

API usada (pública, sin llave):
    GET https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/<VIN>?format=json

Uso típico:
    from pipeline.fetch_vehicles import fetch_vehicle
    vehiculo = fetch_vehicle("JA4AP3AU0LU000302")
    if vehiculo["error"] is None:
        ...  # vehiculo cumple el esquema de CONTRACTS.md (vehicles.json)
    else:
        ...  # VIN inválido / problema de red: manejar sin tumbar el pipeline

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
DEFAULT_TIMEOUT_S = 10

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


def _main(argv: list[str]) -> int:
    if not argv:
        print("Uso: python pipeline/fetch_vehicles.py VIN1 [VIN2 ...]", file=sys.stderr)
        return 1
    resultados = fetch_vehicles(argv)
    print(json.dumps(resultados, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
