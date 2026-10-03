"""Tests de pipeline/build_index.py (T-D1).

Convención compartida con los demás tests de pipeline/tests/ (ver
test_fetch_vehicles.py, test_fetch_ebay.py, test_normalize.py): sys.path
insert + import por nombre simple, sin paquete.

Usa unittest (stdlib) a propósito, igual que los demás módulos: corre
out-of-the-box sin instalar nada además de lo que ya pide requirements.txt.

NOTA sobre red: `build_vehicles()` intenta una llamada real a vPIC
(comportamiento de fetch_vehicles.py, T-A1) y cae a un fallback fijo si
falla. Estos tests NO dependen de que esa llamada tenga éxito: se prueba el
fallback directamente monkeypatcheando `fetch_vehicle` para simular "sin
red", que es exactamente el modo exigido por T-D1 (build completamente
mock). También hay un test que ejercita el build completo tal como corre en
CI (con o sin red disponible, el resultado debe ser válido).
"""

from __future__ import annotations

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import build_index  # noqa: E402
from normalize import normalize_part_number  # noqa: E402


class TestBuildVehiclesOffline(unittest.TestCase):
    """build_vehicles() debe funcionar sin red (requisito de T-D1)."""

    def test_fallback_cuando_vpic_lanza_excepcion(self):
        with mock.patch.object(build_index, "fetch_vehicle", side_effect=RuntimeError("sin red")):
            vehicles = build_index.build_vehicles()
        self.assertEqual(len(vehicles), 1)
        self.assertEqual(vehicles[0]["make"], "Mitsubishi")
        self.assertEqual(vehicles[0]["model"], "Outlander Sport")
        self.assertEqual(vehicles[0]["year"], 2020)

    def test_fallback_cuando_vpic_devuelve_error_controlado(self):
        resultado_con_error = {
            "id": None, "make": None, "model": None, "year": None,
            "trim": None, "engine": None, "vin": build_index.EXAMPLE_VIN,
            "error": "No se pudo contactar vPIC.",
        }
        with mock.patch.object(build_index, "fetch_vehicle", return_value=resultado_con_error):
            vehicles = build_index.build_vehicles()
        self.assertEqual(vehicles[0]["make"], "Mitsubishi")

    def test_usa_resultado_real_si_vpic_responde_bien(self):
        resultado_ok = {
            "id": "vin-XXX", "make": "Honda", "model": "Civic", "year": 2010,
            "trim": "EX", "engine": "1.8L", "vin": "XXX", "error": None,
        }
        with mock.patch.object(build_index, "fetch_vehicle", return_value=resultado_ok):
            vehicles = build_index.build_vehicles()
        self.assertEqual(vehicles, [{
            "id": "vin-XXX", "make": "Honda", "model": "Civic",
            "year": 2010, "trim": "EX", "engine": "1.8L",
        }])

    def test_esquema_exacto_vehicles_json(self):
        with mock.patch.object(build_index, "fetch_vehicle", side_effect=RuntimeError("sin red")):
            vehicles = build_index.build_vehicles()
        for clave in ("id", "make", "model", "year", "trim", "engine"):
            self.assertIn(clave, vehicles[0])
        self.assertNotIn("error", vehicles[0])
        self.assertNotIn("vin", vehicles[0])


