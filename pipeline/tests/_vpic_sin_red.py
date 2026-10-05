"""Utilidades para que las pruebas del pipeline NO dependan de la red.

Contexto (04/10/2026): estas pruebas llamaban a vPIC —la API pública de NHTSA— **en vivo**.
Eso las volvía una lotería: el CI de GitHub recibió **HTTP 403** por límite de peticiones y
fallaron pruebas sin que el código tuviera nada malo. La prueba definitiva de que eran
inestables: con el **mismo código**, la matriz de Python 3.12 pasó y la 3.11 falló. Además
hacían que la suite tardara ~39 minutos.

Las respuestas **reales** de vPIC están grabadas una sola vez en
`pipeline/fixtures/vpic_models_for_make.sample.json` (se volverán a grabar si vPIC cambia).
Aquí viven los dos dobles que las reproducen:

- `doble_todo_offline`: simula que vPIC no responde (fuerza el camino offline del pipeline,
  que es el que corre en producción cuando el servicio está caído).
- `doble_con_fixture`: sirve las respuestas grabadas y **hace fallar la prueba si algo intenta
  salir a la red**, para que ninguna prueba pueda pasar "por casualidad" contra la API en vivo.
"""

from __future__ import annotations

import json
import pathlib
import urllib.parse

FIXTURE = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "vpic_models_for_make.sample.json"

# Marca -> Make_ID, para resolver las URLs de GetModelsForMake sin ambigüedad.
ID_A_NOMBRE = {
    8395: "Autocar Ltd",
    5545: "Execucoach Inc",
    629: "Creative Coachworks",
    448: "Toyota",
    481: "Mitsubishi",
}


def registrar_limpieza(destino, funcion, *args):
    """En una clase de unittest se usa addClassCleanup; en una instancia, addCleanup."""
    if hasattr(destino, "addClassCleanup"):
        destino.addClassCleanup(funcion, *args)
    else:
        destino.addCleanup(funcion, *args)


def _instalar(caso_de_prueba, doble):
    import fetch_vehicles

    original = fetch_vehicles._vpic_get_json
    registrar_limpieza(caso_de_prueba, setattr, fetch_vehicles, "_vpic_get_json", original)
    fetch_vehicles._vpic_get_json = doble


def doble_todo_offline(caso_de_prueba):
    """vPIC no responde NADA: fuerza el camino offline (snapshot -> fixture commiteado)."""
    _instalar(caso_de_prueba, lambda url, timeout=30: None)


def doble_con_fixture(caso_de_prueba, sin_datos=()):
    """Sirve las respuestas grabadas; revienta si algo intenta salir a la red."""
    grabado = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def doble(url, timeout=30):
        if "GetModelsForMake/" in url:
            nombre = urllib.parse.unquote(url.split("GetModelsForMake/")[1].split("?")[0])
            if nombre in sin_datos:
                return None  # simula que vPIC no tiene datos para esa marca
            for make_id, conocido in ID_A_NOMBRE.items():
                if conocido == nombre:
                    return grabado.get(f"models_for_make__{make_id}")
            raise AssertionError(
                f"la prueba pidió {nombre!r} y no hay respuesta grabada: no debe salir a la red"
            )
        if "GetModelsForMakeYear/" in url:
            partes = url.split("GetModelsForMakeYear/make/")[1].split("/modelyear/")
            nombre = urllib.parse.unquote(partes[0])
            anio = partes[1].split("?")[0]
            if nombre.strip().lower() == "mitsubishi" and anio == "2020":
                return grabado.get("models_for_make_year__mitsubishi__2020")
            return None  # combinación sin datos: la función devuelve lista vacía
        if "GetMakesForVehicleType" in url or "GetAllMakes" in url:
            # El catálogo completo son cientos de marcas: se sirve del fixture commiteado
            # (camino offline), igual que en producción cuando vPIC no responde.
            return None
        raise AssertionError(f"la prueba intentó salir a la red: {url}")

    _instalar(caso_de_prueba, doble)
