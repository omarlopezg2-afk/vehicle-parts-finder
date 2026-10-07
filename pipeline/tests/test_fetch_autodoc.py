"""Pruebas herméticas de pipeline/fetch_autodoc.py (T-B13).

Todo corre con un `fetch` falso que devuelve respuestas con la MISMA forma que las reales,
capturadas el 07/10/2026 contra la API. Sin red, sin clave y sin gastar cuota.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fetch_autodoc import (  # noqa: E402
    ClienteAutodoc, PresupuestoAgotado, articulos_de_categoria, categorias_del_vehiculo,
    construir, decodificar_vin, elegir_categorias, equivalentes_de_oem, fusionar, normalizar,
    oem_del_vehiculo, resolver_fabricante, resolver_modelo, resolver_variante,
)

CLAVE_FALSA = "clave-de-prueba-que-no-sirve"      # nunca sale de aquí


# --------------------------------------------------------------------------------------
# respuestas de mentira, con la forma real
# --------------------------------------------------------------------------------------

VIN_INFO = {
    "error_text": "0 - VIN decoded clean. Check Digit (9th position) is correct",
    "make": "MITSUBISHI", "model": "Outlander Sport", "model_year": "2020",
    "displacement_(l)": "2", "engine_brake_(hp)_from": "148",
    "fuel_type_-_primary": "Gasoline", "engine_model": "MIVEC",
}

FABRICANTES = {"countManufactures": 4, "manufacturers": [
    {"manufacturerId": 8232, "manufacturerName": "212"},
    {"manufacturerId": 3650, "manufacturerName": "MITSUBISHI (BJC)"},
    {"manufacturerId": 77, "manufacturerName": "MITSUBISHI"},
    {"manufacturerId": 3837, "manufacturerName": "MITSUBISHI (GAC)"},
]}

MODELOS = {"countModels": 3, "models": [
    {"modelId": 4992, "modelName": "OUTLANDER I (CU_W)",
     "modelYearFrom": "2001-03-01", "modelYearTo": "2008-07-01"},
    {"modelId": 8631, "modelName": "OUTLANDER SPORT (GA_W_)",
     "modelYearFrom": "2009-11-01", "modelYearTo": None},
    {"modelId": 10624, "modelName": "OUTLANDER III (GG_W, GF_W, ZJ, ZL, ZK)",
     "modelYearFrom": "2010-11-01", "modelYearTo": "2022-12-01"},
]}

VARIANTES = {"modelType": "PC", "countModelTypes": 3, "modelTypes": [
    # diesel 1.8: NO debe elegirse cuando el VIN dice gasolina
    {"vehicleId": 376, "typeEngineName": "1.8 DI-D (GA6W)", "fuelType": "Diesel",
     "capacityLt": "1.8000", "powerPs": "116.0000", "powerKw": "85.0000",
     "constructionIntervalStart": "2010-06-01", "constructionIntervalEnd": None, "engId": 24446},
    # gasolina 1.8: cilindrada no coincide
    {"vehicleId": 378, "typeEngineName": "1.8 (GA3W)", "fuelType": "Petrol",
     "capacityLt": "1.8000", "powerPs": "139.0000", "powerKw": "102.0000",
     "constructionIntervalStart": "2010-02-01", "constructionIntervalEnd": None, "engId": 24447},
    # gasolina 2.0 con 148 HP: ESTA es la del VIN (y viene repetida a propósito, como en la API)
    {"vehicleId": 126680, "typeEngineName": "2.0 i 4WD", "fuelType": "Petrol",
     "capacityLt": "2.0000", "powerPs": "148.0000", "powerKw": "109.0000",
     "constructionIntervalStart": "2010-06-01", "constructionIntervalEnd": None, "engId": 24448},
    {"vehicleId": 126680, "typeEngineName": "2.0 i 4WD", "fuelType": "Petrol",
     "capacityLt": "2.0000", "powerPs": "148.0000", "powerKw": "109.0000",
     "constructionIntervalStart": "2010-06-01", "constructionIntervalEnd": None, "engId": 24448},
]}

CATEGORIAS = {"categories": [
    {"categoryName1": "Braking System", "categoryId1": 100022,
     "categoryName2": "Disc Brake", "categoryId2": 100626},
    {"categoryName1": "Braking System", "categoryId1": 100022,
     "categoryName2": "Brake Pad", "categoryId2": 100027},
    {"categoryName1": "Filters", "categoryId1": 100005,
     "categoryName2": "Oil Filter", "categoryId2": 100031},
    {"categoryName1": "Filters", "categoryId1": 100005,
     "categoryName2": "Air Filter", "categoryId2": 100032},
    {"categoryName1": "Windows", "categoryId1": 100060,
     "categoryName2": "Wiper Blade", "categoryId2": 100099},
    {"categoryName1": "Accessories", "categoryId1": 100316, "categoryName2": "Wiper Blade", "categoryId2": 100100},
]}

ARTICULOS = {"vehicleId": 126680, "categoryId": 100027, "countArticles": 3, "articles": [
    {"articleId": 1811887, "articleNo": "ADBP450211", "supplierName": "BLUE PRINT",
     "articleProductName": "Brake Caliper", "s3image": "https://fsn1.your-objectstorage.com/x.webp",
     "articleMediaType": "image/webp"},
    {"articleId": 1811888, "articleNo": "0 986 494 123", "supplierName": "BOSCH",
     "articleProductName": "Brake Pad Set", "s3image": None, "articleMediaType": None},
    # sin marca o sin número: no debe entrar
    {"articleId": 1811889, "articleNo": "", "supplierName": "NADIE", "articleProductName": "X"},
    {"articleId": 1811890, "articleNo": "ABC-1", "supplierName": "", "articleProductName": "Y"},
]}


# Respuestas reales de T-B16 (07/10/2026, Outlander Sport del usuario)
OEM_DEL_VEHICULO = [
    {"articleOemNo": "MN102628", "articleProductName": "Brake Pad Set, disc brake"},
    {"articleOemNo": "MR527674", "articleProductName": "Brake Pad Set, disc brake"},
    {"articleOemNo": "MR527674", "articleProductName": "Brake Pad Set, disc brake"},   # repetido a propósito
    {"articleOemNo": "", "articleProductName": "sin número: no debe entrar"},
    {"articleOemNo": "MR527673", "articleProductName": "Accessory Kit, disc brake pad"},
]

EQUIVALENTES = [
    {"articleId": 1811887, "articleSearchNo": "04152-YZZA1", "articleNo": "20-50517-SX",
     "oemNo": [{"oemBrand": "TOYOTA", "oemDisplayNo": "04152-0V010"},
               {"oemBrand": "DAIHATSU", "oemDisplayNo": "04152-31090"}]},
    {"articleId": 1811888, "articleNo": "", "oemNo": []},          # sin número: no debe entrar
]


def fetch_falso(mapa, *_, **__):
    def _f(url, cabeceras, timeout=45):
        for patron, respuesta in mapa:
            if patron in url:
                return 200, json.dumps(respuesta)
        return 404, json.dumps({"message": f"Endpoint '{url}' does not exist"})
    return _f


MAPA_COMPLETO = [
    ("/api/articles-oem/search-all-equal-oem-no", EQUIVALENTES),
    ("/api/articles-oem/", OEM_DEL_VEHICULO),
    ("/api/vin/decoder-v5/", {"vin-data-1": {}, "vin-data-2": {"content": json.dumps(VIN_INFO)},
                              "vin-data-3": {}}),
    ("/api/manufacturers/list/", FABRICANTES),
    ("/api/models/list/", MODELOS),
    ("/api/types/type-id/1/list-vehicles-types/", VARIANTES),
    ("/api/category/", CATEGORIAS),
    ("/api/articles/list/", ARTICULOS),
]

SEMILLA = {
    "pais": 67,
    "max_consultas": 30,
    "max_categorias": 4,
    "vehiculos": [{"etiqueta": "Mitsubishi Outlander Sport 2020 (2.0 gasolina)",
                   "vin": "JA4AP4AU3LU023739",
                   "autodoc": {"manufacturerId": None, "modelId": None, "vehicleId": None}}],
    "categorias_buscadas": ["brake pad", "oil filter", "air filter", "wiper blade", "spark plug"],
    "productos_oem": ["brake pad", "oil filter"],
    "equivalentes_por_producto": 1,
}


class PruebasTexto(unittest.TestCase):
    def test_normalizar_quita_acentos_y_parentesis(self):
        self.assertEqual(normalizar("OUTLANDER SPORT (GA_W_)"), "outlander sport")
        self.assertEqual(normalizar("Filtro de Aire"), "filtro de aire")
        self.assertEqual(normalizar("Disc Brake"), "disc brake")
        self.assertEqual(normalizar(""), "")


class PruebasResolucion(unittest.TestCase):
    def setUp(self):
        self.c = ClienteAutodoc(CLAVE_FALSA, fetch=fetch_falso(MAPA_COMPLETO), pausa=0)

    def test_decodifica_el_vin_del_bloque_2(self):
        d = decodificar_vin(self.c, "JA4AP4AU3LU023739")
        self.assertIsNotNone(d, "el VIN se tiene que poder decodificar")
        assert d is not None
        self.assertTrue(d["valido"])
        self.assertEqual(d["make"], "MITSUBISHI")
        self.assertEqual(d["model"], "Outlander Sport")
        self.assertEqual(d["year"], "2020")
        self.assertEqual(d["cilindrada_l"], 2.0)
        self.assertEqual(d["potencia_hp"], 148.0)
        self.assertEqual(d["combustible"], "Gasoline")

    def test_fabricante_prefiere_el_nombre_exacto(self):
        f = resolver_fabricante(self.c, "Mitsubishi")
        self.assertIsNotNone(f)
        assert f is not None
        self.assertEqual(f["manufacturerId"], 77)          # no MITSUBISHI (BJC) ni (GAC)

    def test_modelo_por_nombre_y_anio(self):
        m = resolver_modelo(self.c, 77, "Outlander Sport", "2020", 67)
        self.assertIsNotNone(m)
        assert m is not None
        self.assertEqual(m["modelId"], 8631)
        # un año fuera de rango no debe colar
        self.assertIsNone(resolver_modelo(self.c, 77, "Outlander I", "2020", 67))

    def test_variante_por_motor_y_descarta_diesel(self):
        v = resolver_variante(self.c, 8631, 67, cilindrada_l=2.0, potencia_hp=148,
                              anio="2020", combustible="Gasoline")
        self.assertIsNotNone(v)
        assert v is not None
        self.assertEqual(v["vehicleId"], 126680)
        self.assertEqual(v["typeEngineName"], "2.0 i 4WD")
        # con gasolina no puede devolver el diesel
        self.assertNotIn("DI-D", v["typeEngineName"])

    def test_no_confunde_generaciones_por_texto(self):
        # "OUTLANDER I" (2001-2008) no debe ganarle a nada en 2020: sin coincidencia segura,
        # se devuelve None y quien llama decide (mejor nada que una pieza de otra generación).
        m = resolver_modelo(self.c, 77, "Outlander I", "2020", 67)
        self.assertIsNone(m, "no puede colar la generación III por parecerse el texto")

    def test_variante_no_inventa_si_no_encaja(self):
        v = resolver_variante(self.c, 8631, 67, cilindrada_l=5.0, potencia_hp=500,
                              anio="2020", combustible="Gasoline")
        self.assertIsNone(v)


class PruebasCategoriasYArticulos(unittest.TestCase):
    def setUp(self):
        self.c = ClienteAutodoc(CLAVE_FALSA, fetch=fetch_falso(MAPA_COMPLETO), pausa=0)

    def test_arbol_se_queda_con_el_nivel_que_acepta_articulos(self):
        arbol = categorias_del_vehiculo(self.c, 126680)
        self.assertEqual(len(arbol), 6)                    # todas traen categoryId2 en el árbol de mentira
        self.assertTrue(all(n["categoryId"] for n in arbol))

    def test_elegir_categorias_respeta_orden_y_tope(self):
        arbol = categorias_del_vehiculo(self.c, 126680)
        elegidas = elegir_categorias(arbol, ["brake pad", "oil filter", "no existe", "air filter"], tope=3)
        self.assertEqual([c["nombre"] for c in elegidas], ["Brake Pad", "Oil Filter", "Air Filter"])

    def test_entre_varias_coincidencias_gana_la_mas_profunda(self):
        arbol = [
            {"categoryId": 1, "nombre": "Body Parts/Wing/Bumper", "ruta": "Body / Attachment / Body Parts/Wing/Bumper"},
            {"categoryId": 2, "nombre": "Track Control Arm", "ruta": "Suspension / Arms / Track Control Arm"},
        ]
        elegidas = elegir_categorias(arbol, ["control arm"], tope=1)
        self.assertEqual(len(elegidas), 1)
        self.assertEqual(elegidas[0]["categoryId"], 2, "debe elegir la rama específica, no la genérica")
        self.assertEqual(elegidas[0]["buscado"], "control arm")

    def test_articulos_exige_numero_y_marca_y_trae_la_foto(self):
        arts = articulos_de_categoria(self.c, 126680, 100027)
        self.assertEqual(len(arts), 2)                     # las dos incompletas se caen
        self.assertEqual(arts[0]["numero"], "ADBP450211")
        self.assertEqual(arts[0]["marca"], "BLUE PRINT")
        self.assertEqual(arts[0]["pieza"], "Brake Caliper")
        self.assertTrue(arts[0]["foto"].startswith("https://"))
        self.assertIsNone(arts[1]["foto"])


class PruebasPresupuesto(unittest.TestCase):
    def test_el_cliente_se_detiene_en_el_tope(self):
        c = ClienteAutodoc(CLAVE_FALSA, max_consultas=2, fetch=fetch_falso(MAPA_COMPLETO), pausa=0)
        c.pedir("/api/languages/list")
        c.pedir("/api/countries/list")
        with self.assertRaises(PresupuestoAgotado):
            c.pedir("/api/countries/list")
        self.assertEqual(c.consultas, 2)                  # la tercera no se cuenta ni se gasta

    def test_si_se_agota_el_presupuesto_el_resultado_se_marca_incompleto(self):
        semilla = json.loads(json.dumps(SEMILLA))
        c = ClienteAutodoc(CLAVE_FALSA, max_consultas=5, fetch=fetch_falso(MAPA_COMPLETO), pausa=0)
        r = construir(semilla, c)
        self.assertTrue(r["incompleto"])
        self.assertTrue(r["vehiculos"][0]["avisos"])


class PruebasNumeroOriginal(unittest.TestCase):
    """T-B16: el número original del fabricante (el equivalente al EPC del concesionario)."""

    def setUp(self):
        self.c = ClienteAutodoc(CLAVE_FALSA, fetch=fetch_falso(MAPA_COMPLETO), pausa=0)

    def test_oem_del_vehiculo_quita_repetidos_y_los_que_no_tienen_numero(self):
        oems = oem_del_vehiculo(self.c, 126680, "brake pad")
        assert isinstance(oems, list)
        numeros = [o["numero"] for o in oems]
        assert numeros == ["MN102628", "MR527674", "MR527673"], numeros
        assert all(o["pieza"] for o in oems)

    def test_equivalentes_de_oem_trae_las_otras_marcas(self):
        eq = equivalentes_de_oem(self.c, "04152YZZA1")
        assert len(eq) == 1, "el artículo sin número no debe entrar"
        assert eq[0]["numero"] == "20-50517-SX"
        assert "04152-0V010" in eq[0]["oemEquivalentes"]

    def test_solo_oem_no_pide_categorias(self):
        pedidas = []
        base = fetch_falso(MAPA_COMPLETO)

        def espia(url, cabeceras, timeout=45):
            pedidas.append(url)
            return base(url, cabeceras, timeout)

        c = ClienteAutodoc(CLAVE_FALSA, fetch=espia, pausa=0)
        r = construir(json.loads(json.dumps(SEMILLA)), c, solo_oem=True)

        assert not any("/api/categories" in u or "/api/category/" in u for u in pedidas), pedidas
        assert not any("/api/articles/list/" in u for u in pedidas), pedidas
        assert any("/api/articles-oem/selecting-oem-parts" in u for u in pedidas)
        assert r["vehiculos"][0]["oem"], "el bloque de originales debe venir"


class PruebasFusion(unittest.TestCase):
    """Un recorrido parcial (--solo-oem) no puede borrar las categorías ya guardadas.

    Es la lección del 07/10/2026 aplicada al catálogo: aquel día un build parcial sobreescribió
    parts.json y se perdió el build real.
    """

    def test_lo_nuevo_manda_y_lo_que_no_vino_se_conserva(self):
        previo = {"generado_en": "2026-10-07T01:00:00Z", "consultas": 27, "vehiculos": [
            {"etiqueta": "Mitsubishi Outlander Sport 2020 (2.0 gasolina)", "vin": "JA4AP4AU3LU023739",
             "vehiculo": {"make": "MITSUBISHI", "model": "Outlander Sport", "year": "2020"},
             "autodoc": {"vehicleId": 126680}, "avisos": [],
             "categorias": [{"nombre": "Disc Brake", "articulos": [{"numero": "D2N097"}]}]},
            {"etiqueta": "Toyota Corolla 2019", "vin": "2T1BURHE6KC123456", "categorias": [{"nombre": "X"}]},
        ]}
        nuevo = {"generado_en": "2026-10-07T02:00:00Z", "consultas": 7, "vehiculos": [
            {"etiqueta": "Mitsubishi Outlander Sport 2020 (2.0 gasolina)", "vin": "JA4AP4AU3LU023739",
             "vehiculo": {}, "autodoc": {}, "avisos": [],
             "oem": [{"buscado": "brake pad", "numeros": [{"numero": "MN102628"}]}],
             "categorias": []},
        ]}

        r = fusionar(previo, nuevo)
        v = r["vehiculos"][0]
        assert v["categorias"], "las categorías del recorrido anterior NO se pueden perder"
        assert v["categorias"][0]["articulos"][0]["numero"] == "D2N097"
        assert v["oem"][0]["numeros"][0]["numero"] == "MN102628", "lo nuevo manda"
        assert v["vehiculo"]["make"] == "MITSUBISHI", "los datos del vehículo se conservan"
        assert any("Toyota Corolla" in (x.get("etiqueta") or "") for x in r["vehiculos"]), \
            "un vehículo que no se recorrió esta vez se queda como estaba"
        assert r["consultas"] == 34, "las consultas se acumulan, no se reinician"


class PruebasExtremoAExtremo(unittest.TestCase):
    def test_recorrido_completo_produce_piezas_con_numero(self):
        c = ClienteAutodoc(CLAVE_FALSA, fetch=fetch_falso(MAPA_COMPLETO), pausa=0)
        r = construir(json.loads(json.dumps(SEMILLA)), c)

        self.assertFalse(r["incompleto"])
        v = r["vehiculos"][0]
        self.assertEqual(v["avisos"], [], "el recorrido completo no debe dejar avisos")
        self.assertEqual(v["autodoc"]["vehicleId"], 126680)
        self.assertEqual(v["nombres"]["variante"], "2.0 i 4WD")
        self.assertEqual(v["vehiculo"]["make"], "MITSUBISHI")

        categorias = [cat["nombre"] for cat in v["categorias"]]
        # "spark plug" no existe en el árbol; el tope de 4 de la semilla deja fuera lo demás
        self.assertEqual(categorias, ["Brake Pad", "Oil Filter", "Air Filter", "Wiper Blade"])
        numeros = [a["numero"] for cat in v["categorias"] for a in cat["articulos"]]
        self.assertIn("ADBP450211", numeros)
        self.assertTrue(r["consultas"] > 0)

        # T-B16: si el presupuesto se agota, lo que debe estar a salvo es el número ORIGINAL.
        self.assertTrue(v["oem"], "el bloque de números originales tiene que venir")
        self.assertEqual(v["oem"][0]["numeros"][0]["numero"], "MN102628")

    def test_los_originales_se_piden_antes_que_las_categorias(self):
        pedidas = []
        base = fetch_falso(MAPA_COMPLETO)

        def espia(url, cabeceras, timeout=45):
            pedidas.append(url)
            return base(url, cabeceras, timeout)

        c = ClienteAutodoc(CLAVE_FALSA, fetch=espia, pausa=0)
        construir(json.loads(json.dumps(SEMILLA)), c)
        i_oem = next(i for i, u in enumerate(pedidas) if "/api/articles-oem/" in u)
        i_cat = next(i for i, u in enumerate(pedidas) if "/api/category/" in u)
        self.assertLess(i_oem, i_cat, "los originales van primero: es lo que no se puede perder")

    def test_la_clave_nunca_aparece_en_el_resultado(self):
        c = ClienteAutodoc(CLAVE_FALSA, fetch=fetch_falso(MAPA_COMPLETO), pausa=0)
        r = construir(json.loads(json.dumps(SEMILLA)), c)
        self.assertNotIn(CLAVE_FALSA, json.dumps(r))


if __name__ == "__main__":
    unittest.main()
