"""Pruebas de pipeline/partir_catalogo.py (T-B19 y T-B27).

`partir_catalogo` es el que decide QUÉ se publica, así que sus dos reglas se prueban aquí:
  1. se conserva lo detallado (especificaciones u originales) — lo que distingue una pieza,
  2. y ADEMÁS el artículo que es el producto de la categoría, aunque no esté detallado: sin eso el
     sitio decía "no tenemos piezas" en 307 vehículo-categoría que sí tenían el número descargado.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from partir_catalogo import _normalizar, _sin_repetir, articulos_utiles, vehiculo_completo  # noqa: E402


def articulo(numero, pieza, **extra):
    return {"numero": numero, "marca": "MARCA", "pieza": pieza, "foto": None, **extra}


CATEGORIA = {
    "nombre": "Disc Brake", "buscado": "brake pad", "ruta": "Braking System / Disc Brake",
    "articulos": [
        # los 3 primeros son discos (les tocó el detalle) y NO son el producto de la categoría
        articulo("D-1", "Brake Disc", especificaciones={"Thickness [mm]": "26"}),
        articulo("D-2", "Brake Disc", especificaciones={"Thickness [mm]": "22"}),
        articulo("D-3", "Brake Disc", oem=[{"numero": "4351202330", "marca": "TOYOTA"}]),
        # las pastillas están en el volcado, sin detallar: SON lo que el sitio va a enseñar
        articulo("P-1", "Brake Pad Set, disc brake"),
        articulo("P-2", "Brake Pad Set, disc brake"),
        # ruido: nada que ver con la categoría
        articulo("X-1", "Sensor, wheel speed"),
        articulo("", "Brake Pad Set, disc brake"),          # sin número: no entra
    ],
}


class PruebaArticulosUtiles(unittest.TestCase):
    def test_publica_lo_detallado_y_ademas_el_producto_de_la_categoria(self):
        utiles = articulos_utiles(CATEGORIA)
        numeros = [a["numero"] for a in utiles]
        self.assertEqual(numeros[:2], ["D-1", "D-2"], "los detallados van primero")
        self.assertIn("P-1", numeros, "la pastilla tiene que publicarse aunque no esté detallada")
        self.assertNotIn("X-1", numeros, "lo que no es el producto de la categoría no entra")

    def test_quita_repetidos_por_numero_y_marca(self):
        repetido = dict(CATEGORIA)
        repetido["articulos"] = CATEGORIA["articulos"] + [articulo("P-1", "Brake Pad Set, disc brake")]
        self.assertEqual(len(articulos_utiles(repetido)), len(articulos_utiles(CATEGORIA)))

    def test_sin_nada_que_coincida_no_publica_nada(self):
        otra = {"nombre": "Lubrication", "buscado": "oil filter", "articulos": [
            articulo("D-1", "Brake Disc", especificaciones={"x": "1"})]}
        self.assertEqual([a["numero"] for a in articulos_utiles(otra)], ["D-1"],
                         "lo detallado se conserva aunque no sea el buscado")
        vacia = {"buscado": "oil filter", "articulos": [articulo("D-1", "Brake Disc")]}
        self.assertEqual(articulos_utiles(vacia), [], "nunca rellena")

    def test_una_categoria_sin_buscado_solo_publica_lo_detallado(self):
        sin = {"buscado": None, "articulos": [articulo("D-1", "Brake Disc"),
                                              articulo("D-2", "Brake Disc", oem=[{"numero": "1"}])]}
        self.assertEqual([a["numero"] for a in articulos_utiles(sin)], ["D-2"])

    def test_la_normalizacion_no_distingue_acentos_ni_mayusculas(self):
        self.assertEqual(_normalizar("Bujía"), "bujia")
        self.assertEqual(_normalizar("  BRAKE  PAD "), "brake  pad")
        self.assertEqual(_normalizar(None), "")

    def test_sin_repetir_quita_los_que_no_tienen_numero(self):
        self.assertEqual(_sin_repetir([articulo("", "x"), articulo("A", "x")]), [articulo("A", "x")])


    def test_sin_tope_una_categoria_de_filtros_publicaria_el_volcado_de_marcas(self):
        filtros = {"buscado": "oil filter", "articulos": [
            articulo(f"F-{i}", "Oil Filter") for i in range(10)]}
        self.assertEqual(len(articulos_utiles(filtros)), 3, "solo 3: el número, no las 10 marcas")
        self.assertEqual(len(articulos_utiles(filtros, tope_del_producto=5)), 5)


class PruebaVehiculoCompleto(unittest.TestCase):
    """El bloque `vehiculo` de una entrada de flota ya viene escrito por el pipeline (T-B25)."""

    def test_si_ya_trae_marca_se_respeta_tal_cual(self):
        entrada = {"vehiculo": {"make": "Toyota", "model": "Corolla", "year": "2016",
                                "combustible": "Petrol", "motor": "2ZR-FE"}}
        self.assertEqual(vehiculo_completo(entrada, []), entrada["vehiculo"])

    def test_si_no_lo_trae_se_deriva_de_la_semilla_y_la_etiqueta(self):
        flota = [{"make": "Toyota", "model": "Corolla"}]
        v = vehiculo_completo({"etiqueta": "Toyota Corolla 2016 1.3 Dual-VVTi (NRE180_)"}, flota)
        self.assertEqual((v["make"], v["model"], v["year"]), ("Toyota", "Corolla", "2016"))
        self.assertEqual(v["variante"], "1.3 Dual-VVTi (NRE180_)")
        self.assertEqual(v["origen"], "flota")


if __name__ == "__main__":
    unittest.main()
