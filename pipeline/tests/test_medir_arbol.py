"""Pruebas herméticas de pipeline/medir_arbol.py. Nada de red."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medir_arbol import pedir_arbol, resumen  # noqa: E402


class FalsoCliente:
    def __init__(self, datos):
        self.datos, self.rutas = datos, []

    def pedir(self, ruta):
        self.rutas.append(ruta)
        return self.datos


ARBOL = [
    {"categoryId1": 1, "categoryName1": "Brake System"},
    {"categoryId1": 1, "categoryName1": "Brake System", "categoryId2": 10, "categoryName2": "Brake Pad"},
    {"categoryId1": 1, "categoryName1": "Brake System", "categoryId2": 11, "categoryName2": "Brake Disc",
     "categoryId3": 110, "categoryName3": "Vented"},
    {"categoryId1": 2, "categoryName1": "Engine", "categoryId2": 20, "categoryName2": "Oil Filter"},
]


class PruebaResumen(unittest.TestCase):
    def test_cuenta_hojas_distintas_y_grupos(self):
        r = resumen(ARBOL)
        self.assertEqual(r["nodos"], 4)
        self.assertEqual(r["hojas"], 4)          # 1, 10, 110, 20
        self.assertEqual(r["con_categoryId2"], 3)
        self.assertEqual(r["grupos"], {"Brake System": 3, "Engine": 1})

    def test_vacio(self):
        self.assertEqual(resumen([])["hojas"], 0)

    def test_pedir_arbol_es_una_sola_consulta(self):
        c = FalsoCliente({"categories": ARBOL})
        self.assertEqual(pedir_arbol(c, 5), ARBOL)
        self.assertEqual(len(c.rutas), 1)
        self.assertIsNone(pedir_arbol(FalsoCliente(None), 5))


if __name__ == "__main__":
    unittest.main()
