"""Tests de pipeline/validate.py (T-D1).

Convención compartida con los demás tests de pipeline/tests/: sys.path
insert + import por nombre simple.

No toca los archivos reales de data/build/: construye dicts en memoria y
llama directo a las funciones validate_* / run_validation (con monkeypatch
de _load_json cuando hace falta), así los tests son deterministas y no
dependen del estado actual de data/build/.
"""

from __future__ import annotations

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import validate  # noqa: E402


def _parte_valida(**overrides):
    base = {
        "id": "toyota-filtro-aceite-04152-yzza1",
        "part_number": "04152-YZZA1",
        "part_number_norm": "04152YZZA1",
        "type": "OEM",
        "brand": "Toyota",
        "name": "Filtro de aceite",
        "category": "filtro-aceite",
        "epc_link": {"source": None, "url": None},
        "image": {"url": None, "source": "generic", "credit": None},
        "equivalents": [],
        "fitment_ids": [],
        "offers": [],
        "updated_at": "2026-09-25T00:00:00Z",
    }
    base.update(overrides)
    return base


class TestValidateParts(unittest.TestCase):
    def test_parte_valida_no_genera_errores(self):
        errores = validate.ValidationErrors()
        validate.validate_parts([_parte_valida()], errores)
        self.assertEqual(list(errores), [])

    def test_epc_link_faltante_es_error(self):
        parte = _parte_valida()
        del parte["epc_link"]
        errores = validate.ValidationErrors()
        validate.validate_parts([parte], errores)
        self.assertTrue(any("epc_link" in e for e in errores))

    def test_epc_link_con_source_y_url_null_es_valido(self):
        # Regla explícita de CONTRACTS.md: epc_link es obligatorio como
        # clave, pero su contenido puede ser null mientras no se resuelva.
        parte = _parte_valida(epc_link={"source": None, "url": None})
        errores = validate.ValidationErrors()
        validate.validate_parts([parte], errores)
        self.assertEqual(list(errores), [])

    def test_part_number_norm_mal_calculado_es_error(self):
        parte = _parte_valida(part_number_norm="04152-YZZA1")  # no debería tener guión
        errores = validate.ValidationErrors()
        validate.validate_parts([parte], errores)
        self.assertTrue(any("part_number_norm" in e for e in errores))

    def test_type_invalido_es_error(self):
        parte = _parte_valida(type="REFABRICADO")
        errores = validate.ValidationErrors()
        validate.validate_parts([parte], errores)
        self.assertTrue(any("'type'" in e for e in errores))

    def test_id_duplicado_es_error(self):
        errores = validate.ValidationErrors()
        validate.validate_parts([_parte_valida(), _parte_valida()], errores)
        self.assertTrue(any("duplicado" in e for e in errores))

    def test_offer_sin_claves_requeridas_es_error(self):
        parte = _parte_valida(offers=[{"store": "eBay"}])
        errores = validate.ValidationErrors()
        validate.validate_parts([parte], errores)
        self.assertTrue(any("oferta sin claves requeridas" in e for e in errores))

    def test_offer_bien_formada_no_genera_error(self):
        parte = _parte_valida(offers=[{
            "store": "eBay", "url": "https://www.ebay.com/itm/1",
            "price": 9.99, "currency": "USD", "condition": "New",
            "updated_at": "2026-09-25T00:00:00Z",
        }])
        errores = validate.ValidationErrors()
        validate.validate_parts([parte], errores)
        self.assertEqual(list(errores), [])

    def test_updated_at_no_iso8601_es_error(self):
        parte = _parte_valida(updated_at="25/09/2026")
        errores = validate.ValidationErrors()
        validate.validate_parts([parte], errores)
        self.assertTrue(any("ISO-8601" in e for e in errores))

    def test_no_es_lista_es_error(self):
        errores = validate.ValidationErrors()
        validate.validate_parts({"no": "es una lista"}, errores)
        self.assertTrue(any("debería ser una lista" in e for e in errores))

    def test_other_names_ausente_no_genera_error(self):
        # T-D2: other_names es opcional -- no debe exigirse como clave.
        parte = _parte_valida()
        self.assertNotIn("other_names", parte)
        errores = validate.ValidationErrors()
        validate.validate_parts([parte], errores)
        self.assertEqual(list(errores), [])

    def test_other_names_lista_de_strings_es_valido(self):
        parte = _parte_valida(other_names=["Bumper Cover Retainer Clip", "Grille Clip"])
        errores = validate.ValidationErrors()
        validate.validate_parts([parte], errores)
        self.assertEqual(list(errores), [])

    def test_other_names_como_string_es_error(self):
        # Tipo incorrecto explícito del enunciado de T-D2: other_names como
        # string en vez de array debe fallar validate.py.
        parte = _parte_valida(other_names="Grille Clip")
        errores = validate.ValidationErrors()
        validate.validate_parts([parte], errores)
        self.assertTrue(any("other_names" in e for e in errores))

    def test_other_names_con_elemento_no_string_es_error(self):
        parte = _parte_valida(other_names=["Grille Clip", 123])
        errores = validate.ValidationErrors()
        validate.validate_parts([parte], errores)
        self.assertTrue(any("other_names" in e for e in errores))


