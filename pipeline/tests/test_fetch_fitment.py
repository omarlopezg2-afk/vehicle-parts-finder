#!/usr/bin/env python3
"""Pruebas de pipeline/fetch_fitment.py (T-B8).

**No salen a la red**: la función que hace la llamada real (`_buscar`) se sustituye por una
doble. Lo que se fija aquí es lo que decide el comportamiento del catálogo: que solo entren
los anuncios EXACT, que se ordenen por precio, que se recorte a los más baratos y que un
fallo de la API no tumbe el build.
"""

import unittest
from unittest import mock

# Igual que el resto de pruebas del pipeline: se corren desde el directorio `pipeline/`,
# así que el módulo se importa directo.
import fetch_fitment as ff

VEHICULO = {"id": "vin-JA4AP4AU3LU023739", "make": "Mitsubishi", "model": "Outlander Sport", "year": 2020}
CATEGORIA = {"slug": "filtro-aire", "nombre": "Filtro de aire", "category_id": "33659"}


def _item(titulo, precio, match="EXACT", foto="https://i.ebayimg.com/x.jpg"):
    """Un anuncio de prueba. Con match="SIN_CAMPO" se omite el campo por completo,
    que es un caso real: hay anuncios que no lo traen."""
    item = {"itemId": "v1|1|0", "title": titulo, "itemWebUrl": "https://www.ebay.com/itm/1",
            "price": {"value": precio, "currency": "USD"}, "condition": "New",
            "image": {"imageUrl": foto}}
    if match != "SIN_CAMPO":
        item["compatibilityMatch"] = match
    return item


class TestAOferta(unittest.TestCase):
    def test_mapea_los_campos_que_exportamos(self):
        o = ff._a_oferta(_item("Filtro", "12.99"))
        self.assertEqual(o["precio"], 12.99)
        self.assertEqual(o["moneda"], "USD")
        self.assertEqual(o["compatibilidad"], "EXACT")
        self.assertEqual(o["foto"], "https://i.ebayimg.com/x.jpg")
        self.assertEqual(o["url"], "https://www.ebay.com/itm/1")

    def test_precio_ausente_o_basura_no_rompe(self):
        for raro in (None, "", "no es un numero", {}):
            item = _item("Filtro", "1")
            item["price"] = {"value": raro, "currency": "USD"}
            with self.subTest(valor=raro):
                self.assertIsNone(ff._a_oferta(item)["precio"])

    def test_foto_inesperada_queda_en_none(self):
        item = _item("Filtro", "1")
        item["image"] = "https://i.ebayimg.com/no-es-objeto.jpg"
        self.assertIsNone(ff._a_oferta(item)["foto"])


class TestBuscarCategoria(unittest.TestCase):
    def _con_respuesta(self, items, total=99):
        respuesta = {"total": total, "itemSummaries": items}
        with mock.patch.object(ff, "_buscar", return_value=respuesta):
            return ff.buscar_categoria("token", VEHICULO, CATEGORIA, limite_por_categoria=3)

    def test_solo_entran_los_EXACT(self):
        r = self._con_respuesta([
            _item("exacta", "10"), _item("posible", "5", match="POSSIBLE"),
            _item("sin campo", "1", match="SIN_CAMPO"), _item("otra exacta", "20")])
        self.assertEqual(r["exactos"], 2)
        self.assertEqual([o["titulo"] for o in r["ofertas"]], ["exacta", "otra exacta"])

    def test_ordena_por_precio_ascendente(self):
        r = self._con_respuesta([_item("cara", "90"), _item("barata", "9"), _item("media", "40")])
        self.assertEqual([o["precio"] for o in r["ofertas"]], [9, 40, 90])

    def test_recorta_a_los_mas_baratos(self):
        items = [_item(f"p{i}", str(100 - i)) for i in range(10)]
        r = self._con_respuesta(items)
        self.assertEqual(len(r["ofertas"]), 3)
        self.assertEqual([o["precio"] for o in r["ofertas"]], [91.0, 92.0, 93.0])

    def test_las_ofertas_sin_precio_van_al_final(self):
        sin = _item("sin precio", "1")
        sin["price"] = {"value": None, "currency": "USD"}
        r = self._con_respuesta([sin, _item("con precio", "50")])
        self.assertEqual(r["ofertas"][0]["titulo"], "con precio")
        self.assertIsNone(r["ofertas"][-1]["precio"])

    def test_un_fallo_de_la_api_no_tumba_el_build(self):
        import urllib.error
        with mock.patch.object(ff, "_buscar", side_effect=urllib.error.HTTPError(
                "u", 403, "forbidden", None, None)):
            r = ff.buscar_categoria("token", VEHICULO, CATEGORIA)
        self.assertEqual(r["ofertas"], [])
        self.assertIn("403", r["error"])


class TestBuildFitment(unittest.TestCase):
    def test_agrega_y_cuenta_bien(self):
        def doble(token, anio, marca, modelo, category_id, limite=200):
            return {"total": 10, "itemSummaries": [_item("a", "5"), _item("b", "7", match="POSSIBLE")]}
        with mock.patch.object(ff, "_buscar", side_effect=doble):
            datos = ff.build_fitment([VEHICULO], categorias=[CATEGORIA], token="token")
        v = datos["vehiculos"][0]
        self.assertEqual(v["categorias_con_ofertas"], 1)
        self.assertEqual(v["ofertas_totales"], 1)
        self.assertEqual(datos["vehiculos"][0]["categorias"][0]["exactos"], 1)
        self.assertIn("updated_at", datos)
        self.assertIn("NO da el número de parte", datos["nota_numero_de_parte"])

    def test_vehiculo_sin_ofertas_queda_con_cero_y_no_se_rompe(self):
        with mock.patch.object(ff, "_buscar", return_value={"total": 0, "itemSummaries": []}):
            datos = ff.build_fitment([VEHICULO], categorias=[CATEGORIA], token="token")
        v = datos["vehiculos"][0]
        self.assertEqual(v["ofertas_totales"], 0)
        self.assertEqual(v["categorias_con_ofertas"], 0)


if __name__ == "__main__":
    unittest.main()
