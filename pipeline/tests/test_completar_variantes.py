"""Pruebas herméticas de pipeline/completar_variantes.py (T-B25).

Todo corre con un `fetch` falso y una caché en carpeta temporal: sin red, sin clave y sin gastar
una sola consulta. La forma de la respuesta es la real (capturada el 07/10/2026 contra la API).
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from completar_variantes import (  # noqa: E402
    completar, datos_de_variante, mapa_de_variantes, pares_pendientes, variantes_del_modelo,
)
from fetch_autodoc import ClienteAutodoc, PresupuestoAgotado  # noqa: E402

CLAVE_FALSA = "clave-de-prueba-que-no-sirve"

# Respuesta real de /api/types/type-id/1/list-vehicles-types/11560 (recortada).
MODEL_TYPES = [
    {"vehicleId": 52438, "engId": 11, "typeEngineName": "1.3 Dual-VVTi (NRE180_)",
     "capacityLt": "1.3", "powerPs": "99", "engineCodes": "1NR-FE", "fuelType": "Petrol",
     "constructionIntervalStart": "2013-06", "constructionIntervalEnd": "2018-12"},
    {"vehicleId": 52439, "engId": 12, "typeEngineName": "1.8 (ZRE172_)",
     "capacityLt": "1.8", "powerPs": "140", "engineCodes": "2ZR-FE", "fuelType": "Petrol",
     "constructionIntervalStart": "2013-06", "constructionIntervalEnd": "2019-01"},
    {"vehicleId": 60001, "engId": 13, "typeEngineName": "1.4 D-4D",
     "capacityLt": "1.4", "powerPs": "90", "engineCodes": "1ND-TV", "fuelType": "Diesel",
     "constructionIntervalStart": "2013-06", "constructionIntervalEnd": ""},
]

SEMILLA_FLOTA = [
    {"make": "Toyota", "model": "Corolla", "years": [2016]},
]


def _entrada(etiqueta, vehicle_id, vehiculo=None):
    e = {"etiqueta": etiqueta, "vin": None, "avisos": [], "categorias": [],
         "autodoc": {"manufacturerId": 111, "modelId": 11560, "vehicleId": vehicle_id}}
    if vehiculo is not None:
        e["vehiculo"] = vehiculo
    return e


class PruebaDatosDeVariante(unittest.TestCase):
    def test_toma_identidad_y_tira_lo_vacio(self):
        self.assertEqual(datos_de_variante(MODEL_TYPES[0]), {
            "combustible": "Petrol", "cilindrada_l": 1.3, "potencia_ps": 99.0,
            "motor": "1NR-FE", "variante": "1.3 Dual-VVTi (NRE180_)",
        })
        # Una variante sin potencia ni código de motor no inventa campos.
        self.assertEqual(datos_de_variante({"vehicleId": 1, "fuelType": "Diesel"}),
                         {"combustible": "Diesel"})
        self.assertEqual(datos_de_variante(None), {})

    def test_la_potencia_se_guarda_en_PS_no_en_HP(self):
        # powerPs es caballo métrico: rotularlo "HP" sería un número mal dicho.
        self.assertIn("potencia_ps", datos_de_variante(MODEL_TYPES[1]))
        self.assertNotIn("potencia_hp", datos_de_variante(MODEL_TYPES[1]))


class PruebaMapaDeVariantes(unittest.TestCase):
    def test_indexa_por_vehicle_id(self):
        mapa, ambiguos, choques = mapa_de_variantes(MODEL_TYPES)
        self.assertEqual(sorted(mapa), ["52438", "52439", "60001"])
        self.assertEqual(mapa["52439"]["combustible"], "Petrol")
        self.assertEqual(ambiguos, [])
        self.assertEqual(choques, {})

    def test_vehicle_id_con_varios_motores_conserva_el_primero_y_lo_reporta(self):
        otro = dict(MODEL_TYPES[0], engId=99, engineCodes="OTRO")     # mismo combustible
        mapa, ambiguos, choques = mapa_de_variantes([MODEL_TYPES[0], otro])
        self.assertEqual(mapa["52438"]["motor"], "1NR-FE")            # gana la primera
        self.assertEqual(ambiguos, ["52438"])
        self.assertEqual(choques, {})

    def test_combustible_contradictorio_no_se_rellena_y_es_alarma(self):
        # El mismo vehículo como gasolina y como diésel: no se elige a dedo, se deja sin dato.
        diesel = dict(MODEL_TYPES[0], engId=99, fuelType="Diesel")
        mapa, _, choques = mapa_de_variantes([MODEL_TYPES[0], diesel])
        self.assertNotIn("52438", mapa)
        self.assertEqual(choques, {"52438": ["Diesel", "Petrol"]})


class PruebaCompletar(unittest.TestCase):
    def setUp(self):
        self.mapa, _, _ = mapa_de_variantes(MODEL_TYPES)

    def test_rellena_la_entrada_de_flota_y_le_pone_marca_modelo_anio(self):
        entradas = [_entrada("Toyota Corolla 2016 1.3 Dual-VVTi (NRE180_)", 52438)]
        informe = completar(entradas, self.mapa, SEMILLA_FLOTA)
        vh = entradas[0]["vehiculo"]
        self.assertEqual(informe["rellenadas"], 1)
        self.assertEqual(vh["make"], "Toyota")
        self.assertEqual(vh["year"], "2016")
        self.assertEqual(vh["combustible"], "Petrol")
        self.assertEqual(vh["cilindrada_l"], 1.3)
        self.assertEqual(vh["motor"], "1NR-FE")
        self.assertEqual(vh["origen"], "flota")

    def test_no_sobreescribe_lo_que_ya_estaba(self):
        original = {"make": "MITSUBISHI", "model": "Outlander Sport", "year": "2020",
                    "cilindrada_l": 2.4, "combustible": "Petrol", "origen": "vin"}
        entradas = [_entrada("Mitsubishi Outlander Sport 2020", 52438, vehiculo=dict(original))]
        informe = completar(entradas, self.mapa, SEMILLA_FLOTA)
        self.assertEqual(informe["ya_completas"], 1)
        self.assertEqual(entradas[0]["vehiculo"], original)   # intacto

    def test_vehicle_id_desconocido_no_se_rellena_y_se_reporta(self):
        entradas = [_entrada("Toyota Corolla 2016 raro", 99999)]
        informe = completar(entradas, self.mapa, SEMILLA_FLOTA)
        self.assertEqual(informe["rellenadas"], 0)
        self.assertEqual(informe["sin_dato"], ["Toyota Corolla 2016 raro"])
        self.assertFalse((entradas[0].get("vehiculo") or {}).get("combustible"))

    def test_sin_vehicle_id_se_reporta(self):
        entradas = [{"etiqueta": "algo", "autodoc": {}}]
        informe = completar(entradas, self.mapa, SEMILLA_FLOTA)
        self.assertEqual(informe["sin_id"], ["algo"])

    def test_el_bloque_queda_ordenado_para_leerse(self):
        entradas = [_entrada("Toyota Corolla 2016 1.3 Dual-VVTi (NRE180_)", 52438)]
        completar(entradas, self.mapa, SEMILLA_FLOTA)
        self.assertEqual(list(entradas[0]["vehiculo"])[:4], ["make", "model", "year", "cilindrada_l"])


class PruebaParesPendientes(unittest.TestCase):
    def test_cuenta_parejas_distintas_y_salta_las_que_ya_tienen_combustible(self):
        entradas = [
            _entrada("a", 1),
            _entrada("b", 2),                                     # misma pareja (111, 11560)
            _entrada("c", 3, vehiculo={"make": "X", "combustible": "Diesel"}),
        ]
        entradas.append({"etiqueta": "d", "autodoc": {"manufacturerId": 77, "modelId": 8631, "vehicleId": 4}})
        self.assertEqual(pares_pendientes(entradas), [(77, 8631), (111, 11560)])


class PruebaCacheDeVariantes(unittest.TestCase):
    def _cliente(self):
        llamadas = []

        def fetch_falso(url, cabeceras, timeout=45):
            llamadas.append(url)
            return 200, json.dumps({"modelTypes": MODEL_TYPES})

        return ClienteAutodoc(CLAVE_FALSA, max_consultas=5, fetch=fetch_falso, pausa=0), llamadas

    def test_la_segunda_llamada_no_gasta_ni_una_consulta(self):
        cliente, llamadas = self._cliente()
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            primera = variantes_del_modelo(cliente, 11560, 67, cache=cache)
            segunda = variantes_del_modelo(cliente, 11560, 67, cache=cache)
        self.assertIsNotNone(primera)
        self.assertEqual(len(primera), 3)
        self.assertEqual(primera, segunda)
        self.assertEqual(cliente.consultas, 1)          # la segunda salió de disco
        self.assertEqual(len(llamadas), 1)

    def test_sin_red_no_toca_la_api_y_devuelve_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(variantes_del_modelo(None, 11560, 67, cache=Path(tmp)))

    def test_el_tope_de_consultas_para_la_corrida(self):
        cliente, _ = self._cliente()
        cliente.max_consultas = 0                           # `is not None`: 0 es un tope, no un hueco
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(PresupuestoAgotado):
                variantes_del_modelo(cliente, 11560, 67, cache=Path(tmp))

    def test_la_cache_de_una_respuesta_vacia_tambien_vale(self):
        vacio = {"modelTypes": []}
        cliente = ClienteAutodoc(CLAVE_FALSA, max_consultas=5,
                                 fetch=lambda *a, **k: (200, json.dumps(vacio)), pausa=0)
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            self.assertEqual(variantes_del_modelo(cliente, 1, 67, cache=cache), [])
            self.assertEqual(variantes_del_modelo(cliente, 1, 67, cache=cache), [])
        self.assertEqual(cliente.consultas, 1)


if __name__ == "__main__":
    unittest.main()