class TestValidateVehicles(unittest.TestCase):
    def test_vehiculo_valido_no_genera_errores(self):
        errores = validate.ValidationErrors()
        validate.validate_vehicles([{
            "id": "vin-X", "make": "Mitsubishi", "model": "Outlander Sport",
            "year": 2020, "trim": None, "engine": None,
        }], errores)
        self.assertEqual(list(errores), [])

    def test_year_como_string_es_error(self):
        errores = validate.ValidationErrors()
        validate.validate_vehicles([{
            "id": "vin-X", "make": "Mitsubishi", "model": "Outlander Sport",
            "year": "2020", "trim": None, "engine": None,
        }], errores)
        self.assertTrue(any("'year'" in e for e in errores))

    def test_falta_make_es_error(self):
        errores = validate.ValidationErrors()
        validate.validate_vehicles([{
            "id": "vin-X", "model": "Outlander Sport",
            "year": 2020, "trim": None, "engine": None,
        }], errores)
        self.assertTrue(any("make" in e for e in errores))


class TestValidateSearchIndex(unittest.TestCase):
    def test_entrada_valida_no_genera_errores(self):
        errores = validate.ValidationErrors()
        validate.validate_search_index([{
            "id": "a", "part_number_norm": "ABC123", "name": "Filtro", "brand": "Toyota",
        }], errores)
        self.assertEqual(list(errores), [])

    def test_part_number_norm_no_normalizado_es_error(self):
        errores = validate.ValidationErrors()
        validate.validate_search_index([{
            "id": "a", "part_number_norm": "abc-123", "name": "Filtro", "brand": "Toyota",
        }], errores)
        self.assertTrue(any("normalizado" in e for e in errores))


class TestValidateCategories(unittest.TestCase):
    def test_categoria_valida_no_genera_errores(self):
        errores = validate.ValidationErrors()
        validate.validate_categories([{
            "slug": "filtro-aceite", "name_es": "Filtro de aceite", "svg": "filtro-aceite.svg",
        }], errores)
        self.assertEqual(list(errores), [])

    def test_slug_duplicado_es_error(self):
        errores = validate.ValidationErrors()
        cat = {"slug": "filtro-aceite", "name_es": "Filtro de aceite", "svg": "filtro-aceite.svg"}
        validate.validate_categories([cat, dict(cat)], errores)
        self.assertTrue(any("duplicado" in e for e in errores))


