"""Tests de integridad de `data/build/categories.json` contra la taxonomía
congelada (T-F3, `docs/taxonomia-categorias.md`).

Convención compartida con los demás tests de pipeline/tests/: sys.path
insert + import por nombre simple, unittest (stdlib), sin dependencias
nuevas.

Verifica las DOS direcciones que pide la tarea:

  (a) todo `svg` referenciado en categories.json existe de verdad en
      site/assets/categories/ (un icono roto es un fallo visible para el
      usuario).
  (b) todo slug de categories.json (salvo el marcador `generico-sin-foto`,
      que el propio documento dice que NO es categoría de producto) está
      en la lista congelada de docs/taxonomia-categorias.md, con sus 5
      campos (slug, name_es, svg, group_slug, group_name_es) y el nombre
      de grupo en español coincide con el documento.

Si alguien agrega una categoría a categories.json sin su SVG, o sin fila
en el documento congelado, estos tests fallan (comprobado a mano
quitando un SVG y viendo el test en rojo antes de este commit).
"""

from __future__ import annotations

import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CATEGORIES_JSON = os.path.join(REPO_ROOT, "data", "build", "categories.json")
CATEGORIES_SVG_DIR = os.path.join(REPO_ROOT, "site", "assets", "categories")
TAXONOMIA_MD = os.path.join(REPO_ROOT, "docs", "taxonomia-categorias.md")

NO_ES_CATEGORIA_DE_PRODUCTO = {"generico-sin-foto"}

# Fila de tabla markdown: | `slug` | name_es | svg (existente/nuevo) |
_FILA_RE = re.compile(
    r"^\|\s*`([a-z0-9-]+)`\s*\|\s*([^|]+?)\s*\|\s*([a-z0-9-]+\.svg)\s*\([^)]*\)\s*\|$",
    re.MULTILINE,
)
_GRUPO_RE = re.compile(r"^### ([a-z0-9-]+) — (.+)$", re.MULTILINE)


def _parse_taxonomia_congelada() -> dict[str, dict[str, str]]:
    """Parsea docs/taxonomia-categorias.md y devuelve {slug: {name_es, svg,
    group_slug, group_name_es}} para las 33 categorías de producto.

    Recorre el documento línea por línea para asociar cada fila de tabla
    con el encabezado de grupo (### slug — Nombre) más reciente, en vez de
    asumir un orden fijo de secciones.
    """
    with open(TAXONOMIA_MD, "r", encoding="utf-8") as f:
        texto = f.read()

    congelado: dict[str, dict[str, str]] = {}
    grupo_actual: tuple[str, str] | None = None

    for linea in texto.splitlines():
        m_grupo = _GRUPO_RE.match(linea.strip())
        if m_grupo:
            grupo_actual = (m_grupo.group(1).strip(), m_grupo.group(2).strip())
            continue

        m_fila = _FILA_RE.match(linea.strip())
        if m_fila and grupo_actual:
            slug, name_es, svg = m_fila.groups()
            congelado[slug] = {
                "name_es": name_es.strip(),
                "svg": svg.strip(),
                "group_slug": grupo_actual[0],
                "group_name_es": grupo_actual[1],
            }

    return congelado


