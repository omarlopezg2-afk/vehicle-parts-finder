"""Pruebas de T-A4: criterio de datos para excluir "fabricantes-cascarón"
del selector marca → modelo → año.

Fija los casos pedidos en TASKS.md (ver fila T-A4): excluidos por nombre
exacto Autocar Ltd, Execucoach Inc, Londoncoach Inc, Daytona Coach Builders,
Creative Coachworks; presentes Toyota, Mitsubishi, Honda, BMW, Byd, Sprinter
(Dodge Or Freightliner), Morgan, Sterling Motor Car.

Igual que test_fetch_vehicles_makes.py (T-A2/T-A3), hace llamadas HTTP reales
a vPIC salvo que ya exista un snapshot en `data/raw/vpic_cache/` (ver
`_vpic_get_json_cached` en fetch_vehicles.py): sin red Y sin caché estos tests
fallarán con un error de conexión -- es esperado y documentado, no hay modo
mock dedicado porque vPIC no requiere llave. El propio pipeline SÍ tolera esa
falta de red en producción (ver docstring de get_all_makes: caché -> snapshot
offline -> fixture commiteado); estos tests ejercitan el camino normal
(con red, o con el caché ya poblado por una corrida anterior).

Ejecutar:
    python3 -m unittest pipeline/tests/test_fetch_vehicles_criterio_marcas.py -v
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import unittest
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fetch_vehicles  # noqa: E402
from fetch_vehicles import (  # noqa: E402
    _es_fabricante_cascaron,
    _normalizar_nombre_marca,
    get_all_makes,
)

# Respuestas REALES de vPIC, grabadas una vez (ver el fixture). Se reproducen
# para que estas pruebas no dependan de la red: el CI se puso rojo precisamente
# porque vPIC devolvió HTTP 403 a los servidores de GitHub y una prueba que sale
# a internet puede fallar por causas ajenas al código.
_FIXTURE_MODELOS = (
    pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "vpic_models_for_make.sample.json"
)

# Para resolver la URL pedida sin ambigüedad.
_ID_A_NOMBRE = {
    8395: "Autocar Ltd",
    5545: "Execucoach Inc",
    629: "Creative Coachworks",
    448: "Toyota",
    481: "Mitsubishi",
}


def _registrar_limpieza(destino, funcion, *args):
    """En una clase se usa addClassCleanup; en una instancia, addCleanup."""
    if hasattr(destino, "addClassCleanup"):
        destino.addClassCleanup(funcion, *args)
    else:
        destino.addCleanup(funcion, *args)


def _instalar_doble_todo_offline(caso_de_prueba):
    """Simula que vPIC no responde NADA: fuerza el camino offline del pipeline
    (snapshot -> fixture commiteado), que es exactamente lo que corre en producción
    cuando el servicio está caído o devuelve 403, como pasó en el CI."""
    original = fetch_vehicles._vpic_get_json
    _registrar_limpieza(caso_de_prueba, setattr, fetch_vehicles, "_vpic_get_json", original)
    fetch_vehicles._vpic_get_json = lambda url, timeout=30: None


def _instalar_doble_sin_red(caso_de_prueba, sin_datos=()):
    """Sustituye la descarga de vPIC por las respuestas grabadas.

    Cualquier intento de salir a la red hace fallar la prueba a propósito: si el
    doble no tuviera respuesta, una prueba que "pasa" podría estar pasando por una
    llamada real, que es justo lo que no queremos volver a tener.
    """
    original = fetch_vehicles._vpic_get_json
    _registrar_limpieza(caso_de_prueba, setattr, fetch_vehicles, "_vpic_get_json", original)
    grabado = json.loads(_FIXTURE_MODELOS.read_text(encoding="utf-8"))

    def sin_red(url, timeout=30):
        if "GetModelsForMake/" in url:
            nombre = urllib.parse.unquote(url.split("GetModelsForMake/")[1].split("?")[0])
            if nombre in sin_datos:
                return None  # simula que vPIC no tiene datos para esa marca
            for make_id, conocido in _ID_A_NOMBRE.items():
                if conocido == nombre:
                    return grabado.get(f"models_for_make__{make_id}")
            raise AssertionError(
                f"la prueba pidió {nombre!r} y no hay respuesta grabada: "
                "no debe salir a la red"
            )
        if "GetMakesForVehicleType" in url or "GetAllMakes" in url:
            # El catálogo completo son cientos de marcas: se devuelve None para que
            # get_all_makes() use su camino offline (snapshot -> fixture).
            return None
        raise AssertionError(f"la prueba intentó salir a la red: {url}")

    fetch_vehicles._vpic_get_json = sin_red


# Casos fijos por TASKS.md T-A4.
_DEBEN_EXCLUIRSE = [
    "Autocar Ltd",
    "Execucoach Inc",
    "Londoncoach Inc",
    "Daytona Coach Builders",
    "Creative Coachworks",
]

_DEBEN_PERMANECER = [
    "Toyota",
    "Mitsubishi",
    "Honda",
    "Bmw",  # get_all_makes normaliza MAYÚSCULAS -> Title Case: "BMW" -> "Bmw"
    "Byd",
    "Sprinter (Dodge Or Freightliner)",
    "Morgan",
    "Sterling Motor Car",
]


class TestCriterioDeDatosFabricanteCascaron(unittest.TestCase):
    """Fija get_all_makes() contra los casos pedidos en TASKS.md T-A4."""

    @classmethod
    def setUpClass(cls):
        # Sin red: se fuerza el camino offline (snapshot -> fixture), que es el que
        # corre en producción cuando vPIC no responde. Así la prueba es rápida y no
        # depende de un servicio de terceros.
        _instalar_doble_todo_offline(cls)
        cls.marcas = get_all_makes()
        cls.nombres = {m["name"] for m in cls.marcas}

    def test_hay_marcas_suficientes(self):
        # Defensa contra un fallo silencioso (ej. red caída Y sin caché Y sin
        # fixture): si esto falla, todo lo demás de esta clase es ruido.
        self.assertGreater(len(self.marcas), 50)

    def test_excluidos_por_nombre_exacto(self):
        for nombre in _DEBEN_EXCLUIRSE:
            with self.subTest(marca=nombre):
                self.assertNotIn(
                    nombre,
                    self.nombres,
                    f"'{nombre}' debería estar excluida (fabricante-cascarón) "
                    "pero sigue en get_all_makes().",
                )

    def test_marcas_de_consumo_reales_permanecen(self):
        for nombre in _DEBEN_PERMANECER:
            with self.subTest(marca=nombre):
                self.assertIn(
                    nombre,
                    self.nombres,
                    f"'{nombre}' es una marca de consumo real y NO debería "
                    "haber sido excluida por el criterio de T-A4.",
                )

    def test_sin_duplicados_tras_el_nuevo_filtro(self):
        nombres_lista = [m["name"] for m in self.marcas]
        self.assertEqual(len(nombres_lista), len(set(nombres_lista)))

    def test_lista_sigue_ordenada_alfabeticamente(self):
        nombres_lista = [m["name"] for m in self.marcas]
        self.assertEqual(nombres_lista, sorted(nombres_lista, key=str.casefold))

    def test_conteo_total_documentado(self):
        # Antes de T-A4 (solo filtros 1+2 de get_all_makes): 244 marcas.
        # Con el filtro 3 (T-A4): se excluyen 22 adicionales -> 222.
        # No se fija un número exacto (vPIC puede agregar/quitar marcas con
        # el tiempo), pero si el conteo se desvía demasiado del rango
        # esperado, algo cambió que vale la pena mirar a mano.
        self.assertGreater(len(self.marcas), 150)
        self.assertLess(len(self.marcas), 244)


class TestEsFabricanteCascaron(unittest.TestCase):
    """Pruebas unitarias directas de `_es_fabricante_cascaron` (sin pasar por
    get_all_makes completo), para los 3 casos del criterio que SÍ detecta por
    patrón automático (no por la lista residual explícita)."""

    def setUp(self):
        _instalar_doble_sin_red(self)

    def test_autocar_ltd_es_cascaron(self):
        self.assertTrue(_es_fabricante_cascaron("Autocar Ltd", 8395, timeout=10))

    def test_execucoach_inc_es_cascaron(self):
        self.assertTrue(_es_fabricante_cascaron("Execucoach Inc", 5545, timeout=10))

    def test_creative_coachworks_es_cascaron(self):
        self.assertTrue(_es_fabricante_cascaron("Creative Coachworks", 629, timeout=10))

    def test_toyota_no_es_cascaron(self):
        self.assertFalse(_es_fabricante_cascaron("Toyota", 448, timeout=10))

    def test_mitsubishi_no_es_cascaron(self):
        self.assertFalse(_es_fabricante_cascaron("Mitsubishi", 481, timeout=10))

    def test_sin_respuesta_no_inventa_datos(self):
        """Sin dato de vPIC el criterio devuelve None, nunca False: excluir por
        suposición sería peor que no excluir. El llamador decide qué hacer."""
        _instalar_doble_sin_red(self, sin_datos={"Marca Inexistente Xyz"})
        self.assertIsNone(_es_fabricante_cascaron("Marca Inexistente Xyz", 999999, timeout=10))


class TestNormalizarNombreMarca(unittest.TestCase):
    """_normalizar_nombre_marca es pura (sin red): se prueba sin llamadas HTTP."""

    def test_quita_sufijo_inc(self):
        self.assertEqual(_normalizar_nombre_marca("Execucoach Inc"), "execucoach")

    def test_quita_sufijo_ltd(self):
        self.assertEqual(_normalizar_nombre_marca("Autocar Ltd"), "autocar")

    def test_sin_sufijo_no_cambia_mas_que_mayusculas(self):
        self.assertEqual(_normalizar_nombre_marca("Creative Coachworks"), "creative coachworks")

    def test_marca_y_su_propio_modelo_normalizan_igual(self):
        self.assertEqual(
            _normalizar_nombre_marca("Execucoach Inc"),
            _normalizar_nombre_marca("Execucoach"),
        )

    def test_vacio_no_lanza(self):
        self.assertEqual(_normalizar_nombre_marca(""), "")
        self.assertEqual(_normalizar_nombre_marca(None), "")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