class TestValidateReferentialIntegrity(unittest.TestCase):
    """T-D5: integridad referencial entre parts/vehicles/categories.

    Reproduce el bug real de Ronda 3 (MR297182 -> 'clip-parachoques', un slug
    que nunca existió en categories.json) para asegurar que no vuelva a pasar
    desapercibido.
    """

    _CATEGORIAS = [
        {"slug": "filtro-aceite", "name_es": "Filtro de aceite", "svg": "filtro-aceite.svg"},
        {"slug": "clips-y-sujeciones", "name_es": "Clips y sujeciones", "svg": "clips-y-sujeciones.svg"},
    ]
    _VEHICULOS = [
        {"id": "vin-ABC", "make": "Toyota", "model": "Corolla", "year": 2020, "trim": None, "engine": None},
    ]

    def test_categoria_existente_no_genera_error(self):
        errores = validate.ValidationErrors()
        validate.validate_referential_integrity(
            [_parte_valida(category="filtro-aceite")], self._VEHICULOS, self._CATEGORIAS, errores,
        )
        self.assertEqual(list(errores), [])

    def test_categoria_huerfana_es_error(self):
        # Caso real: 'clip-parachoques' no existe en categories.json.
        errores = validate.ValidationErrors()
        validate.validate_referential_integrity(
            [_parte_valida(category="clip-parachoques")], self._VEHICULOS, self._CATEGORIAS, errores,
        )
        self.assertTrue(any("no existe en categories.json" in e for e in errores))

    def test_fitment_id_valido_no_genera_error(self):
        errores = validate.ValidationErrors()
        validate.validate_referential_integrity(
            [_parte_valida(fitment_ids=["vin-ABC"])], self._VEHICULOS, self._CATEGORIAS, errores,
        )
        self.assertEqual(list(errores), [])

    def test_fitment_id_huerfano_es_error(self):
        errores = validate.ValidationErrors()
        validate.validate_referential_integrity(
            [_parte_valida(fitment_ids=["vin-NO-EXISTE"])], self._VEHICULOS, self._CATEGORIAS, errores,
        )
        self.assertTrue(any("no existe en vehicles.json" in e for e in errores))

    def test_fitment_ids_vacio_es_valido(self):
        errores = validate.ValidationErrors()
        validate.validate_referential_integrity(
            [_parte_valida(fitment_ids=[])], self._VEHICULOS, self._CATEGORIAS, errores,
        )
        self.assertEqual(list(errores), [])

    def test_se_invoca_desde_run_validation_sobre_los_archivos_reales(self):
        # Si build_index.py ya corrió en este checkout, run_validation() debe
        # seguir en verde incorporando este chequeo cruzado (no solo la forma).
        ruta = os.path.join(validate.BUILD_DIR, "parts.json")
        if not os.path.isfile(ruta):
            self.skipTest("data/build/parts.json no existe todavía.")
        errores = validate.run_validation()
        self.assertEqual(list(errores), [], msg="\n".join(errores))


class TestRunValidationIntegration(unittest.TestCase):
    """Prueba run_validation() contra los 4 archivos reales de data/build/
    (generados por build_index.py). Si build_index.py no corrió todavía en
    este checkout, se salta con un mensaje claro en vez de fallar engañoso.
    """

    def test_archivos_reales_de_data_build_validan_si_existen(self):
        ruta = os.path.join(validate.BUILD_DIR, "parts.json")
        if not os.path.isfile(ruta):
            self.skipTest(
                "data/build/parts.json no existe todavía: correr "
                "'python pipeline/build_index.py' primero."
            )
        errores = validate.run_validation()
        self.assertEqual(list(errores), [], msg="\n".join(errores))

    def test_main_devuelve_0_cuando_no_hay_errores(self):
        with mock.patch.object(validate, "run_validation", return_value=validate.ValidationErrors()):
            self.assertEqual(validate.main(), 0)

    def test_main_devuelve_distinto_de_0_cuando_hay_errores(self):
        errores_falsos = validate.ValidationErrors()
        errores_falsos.add("parts.json[0]", "error de prueba")
        with mock.patch.object(validate, "run_validation", return_value=errores_falsos):
            self.assertNotEqual(validate.main(), 0)


if __name__ == "__main__":
    unittest.main()