def _load_categories() -> list[dict]:
    with open(CATEGORIES_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


class TestTaxonomiaCongeladaParseable(unittest.TestCase):
    """Guarda contra que el propio parser del test se desactualice en
    silencio (si el documento cambia de formato y el regex deja de
    encontrar filas, este test lo detecta antes que los de abajo)."""

    def test_el_documento_tiene_exactamente_33_categorias_de_producto(self):
        congelado = _parse_taxonomia_congelada()
        self.assertEqual(
            len(congelado), 33,
            f"El parser encontró {len(congelado)} filas; se esperaban 33. "
            "¿Cambió el formato de docs/taxonomia-categorias.md?",
        )


class TestCategoriesJsonContraTaxonomiaCongelada(unittest.TestCase):
    def setUp(self):
        self.categorias = _load_categories()
        self.congelado = _parse_taxonomia_congelada()

    def test_cada_entrada_tiene_los_5_campos_del_contrato(self):
        campos = {"slug", "name_es", "svg", "group_slug", "group_name_es"}
        for cat in self.categorias:
            faltantes = campos - cat.keys()
            self.assertFalse(
                faltantes,
                f"{cat.get('slug', cat)!r} le faltan los campos {faltantes}",
            )

    def test_hay_exactamente_33_categorias_de_producto_mas_el_marcador(self):
        slugs = {c["slug"] for c in self.categorias}
        productos = slugs - NO_ES_CATEGORIA_DE_PRODUCTO
        self.assertEqual(len(productos), 33, f"Categorías de producto: {sorted(productos)}")
        self.assertIn("generico-sin-foto", slugs)
        self.assertEqual(len(self.categorias), 34)

    def test_todo_slug_de_producto_esta_en_la_lista_congelada(self):
        for cat in self.categorias:
            slug = cat["slug"]
            if slug in NO_ES_CATEGORIA_DE_PRODUCTO:
                continue
            self.assertIn(
                slug, self.congelado,
                f"'{slug}' está en categories.json pero no en la taxonomía "
                "congelada (docs/taxonomia-categorias.md)",
            )

    def test_todo_slug_congelado_esta_en_categories_json(self):
        slugs_actuales = {c["slug"] for c in self.categorias}
        for slug in self.congelado:
            self.assertIn(
                slug, slugs_actuales,
                f"'{slug}' está en la taxonomía congelada pero falta en categories.json",
            )

    def test_name_es_group_slug_group_name_es_coinciden_con_el_documento(self):
        por_slug = {c["slug"]: c for c in self.categorias}
        for slug, esperado in self.congelado.items():
            real = por_slug[slug]
            self.assertEqual(real["name_es"], esperado["name_es"], f"name_es de '{slug}'")
            self.assertEqual(real["group_slug"], esperado["group_slug"], f"group_slug de '{slug}'")
            self.assertEqual(
                real["group_name_es"], esperado["group_name_es"], f"group_name_es de '{slug}'"
            )

    def test_svg_de_categories_json_coincide_con_el_del_documento(self):
        por_slug = {c["slug"]: c for c in self.categorias}
        for slug, esperado in self.congelado.items():
            self.assertEqual(por_slug[slug]["svg"], esperado["svg"], f"svg de '{slug}'")


class TestTodosLosSvgReferenciadosExisten(unittest.TestCase):
    """(a) de la tarea: todo `svg` de categories.json existe en disco."""

    def test_cada_svg_referenciado_existe_en_site_assets_categories(self):
        categorias = _load_categories()
        faltantes = []
        for cat in categorias:
            ruta = os.path.join(CATEGORIES_SVG_DIR, cat["svg"])
            if not os.path.isfile(ruta):
                faltantes.append((cat["slug"], cat["svg"]))
        self.assertFalse(
            faltantes,
            f"SVG faltante para: {faltantes} (icono roto visible al usuario)",
        )

    def test_cada_svg_existente_es_xml_valido_con_viewbox_64x64(self):
        import xml.etree.ElementTree as ET

        categorias = _load_categories()
        for cat in categorias:
            ruta = os.path.join(CATEGORIES_SVG_DIR, cat["svg"])
            if not os.path.isfile(ruta):
                continue  # ya lo reporta el test anterior
            try:
                ET.parse(ruta)
            except ET.ParseError as e:
                self.fail(f"{cat['svg']} no es XML válido: {e}")
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = f.read()
            self.assertIn(
                'viewBox="0 0 64 64"', contenido,
                f"{cat['svg']} no usa el viewBox 0 0 64 64 del estilo existente",
            )


if __name__ == "__main__":
    unittest.main()
