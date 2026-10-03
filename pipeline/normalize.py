"""Normalización de números de parte.

Regla (CONTRACTS.md, congelado 25/09/2026):
    part_number_norm = part_number en MAYÚSCULAS, sin espacios, guiones, puntos ni
    barras (ni / ni \\). Ejemplo: "04152-YZZA1" -> "04152YZZA1".

Esto es lo único que este módulo hace. Lo usa fetch_ebay.py (busca por el número
normalizado) y, en la fase de build, pipeline/build_index.py (T-D1) para construir
el campo part_number_norm de data/build/parts.json.
"""

from __future__ import annotations

import re

# Caracteres que se eliminan: espacios (incluye tabs/saltos de línea vía \s),
# guion, punto, barra inclinada y barra invertida.
_CHARS_TO_STRIP_RE = re.compile(r"[\s\-\.\/\\]+")


def normalize_part_number(raw: str) -> str:
    """Normaliza un número de parte para búsqueda.

    - Mayúsculas.
    - Sin espacios (cualquier espacio en blanco), guiones, puntos, ni barras
      (/ o \\).
    - No valida el "shape" del número (eBay y los OEM usan formatos muy
      variados); solo limpia caracteres separadores.

    Args:
        raw: número de parte tal como viene de la fuente (para mostrar).

    Returns:
        El número normalizado (para buscar). Cadena vacía si raw es None/vacío.

    Raises:
        TypeError: si raw no es str (ni None).
    """
    if raw is None:
        return ""
    if not isinstance(raw, str):
        raise TypeError(f"normalize_part_number espera str o None, recibió {type(raw).__name__}")

    cleaned = _CHARS_TO_STRIP_RE.sub("", raw)
    return cleaned.upper()
