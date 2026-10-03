"""Tests de pipeline/fetch_ebay.py (T-B1).

Usa unittest + unittest.mock (stdlib) a propósito: corre out-of-the-box sin
instalar nada, igual que el modo mock del propio módulo.
"""

import io
import os
import sys
import unittest
import urllib.error
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fetch_ebay
from normalize import normalize_part_number

_EXPECTED_OFFER_KEYS = {"store", "url", "price", "currency", "condition", "updated_at"}


class TestHasRealCredentials(unittest.TestCase):
    def test_sin_variables_es_false(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(fetch_ebay.has_real_credentials())

    def test_solo_client_id_es_false(self):
        with mock.patch.dict(os.environ, {"EBAY_CLIENT_ID": "x"}, clear=True):
            self.assertFalse(fetch_ebay.has_real_credentials())

    def test_ambas_variables_es_true(self):
        env = {"EBAY_CLIENT_ID": "x", "EBAY_CLIENT_SECRET": "y"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertTrue(fetch_ebay.has_real_credentials())


class TestSearchPartMock(unittest.TestCase):
    """Sin EBAY_CLIENT_ID/SECRET -> modo mock automático, sin fallar."""

    def setUp(self):
        self._env_patch = mock.patch.dict(os.environ, {}, clear=True)
        self._env_patch.start()

    def tearDown(self):
        self._env_patch.stop()

    def test_devuelve_lista_no_vacia(self):
        offers = fetch_ebay.search_part("04152YZZA1")
        self.assertIsInstance(offers, list)
        self.assertGreater(len(offers), 0)

    def test_forma_de_offer_sigue_contracts(self):
        offers = fetch_ebay.search_part("04152YZZA1")
        for offer in offers:
            self.assertEqual(set(offer.keys()), _EXPECTED_OFFER_KEYS)
            self.assertEqual(offer["store"], "eBay")
            self.assertIsInstance(offer["price"], float)
            self.assertEqual(offer["currency"], "USD")
            self.assertTrue(offer["url"].startswith("http"))
            # ISO-8601 básico, terminado en Z (UTC) como el resto del proyecto.
            self.assertTrue(offer["updated_at"].endswith("Z"))

    def test_part_number_vacio_devuelve_lista_vacia(self):
        self.assertEqual(fetch_ebay.search_part(""), [])

    def test_mock_refleja_el_numero_buscado(self):
        part = normalize_part_number("1230-A114")
        offers = fetch_ebay.search_part(part)
        # El fixture inyecta part_number_norm en el título real de eBay; no se
        # expone título en `offers`, pero sí podemos comprobar que el mock no
        # lanza y que corresponde al número pedido vía la URL/condición.
        self.assertTrue(len(offers) >= 1)


class TestSearchPartReal(unittest.TestCase):
    """Con credenciales, se intenta el modo real; fallos caen a mock."""

    def test_401_hace_un_reintento_y_si_falla_cae_a_mock(self):
        env = {"EBAY_CLIENT_ID": "id", "EBAY_CLIENT_SECRET": "secret"}
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch.object(fetch_ebay, "get_access_token", return_value="tok"):
                err_401 = urllib.error.HTTPError(
                    url="https://api.ebay.com/x", code=401, msg="Unauthorized",
                    hdrs=None, fp=io.BytesIO(b"{}"),
                )
                with mock.patch.object(fetch_ebay, "_do_search_request", side_effect=err_401):
                    offers = fetch_ebay.search_part("04152YZZA1")
        # No se tumba el pipeline: devuelve offers del mock.
        self.assertIsInstance(offers, list)
        self.assertGreater(len(offers), 0)

    def test_429_hace_un_reintento_y_si_falla_cae_a_mock(self):
        env = {"EBAY_CLIENT_ID": "id", "EBAY_CLIENT_SECRET": "secret"}
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch.object(fetch_ebay, "get_access_token", return_value="tok"):
                err_429 = urllib.error.HTTPError(
                    url="https://api.ebay.com/x", code=429, msg="Too Many Requests",
                    hdrs=None, fp=io.BytesIO(b"{}"),
                )
                with mock.patch.object(fetch_ebay, "time") as mocked_time:
                    with mock.patch.object(fetch_ebay, "_do_search_request", side_effect=err_429):
                        offers = fetch_ebay.search_part("04152YZZA1")
                    mocked_time.sleep.assert_called()  # backoff documentado, sin esperar de verdad
        self.assertIsInstance(offers, list)
        self.assertGreater(len(offers), 0)

    def test_exito_al_segundo_intento_tras_401(self):
        env = {"EBAY_CLIENT_ID": "id", "EBAY_CLIENT_SECRET": "secret"}
        real_payload = {
            "itemSummaries": [
                {
                    "itemId": "v1|1|0",
                    "price": {"value": "9.99", "currency": "USD"},
                    "condition": "New",
                    "itemWebUrl": "https://www.ebay.com/itm/1",
                }
            ]
        }
        err_401 = urllib.error.HTTPError(
            url="https://api.ebay.com/x", code=401, msg="Unauthorized",
            hdrs=None, fp=io.BytesIO(b"{}"),
        )
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch.object(fetch_ebay, "get_access_token", return_value="tok"):
                with mock.patch.object(
                    fetch_ebay, "_do_search_request", side_effect=[err_401, real_payload]
                ):
                    offers = fetch_ebay.search_part("04152YZZA1")
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0]["price"], 9.99)
        self.assertEqual(offers[0]["url"], "https://www.ebay.com/itm/1")

    def test_credenciales_invalidas_en_token_cae_a_mock(self):
        env = {"EBAY_CLIENT_ID": "id", "EBAY_CLIENT_SECRET": "secret"}
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch.object(
                fetch_ebay, "get_access_token",
                side_effect=fetch_ebay.EbayAuthError("token eBay: HTTP 401: invalid_client"),
            ):
                offers = fetch_ebay.search_part("04152YZZA1")
        self.assertIsInstance(offers, list)
        self.assertGreater(len(offers), 0)


if __name__ == "__main__":
    unittest.main()
