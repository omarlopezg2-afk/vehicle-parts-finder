"""Pruebas herméticas de pipeline/enriquecer_detalles.py (T-B26 4.2). Nada de red."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from enriquecer_detalles import aplicar, pendientes  # noqa: E402
from fetch_autodoc import PresupuestoAgotado  # noqa: E402


def pastilla(aid, numero, **extra):
    return {"articleId": aid, "numero": numero, "marca": "X", "pieza": "Brake Pad Set, disc brake", **extra}


def disco(aid, numero, **extra):
    return {"articleId": aid, "numero": numero, "marca": "X", "pieza": "Brake Disc", **extra}


def catalogo():
    # Dos vehículos comparten la pastilla 11; el 12 ya tiene detalle; el disco 20 no es del producto.
    return {"vehiculos": [
        {"categorias": [{"buscado": "brake pad", "articulos": [
            disco(20, "D1", especificaciones={"Outer Diameter [mm]": "275"}),
            pastilla(11, "P1"), pastilla(12, "P2", oem=[{"numero": "1", "marca": "TOYOTA"}]),
            disco(21, "D2"),
        ]}]},
        {"categorias": [{"buscado": "brake pad", "articulos": [pastilla(11, "P1")]},
                        {"buscado": "oil filter", "articulos": [
                            {"articleId": 30, "numero": "F1", "marca": "Y", "pieza": "Oil Filter"}]}]},
    ]}


class PruebaPendientes(unittest.TestCase):
    def test_una_pastilla_compartida_se_pide_una_vez(self):
        pend = pendientes(catalogo(), ["brake pad"])
        self.assertEqual(list(pend), [11])
        self.assertEqual(len(pend[11]), 2, "las dos apariciones se completan con una consulta")

    def test_no_pide_lo_que_ya_tiene_detalle_ni_lo_que_no_es_el_producto(self):
        pend = pendientes(catalogo(), ["brake pad"])
        self.assertNotIn(12, pend)
        self.assertNotIn(21, pend, "un disco dentro de la categoría de pastillas no es el producto")

    def test_respeta_el_producto_pedido(self):
        self.assertEqual(list(pendientes(catalogo(), ["oil filter"])), [30])
        self.assertEqual(pendientes(catalogo(), ["spark plug"]), {})

    def test_solo_cuenta_lo_que_el_sitio_publica(self):
        # Con 5 pastillas sin detalle solo se publican las 3 primeras del producto: no se pagan las demás.
        arts = [pastilla(100 + i, f"P{i}") for i in range(5)]
        pend = pendientes({"vehiculos": [{"categorias": [{"buscado": "brake pad", "articulos": arts}]}]},
                          ["brake pad"])
        self.assertEqual(list(pend), [100, 101, 102])


class PruebaAplicar(unittest.TestCase):
    def test_escribe_el_detalle_en_todas_las_apariciones(self):
        cat = catalogo()
        pend = pendientes(cat, ["brake pad"])
        det = {"especificaciones": {"Fitting Position": "Front Axle"}, "oem": [{"numero": "04465", "marca": "TOYOTA"}]}
        hechos, cortado = aplicar(pend, None, pedir=lambda c, aid: det)
        self.assertEqual((hechos, cortado), (1, False))
        for v in cat["vehiculos"]:
            for c in v["categorias"]:
                for a in c["articulos"]:
                    if a["articleId"] == 11:
                        self.assertEqual(a["oem"], det["oem"])
                        self.assertEqual(a["especificaciones"], det["especificaciones"])

    def test_si_tecdoc_no_devuelve_detalle_la_pieza_se_queda_como_estaba(self):
        cat = catalogo()
        pend = pendientes(cat, ["brake pad"])
        hechos, _ = aplicar(pend, None, pedir=lambda c, aid: {})
        self.assertEqual(hechos, 0)
        self.assertNotIn("oem", cat["vehiculos"][1]["categorias"][0]["articulos"][0])

    def test_al_agotar_el_presupuesto_corta_y_conserva_lo_hecho(self):
        arts = [pastilla(200 + i, f"P{i}") for i in range(3)]
        cat = {"vehiculos": [{"categorias": [{"buscado": "brake pad", "articulos": arts}]}]}
        pend = pendientes(cat, ["brake pad"])
        llamadas = []

        def pedir(c, aid):
            llamadas.append(aid)
            if len(llamadas) == 2:
                raise PresupuestoAgotado("tope")
            return {"especificaciones": {"k": "v"}, "oem": []}

        hechos, cortado = aplicar(pend, None, pedir=pedir)
        self.assertEqual((hechos, cortado), (1, True))
        self.assertEqual(arts[0]["especificaciones"], {"k": "v"})
        self.assertNotIn("especificaciones", arts[1])


if __name__ == "__main__":
    unittest.main()
