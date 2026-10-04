"""Tests del camino sin VIN (drill-down marca → modelo → año) de
pipeline/fetch_vehicles.py (T-A2).

Igual que test_fetch_vehicles.py, usa unittest (stdlib) y hace llamadas HTTP
reales a vPIC (API pública, sin llave). Si no hay red disponible, estos tests
fallarán con un error de conexión — es esperado y documentado (no hay modo
mock para este cliente porque vPIC no requiere llave).

Ejecutar:
    python3 -m unittest pipeline/tests/test_fetch_vehicles_makes.py -v
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetch_vehicles import get_all_makes, get_models_for_make_year


class TestGetAllMakes(unittest.TestCase):
    def test_mitsubishi_esta_en_la_lista(self):
        marcas = get_all_makes()
        nombres = [m["name"] for m in marcas]
        self.assertIn("Mitsubishi", nombres)

    def test_cada_marca_tiene_esquema_id_name(self):
        marcas = get_all_makes()
        self.assertGreater(len(marcas), 50)  # decenas de marcas de auto/SUV reales
        for marca in marcas[:10]:
            self.assertIn("id", marca)
            self.assertIn("name", marca)
            self.assertIsInstance(marca["id"], int)
            self.assertIsInstance(marca["name"], str)
            self.assertTrue(marca["name"])

    def test_lista_ordenada_alfabeticamente(self):
        marcas = get_all_makes()
        nombres = [m["name"] for m in marcas]
        self.assertEqual(nombres, sorted(nombres, key=str.casefold))

    def test_sin_duplicados_por_nombre(self):
        marcas = get_all_makes()
        nombres = [m["name"] for m in marcas]
        self.assertEqual(len(nombres), len(set(nombres)))

    def test_marcas_de_moto_conocidas_no_aparecen(self):
        # Documentado en el docstring de get_all_makes: el filtro car+MPV
        # excluye motos. Harley-Davidson es el caso de prueba más claro.
        marcas = get_all_makes()
        nombres = {m["name"] for m in marcas}
        self.assertNotIn("Harley-Davidson", nombres)
        self.assertNotIn("Harley Davidson", nombres)

    def test_fabricantes_de_camiones_pesados_excluidos(self):
        # T-A3: Freightliner aparece en car+MPV sin este filtro (verificado
        # contra la API real); Peterbilt y Kenworth nunca aparecen en
        # car+MPV pero están en la lista de exclusión explícita como
        # defensa en profundidad. Ninguno de los tres debe aparecer.
        marcas = get_all_makes()
        nombres = {m["name"] for m in marcas}
        self.assertNotIn("Freightliner", nombres)
        self.assertNotIn("Peterbilt", nombres)
        self.assertNotIn("Kenworth", nombres)

    def test_marcas_de_auto_consumo_conocidas_si_aparecen(self):
        # T-A3: el filtro de fabricantes industriales no debe tocar marcas
        # de auto/SUV/pickup de consumo reales.
        marcas = get_all_makes()
        nombres = {m["name"] for m in marcas}
        self.assertIn("Mitsubishi", nombres)
        self.assertIn("Toyota", nombres)
        self.assertIn("Ford", nombres)


class TestGetModelsForMakeYear(unittest.TestCase):
    def test_outlander_sport_esta_en_los_modelos_2020(self):
        modelos = get_models_for_make_year("Mitsubishi", 2020)
        nombres = [m["name"] for m in modelos]
        self.assertIn("Outlander Sport", nombres)

    def test_cada_modelo_tiene_esquema_id_name(self):
        modelos = get_models_for_make_year("Mitsubishi", 2020)
        self.assertGreater(len(modelos), 0)
        for modelo in modelos:
            self.assertIn("id", modelo)
            self.assertIn("name", modelo)
            self.assertIsInstance(modelo["id"], int)
            self.assertIsInstance(modelo["name"], str)
            self.assertTrue(modelo["name"])

    def test_lista_ordenada_alfabeticamente(self):
        modelos = get_models_for_make_year("Mitsubishi", 2020)
        nombres = [m["name"] for m in modelos]
        self.assertEqual(nombres, sorted(nombres, key=str.casefold))

    def test_make_insensible_a_mayusculas(self):
        modelos_mayus = get_models_for_make_year("MITSUBISHI", 2020)
        modelos_normal = get_models_for_make_year("Mitsubishi", 2020)
        nombres_mayus = {m["name"] for m in modelos_mayus}
        nombres_normal = {m["name"] for m in modelos_normal}
        self.assertEqual(nombres_mayus, nombres_normal)

    def test_marca_inexistente_no_tumba_el_pipeline(self):
        # No debe lanzar excepción: debe devolver lista vacía.
        modelos = get_models_for_make_year("NOTAREALMAKE12345", 2020)
        self.assertEqual(modelos, [])

    def test_anio_invalido_no_tumba_el_pipeline(self):
        modelos = get_models_for_make_year("Mitsubishi", "no-es-un-año")  # type: ignore[arg-type]
        self.assertEqual(modelos, [])

    def test_make_vacio_no_tumba_el_pipeline(self):
        modelos = get_models_for_make_year("", 2020)
        self.assertEqual(modelos, [])

    def test_anio_sin_registros_devuelve_lista_vacia(self):
        # 1800 es anterior a cualquier VIN moderno: no debe tumbar el pipeline.
        modelos = get_models_for_make_year("Mitsubishi", 1800)
        self.assertEqual(modelos, [])


if __name__ == "__main__":
    unittest.main()
