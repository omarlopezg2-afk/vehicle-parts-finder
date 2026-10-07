"""Pruebas herméticas de pipeline/agregar_variantes.py (T-B26).

Nada de red: la elección de variantes se prueba con un catálogo de mentira y una caché en carpeta
temporal. Lo que se fija aquí es el criterio (la gasolina más potente que falta) y que NUNCA se
invente un motor que la caché no tenga.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agregar_variantes import candidatos, identidades, semilla_de  # noqa: E402

# Variantes reales (recortadas) de un Corolla 2016: el catálogo se quedó con las dos primeras.
COROLLA = [
    {"vehicleId": 52438, "typeEngineName": "1.3 Dual-VVTi (NRE180_)", "capacityLt": "1.3",
     "powerPs": "99", "engineCodes": "1NR-FE", "fuelType": "Petrol",
     "constructionIntervalStart": "2013-06", "constructionIntervalEnd": "2018-12"},
    {"vehicleId": 52439, "typeEngineName": "1.4 D-4D (NDE180_)", "capacityLt": "1.4",
     "powerPs": "90", "engineCodes": "1ND-TV", "fuelType": "Diesel",
     "constructionIntervalStart": "2013-06", "constructionIntervalEnd": "2018-12"},
    {"vehicleId": 109621, "typeEngineName": "1.8 VVT-i (ZRE172)", "capacityLt": "1.8",
     "powerPs": "151", "engineCodes": "2ZR-FE", "fuelType": "Petrol",
     "constructionIntervalStart": "2013-06", "constructionIntervalEnd": "2018-12"},
    {"vehicleId": 109622, "typeEngineName": "1.8 (otra)", "capacityLt": "1.8",
     "powerPs": "140", "engineCodes": "2ZR-FE", "fuelType": "Petrol",
     "constructionIntervalStart": "2013-06", "constructionIntervalEnd": "2018-12"},
]

CATALOGO = {
    "pais_filtro": 67,
    "vehiculos": [
        {"etiqueta": "Toyota Corolla 2016 1.3 Dual-VVTi (NRE180_)", "vin": None,
         "vehiculo": {"make": "Toyota", "model": "Corolla", "year": "2016", "motor": "1NR-FE"},
         "autodoc": {"manufacturerId": 111, "modelId": 11560, "vehicleId": 52438},
         "categorias": []},
        {"etiqueta": "Toyota Corolla 2016 1.4 D-4D (NDE180_)", "vin": None,
         "vehiculo": {"make": "Toyota", "model": "Corolla", "year": "2016", "motor": "1ND-TV"},
         "autodoc": {"manufacturerId": 111, "modelId": 11560, "vehicleId": 52439},
         "categorias": []},
    ],
}

BASE = {"pais": 67, "categorias_buscadas": ["brake pad"], "productos_oem": ["brake pad"],
        "equivalentes_por_producto": 1, "detalles_por_categoria": 3, "max_categorias": 10}


class PruebaEleccion(unittest.TestCase):
    def test_elige_la_gasolina_mas_potente_que_falta(self):
        lista = candidatos(CATALOGO, {11560: COROLLA})
        self.assertEqual(len(lista), 1)
        c = lista[0]
        self.assertEqual(c["vehicleId"], 109621, "el 1.8 de 151 PS, no el de 140")
        self.assertEqual(c["anio"], "2016")
        self.assertEqual(c["identidad"]["motor"], "2ZR-FE")
        self.assertEqual(c["identidad"]["combustible"], "Petrol")
        self.assertEqual(c["manufacturerId"], 111)

    def test_no_repite_lo_que_ya_esta_catalogado(self):
        # Si el 1.8 ya estuviera, no hay nada que añadir.
        catalogo = json.loads(json.dumps(CATALOGO))
        catalogo["vehiculos"].append({
            "etiqueta": "Toyota Corolla 2016 1.8 VVT-i (ZRE172)", "vin": None,
            "vehiculo": {"make": "Toyota", "model": "Corolla", "year": "2016"},
            "autodoc": {"manufacturerId": 111, "modelId": 11560, "vehicleId": 109621},
            "categorias": [],
        })
        self.assertEqual(candidatos(catalogo, {11560: COROLLA}), [])

    def test_sin_gasolina_ese_ano_no_se_inventa_nada(self):
        solo_diesel = [v for v in COROLLA if v["fuelType"] == "Diesel"]
        self.assertEqual(candidatos(CATALOGO, {11560: solo_diesel}), [])

    def test_un_modelo_que_no_esta_en_la_cache_no_aporta_nada(self):
        self.assertEqual(candidatos(CATALOGO, {}), [])

    def test_una_variante_sin_vehicle_id_no_entra(self):
        sin_id = [dict(v) for v in COROLLA]
        sin_id[2] = dict(sin_id[2], vehicleId=None)
        self.assertEqual(candidatos(CATALOGO, {11560: sin_id}), [])

    def test_un_criterio_desconocido_se_rechaza_en_vez_de_adivinar(self):
        with self.assertRaises(ValueError):
            candidatos(CATALOGO, {11560: COROLLA}, criterio="todas")


class PruebaSemilla(unittest.TestCase):
    def test_la_semilla_lleva_los_ids_resueltos_y_ninguna_flota(self):
        lista = candidatos(CATALOGO, {11560: COROLLA})
        semilla = semilla_de(lista, BASE, max_consultas=500)
        self.assertNotIn("flota", semilla, "nada se expande por su cuenta")
        self.assertEqual(semilla["max_consultas"], 500)
        self.assertEqual(semilla["categorias_buscadas"], ["brake pad"])
        v = semilla["vehiculos"][0]
        self.assertEqual(v["autodoc"], {"manufacturerId": 111, "modelId": 11560, "vehicleId": 109621})
        self.assertEqual(v["etiqueta"], "Toyota Corolla 2016 1.8 VVT-i (ZRE172)")
        self.assertEqual(v["_make"], "Toyota")
        self.assertEqual(v["_anio"], "2016")
        # La identidad viaja con la entrada: el bloque `vehiculo` se escribe sin gastar (T-B25).
        self.assertEqual(v["_variante_datos"]["combustible"], "Petrol")
        self.assertEqual(v["_variante_datos"]["potencia_ps"], 151.0)
        self.assertTrue(v["criterio"])


class PruebaCache(unittest.TestCase):
    def test_lee_las_identidades_de_la_cache_sin_tocar_la_red(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "country-67-modelo-11560.json").write_text(
                json.dumps({"modelId": 11560, "pais": 67, "modelTypes": COROLLA}), encoding="utf-8")
            (d / "country-67-modelo-11561.json").write_text(
                json.dumps({"modelId": 11561, "pais": 67, "modelTypes": []}), encoding="utf-8")
            (d / "roto.json").write_text("{no es json", encoding="utf-8")
            mapa = identidades(d)
        self.assertEqual(sorted(mapa), [11560, 11561])
        self.assertEqual(len(mapa[11560]), 4)


if __name__ == "__main__":
    unittest.main()
