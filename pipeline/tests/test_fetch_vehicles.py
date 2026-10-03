"""Tests de pipeline/fetch_vehicles.py (T-A1).

Usa unittest (stdlib) para no depender de pytest. Hace llamadas HTTP reales a
vPIC (API pública, sin llave) con VINs conocidos. Si no hay red disponible,
estos tests fallarán con un error de conexión — es esperado y documentado en
el PR (no hay modo mock para este cliente porque vPIC no requiere llave).

Ejecutar:
    python3 -m unittest pipeline/tests/test_fetch_vehicles.py -v
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetch_vehicles import fetch_vehicle, fetch_vehicles

# VIN real de un Mitsubishi Outlander Sport 2020 (ES FWD, motor 2.0L 4cil CVT).
#
# NOTA / supuesto documentado: no se dispone del VIN real del vehículo de Omar.
# Este es un VIN real de producción de un Outlander Sport 2020 (prefijo
# JA4AP3AU, posición 10 = 'L' = 2020), obtenido de bases públicas de VINs reales
# en circulación (vinassessment.com / clearvin.com), usado aquí como
# representante válido de "Outlander Sport 2020" tal como pide T-A1. Si Omar
# provee su VIN real, basta con reemplazar esta constante.
VIN_OUTLANDER_SPORT_2020 = "JA4AP3AU0LU000302"

# VIN real conocido, ampliamente usado en ejemplos de la industria/documentación
# de decodificadores VIN (2003 Honda Accord EX-V6 Coupe).
VIN_HONDA_ACCORD_2003 = "1HGCM82633A004352"

# VIN real de un Ford F-150 2013 (usado en ejemplos públicos de vPIC/Apify).
VIN_FORD_F150_2013 = "1FTFW1ET5DFC10312"

# VIN deliberadamente inválido (caracteres no permitidos I y dígito check mal).
VIN_INVALIDO = "INVALIDVIN1234567"


class TestFetchVehicle(unittest.TestCase):
    def test_outlander_sport_2020_de_omar(self):
        resultado = fetch_vehicle(VIN_OUTLANDER_SPORT_2020)
        self.assertIsNone(resultado["error"], resultado)
        self.assertEqual(resultado["make"], "Mitsubishi")
        self.assertEqual(resultado["model"], "Outlander Sport")
        self.assertEqual(resultado["year"], 2020)
        self.assertTrue(resultado["id"])
        self.assertIsNotNone(resultado["engine"])
        # Esquema exacto de CONTRACTS.md: estas claves deben existir.
        for clave in ("id", "make", "model", "year", "trim", "engine"):
            self.assertIn(clave, resultado)

    def test_honda_accord_2003(self):
        resultado = fetch_vehicle(VIN_HONDA_ACCORD_2003)
        self.assertIsNone(resultado["error"], resultado)
        self.assertEqual(resultado["make"], "Honda")
        self.assertEqual(resultado["model"], "Accord")
        self.assertEqual(resultado["year"], 2003)
        self.assertEqual(resultado["trim"], "EX-V6")

    def test_ford_f150_2013(self):
        resultado = fetch_vehicle(VIN_FORD_F150_2013)
        self.assertIsNone(resultado["error"], resultado)
        self.assertEqual(resultado["make"], "Ford")
        self.assertEqual(resultado["model"], "F-150")
        self.assertEqual(resultado["year"], 2013)

    def test_vin_invalido_no_tumba_el_pipeline(self):
        # No debe lanzar excepción: debe devolver un dict con error legible.
        resultado = fetch_vehicle(VIN_INVALIDO)
        self.assertIsNotNone(resultado["error"])
        self.assertIsNone(resultado["make"])
        self.assertIsNone(resultado["model"])
        self.assertIsNone(resultado["year"])

    def test_vin_vacio_no_tumba_el_pipeline(self):
        resultado = fetch_vehicle("")
        self.assertIsNotNone(resultado["error"])

    def test_vin_con_longitud_incorrecta_no_tumba_el_pipeline(self):
        resultado = fetch_vehicle("CORTO123")
        self.assertIsNotNone(resultado["error"])

    def test_fetch_vehicles_mezcla_validos_e_invalidos(self):
        # Un VIN inválido en el lote no debe impedir resolver los demás.
        resultados = fetch_vehicles([VIN_OUTLANDER_SPORT_2020, VIN_INVALIDO])
        self.assertEqual(len(resultados), 2)
        self.assertIsNone(resultados[0]["error"])
        self.assertIsNotNone(resultados[1]["error"])


if __name__ == "__main__":
    unittest.main()
