"""Tests de pipeline/normalize.py (T-B2).

Usa unittest (stdlib) a propósito: así corre con `python3 -m unittest` sin
necesidad de instalar pytest ni nada más, out-of-the-box.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from normalize import normalize_part_number


class TestNormalizePartNumber(unittest.TestCase):
    def test_ejemplo_del_contrato(self):
        # Ejemplo literal de CONTRACTS.md.
        self.assertEqual(normalize_part_number("04152-YZZA1"), "04152YZZA1")

    def test_guiones(self):
        self.assertEqual(normalize_part_number("1230-A114"), "1230A114")
        self.assertEqual(normalize_part_number("MB-958-712"), "MB958712")

    def test_puntos(self):
        self.assertEqual(normalize_part_number("90.915.YZZD1"), "90915YZZD1")

    def test_espacios(self):
        self.assertEqual(normalize_part_number("04152 YZZ A1"), "04152YZZA1")
        self.assertEqual(normalize_part_number("  04152YZZA1  "), "04152YZZA1")

    def test_mezcla_guiones_puntos_espacios(self):
        self.assertEqual(normalize_part_number(" 04152-YZZ.A1 "), "04152YZZA1")
        self.assertEqual(normalize_part_number("MN-10.28 05"), "MN102805")

    def test_barras(self):
        self.assertEqual(normalize_part_number("MZ690/125"), "MZ690125")
        self.assertEqual(normalize_part_number("AB\\123-45"), "AB12345")

    def test_mayusculas(self):
        self.assertEqual(normalize_part_number("04152-yzza1"), "04152YZZA1")
        self.assertEqual(normalize_part_number("mb958712"), "MB958712")

    def test_ya_normalizado_no_cambia(self):
        self.assertEqual(normalize_part_number("1230A114"), "1230A114")

    def test_cadena_vacia(self):
        self.assertEqual(normalize_part_number(""), "")

    def test_none_devuelve_vacio(self):
        self.assertEqual(normalize_part_number(None), "")

    def test_tipo_invalido_lanza_typeerror(self):
        with self.assertRaises(TypeError):
            normalize_part_number(12345)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
