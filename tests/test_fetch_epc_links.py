"""
Tests para pipeline/fetch_epc_links.py (T-C1).

No hace llamadas de red: solo verifica que la construccion de URLs sea
correcta y consistente. La verificacion "la URL abre y muestra contenido
real" se hizo a mano/con curl fuera de este test (ver docstring del modulo
y la descripcion del PR) porque requiere red real y un navegador no-headless
para pasar el challenge de Cloudflare.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.fetch_epc_links import get_epc_links  # noqa: E402


# ---------------------------------------------------------------------------
# Caso principal del contrato: Outlander Sport 2020, filtro de aceite
# ---------------------------------------------------------------------------

def test_outlander_sport_2020_filtro_aceite_devuelve_7zap_verificado():
    links = get_epc_links("Mitsubishi", "Outlander Sport", 2020, "filtro-aceite")
    assert len(links) >= 1
    primero = links[0]
    assert primero["source"] == "7zap"
    assert primero["url"] == (
        "https://7zap.com/en/catalog/cars/mitsubishi/"
        "asx-outlander-sport-rvr-4th-facelift-parts-catalog/"
        "oil-pump-oil-filter/"
    )
    # Es la unica categoria que verificamos en vivo -> confianza alta.
    assert primero["confidence"] == "alta"


def test_outlander_sport_2020_incluye_partsouq_como_alternativa_por_vin():
    vin = "JA4AR3AU0LU018776"  # formato real de VIN de Mitsubishi (17 chars)
    links = get_epc_links(
        "Mitsubishi", "Outlander Sport", 2020, "filtro-aceite", vin=vin
    )
    fuentes = {l["source"] for l in links}
    assert "7zap" in fuentes
    assert "partsouq" in fuentes
    partsouq = next(l for l in links if l["source"] == "partsouq")
    assert partsouq["url"] == f"https://partsouq.com/en/search/all?q={vin}"


def test_outlander_sport_2020_motor_usa_slug_de_categoria_correcto():
    links = get_epc_links("Mitsubishi", "Outlander Sport", 2020, "motor")
    sevenzap = next(l for l in links if l["source"] == "7zap")
    assert sevenzap["url"].endswith("/engine/")


def test_outlander_sport_2020_frenos_cae_en_chassis_systems():
    # 7zap no separa "frenos" como ensamblaje propio para esta generacion;
    # documentamos que usamos el grupo paraguas "Chassis Systems".
    links = get_epc_links("Mitsubishi", "Outlander Sport", 2020, "frenos")
    sevenzap = next(l for l in links if l["source"] == "7zap")
    assert sevenzap["url"].endswith("/chassis-systems/")


# ---------------------------------------------------------------------------
# Variantes de nombre de modelo (ASX / RVR en otros mercados)
# ---------------------------------------------------------------------------

def test_asx_mismo_vehiculo_mismo_slug_de_generacion():
    links_asx = get_epc_links("Mitsubishi", "ASX", 2020, "filtro-aceite")
    links_sport = get_epc_links("Mitsubishi", "Outlander Sport", 2020, "filtro-aceite")
    assert links_asx[0]["url"] == links_sport[0]["url"]


def test_rvr_mismo_vehiculo_mismo_slug_de_generacion():
    links_rvr = get_epc_links("Mitsubishi", "RVR", 2020, "filtro-aceite")
    links_sport = get_epc_links("Mitsubishi", "Outlander Sport", 2020, "filtro-aceite")
    assert links_rvr[0]["url"] == links_sport[0]["url"]


# ---------------------------------------------------------------------------
# Generaciones distintas por año (facelifts) deben dar slugs distintos
# ---------------------------------------------------------------------------

def test_outlander_sport_2015_usa_generacion_1st_facelift():
    links = get_epc_links("Mitsubishi", "Outlander Sport", 2015, "filtro-aceite")
    sevenzap = next(l for l in links if l["source"] == "7zap")
    assert "1st-facelift" in sevenzap["url"]


def test_outlander_sport_2011_usa_generacion_base():
    links = get_epc_links("Mitsubishi", "Outlander Sport", 2011, "filtro-aceite")
    sevenzap = next(l for l in links if l["source"] == "7zap")
    assert "asx-outlander-sport-rvr-parts-catalog" in sevenzap["url"]
    assert "facelift" not in sevenzap["url"]


# ---------------------------------------------------------------------------
# Casos donde NO debemos inventar nada
# ---------------------------------------------------------------------------

def test_marca_sin_mapeo_no_inventa_url():
    # No tenemos a Toyota mapeado en _SEVENZAP_GENERATIONS; debe devolver
    # lista vacia (o solo partsouq si hay VIN/numero de parte) en vez de
    # adivinar un slug de 7zap que podria ser un 404.
    links = get_epc_links("Toyota", "Corolla", 2020, "filtro-aceite")
    assert all(l["source"] != "7zap" for l in links)


def test_sin_datos_minimos_devuelve_lista_vacia():
    assert get_epc_links("", "", 0, "filtro-aceite") == []
    assert get_epc_links("Mitsubishi", "", 2020, "filtro-aceite") == []


def test_sin_vin_ni_numero_de_parte_no_da_partsouq():
    links = get_epc_links("Mitsubishi", "Outlander Sport", 2020, "filtro-aceite")
    assert all(l["source"] != "partsouq" for l in links)


def test_categoria_desconocida_cae_a_pagina_de_generacion_sin_inventar_slug():
    links = get_epc_links(
        "Mitsubishi", "Outlander Sport", 2020, "categoria-que-no-existe"
    )
    sevenzap = next(l for l in links if l["source"] == "7zap")
    assert sevenzap["url"] == (
        "https://7zap.com/en/catalog/cars/mitsubishi/"
        "asx-outlander-sport-rvr-4th-facelift-parts-catalog/"
    )
    assert sevenzap["confidence"] == "media"


def test_vin_invalido_no_genera_link_de_partsouq_ni_decoder():
    links = get_epc_links(
        "Mitsubishi", "Outlander Sport", 2020, "filtro-aceite", vin="VIN-CORTO"
    )
    assert all(l["source"] != "partsouq" for l in links)
    # El decoder de 7zap tampoco debe aparecer con un VIN invalido.
    assert len(links) == 1  # solo el link directo de 7zap por generacion


def test_numero_de_parte_se_usa_para_partsouq_si_no_hay_vin():
    links = get_epc_links(
        "Mitsubishi",
        "Outlander Sport",
        2020,
        "filtro-aceite",
        part_number_norm="1230A152",
    )
    partsouq = next(l for l in links if l["source"] == "partsouq")
    assert partsouq["url"] == "https://partsouq.com/en/search/all?q=1230A152"
