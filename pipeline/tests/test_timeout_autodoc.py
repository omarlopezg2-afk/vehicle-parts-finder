"""La regresión que costó una noche entera (07/10/2026).

El bloque de flota se quedó 4 horas y media parado: un socket ESTABLISHED, 0 bytes pendientes,
CPU 0 y ninguna excepción. El `timeout` de urlopen estaba puesto (45s) y no lo cortó: el proceso
se quedó esperando una respuesta que no llegaba.

Aquí queda clavado que una petición colgada se corta sola y que el bloque sigue vivo. Si alguien
alguna vez 'simplifica' la función y quita la alarma, esta prueba se cae.
"""
from __future__ import annotations

import sys
import time
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(RAIZ))

from pipeline.fetch_autodoc import ClienteAutodoc  # noqa: E402


def test_una_peticion_que_nunca_responde_se_corta(monkeypatch=None):
    """No puede tardar más que el timeout, aunque el socket se quede mudo para siempre."""
    real = urllib.request.urlopen

    def se_duerme(*_a, **_k):
        time.sleep(600)

    urllib.request.urlopen = se_duerme
    try:
        t0 = time.time()
        estado, cuerpo = ClienteAutodoc._fetch_http("https://ejemplo.invalido/x", {}, timeout=2)
        demora = time.time() - t0
    finally:
        urllib.request.urlopen = real

    assert estado == 0, "una petición cortada no puede parecer una respuesta válida"
    assert cuerpo == ""
    assert demora < 5, f"tardó {demora:.1f}s: la alarma no está cortando la espera"


def test_la_alarma_no_deja_el_proceso_marcado():
    """Tras un corte, el cliente sigue funcionando: la alarma se desarma y no se cuela."""
    real = urllib.request.urlopen

    def falla(*_a, **_k):
        raise OSError("red caída")

    urllib.request.urlopen = falla
    try:
        assert ClienteAutodoc._fetch_http("https://ejemplo.invalido/x", {}, timeout=2) == (0, "")
        # Segunda llamada: si la alarma hubiera quedado armada, esta también devolvería 0.
        assert ClienteAutodoc._fetch_http("https://ejemplo.invalido/y", {}, timeout=2) == (0, "")
    finally:
        urllib.request.urlopen = real


if __name__ == "__main__":
    test_una_peticion_que_nunca_responde_se_corta()
    test_la_alarma_no_deja_el_proceso_marcado()
    print("OK: la espera se corta y el proceso queda limpio para la siguiente")