class TestBuildPartsOffline(unittest.TestCase):
    """build_parts() debe funcionar sin red ni llaves de eBay."""

    def setUp(self):
        self._env_patch = mock.patch.dict(os.environ, {}, clear=True)
        self._env_patch.start()
        self.vehiculo_ejemplo = {
            "id": "vin-TEST", "make": "Mitsubishi", "model": "Outlander Sport",
            "year": 2020, "trim": None, "engine": None,
        }

    def tearDown(self):
        self._env_patch.stop()

    def test_devuelve_al_menos_las_partes_del_seed(self):
        parts = build_index.build_parts(self.vehiculo_ejemplo)
        seed = build_index._load_seed_parts()
        self.assertEqual(len(parts), len(seed))
        self.assertGreater(len(parts), 0)

    def test_cada_parte_tiene_las_claves_del_contrato(self):
        parts = build_index.build_parts(self.vehiculo_ejemplo)
        claves_esperadas = {
            "id", "part_number", "part_number_norm", "type", "brand", "name",
            "category", "epc_link", "image", "equivalents", "fitment_ids",
            "offers", "updated_at",
        }
        for parte in parts:
            self.assertEqual(claves_esperadas, set(parte.keys()))

    def test_epc_link_siempre_presente_como_clave(self):
        # Clave central de CONTRACTS.md: epc_link existe aunque url sea null.
        parts = build_index.build_parts(self.vehiculo_ejemplo)
        for parte in parts:
            self.assertIn("epc_link", parte)
            self.assertIn("source", parte["epc_link"])
            self.assertIn("url", parte["epc_link"])

    def test_part_number_norm_coincide_con_normalize(self):
        parts = build_index.build_parts(self.vehiculo_ejemplo)
        for parte in parts:
            self.assertEqual(
                parte["part_number_norm"],
                normalize_part_number(parte["part_number"]),
            )

    def test_offers_vienen_del_modo_mock_sin_llaves(self):
        parts = build_index.build_parts(self.vehiculo_ejemplo)
        al_menos_una_con_offers = any(len(p["offers"]) > 0 for p in parts)
        self.assertTrue(al_menos_una_con_offers)
        for parte in parts:
            for offer in parte["offers"]:
                self.assertEqual(offer["store"], "eBay")

    def test_mitsubishi_del_seed_resuelve_7zap_para_outlander_sport(self):
        # El seed trae una parte Mitsubishi de filtro-aceite; para el
        # vehículo de ejemplo (Outlander Sport 2020) get_epc_links (T-C1)
        # SÍ debe poder resolver un link real de 7zap.
        parts = build_index.build_parts(self.vehiculo_ejemplo)
        mitsubishi_parts = [p for p in parts if p["brand"] == "Mitsubishi"]
        self.assertTrue(mitsubishi_parts)
        self.assertEqual(mitsubishi_parts[0]["epc_link"]["source"], "7zap")
        self.assertIsNotNone(mitsubishi_parts[0]["epc_link"]["url"])


class TestBuildSearchIndex(unittest.TestCase):
    def test_derivado_correctamente_de_parts(self):
        parts = [
            {
                "id": "a", "part_number_norm": "ABC123", "name": "Filtro",
                "brand": "Toyota", "otros_campos": "ignorados",
            }
        ]
        index = build_index.build_search_index(parts)
        self.assertEqual(index, [{
            "id": "a", "part_number_norm": "ABC123",
            "name": "Filtro", "brand": "Toyota",
        }])


class TestLoadCategories(unittest.TestCase):
    def test_categories_existente_tiene_esquema_valido(self):
        categorias = build_index.load_categories()
        self.assertIsInstance(categorias, list)
        self.assertGreater(len(categorias), 0)
        for cat in categorias:
            for clave in ("slug", "name_es", "svg"):
                self.assertIn(clave, cat)


class TestBuildIndexEndToEnd(unittest.TestCase):
    """El build completo debe producir los 4 archivos y pasar validate.py,
    sin red ni llaves de eBay (requisito explícito de T-D1)."""

    def test_main_genera_los_4_archivos_validos_sin_llaves(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            exit_code = build_index.main()
        self.assertEqual(exit_code, 0)

        # Reusa el validador real (pipeline/validate.py) para confirmar
        # que el resultado de este build cumple CONTRACTS.md. pipeline/ ya
        # está en sys.path (insert al tope de este archivo).
        import validate  # noqa: E402

        errores = validate.run_validation()
        self.assertEqual(list(errores), [], msg="\n".join(errores))


if __name__ == "__main__":
    unittest.main()
