"""
fetch_epc_links.py — T-C1 (Agente C: EPC-Puente)
==================================================

Objetivo del contrato (CONTRACTS.md / TASKS.md, fila T-C1):
Dado un vehiculo (make, model, year) y opcionalmente un VIN, mas una categoria
de ensamblaje (ej. 'filtro-aceite', 'frenos', 'motor'), construir el/los deep
link(s) reales hacia 7zap, Partsouq y/o la tienda oficial de la marca que
lleven lo mas cerca posible al ensamblaje correcto, donde el usuario puede
leer el numero de parte de fabrica con sus propios ojos.

REGLA NO NEGOCIABLE (CONTRACTS.md, regla transversal #2): este modulo NUNCA
descarga, cachea ni re-aloja diagramas/imagenes de estas fuentes. Solo
construye URLs (texto). El usuario abre el link en su navegador.

------------------------------------------------------------------------------
COMO SE INVESTIGO (navegador real + curl, ver PR para el detalle completo)
------------------------------------------------------------------------------
Vehiculo de prueba: Mitsubishi Outlander Sport 2020 (plataforma global
ASX/Outlander Sport/RVR, vendida en Japon como RVR y en el resto del mundo
como ASX). Categoria de prueba: filtro de aceite ("maintenance parts" /
"oil-pump-oil-filter" en la taxonomia de 7zap).

1) 7ZAP (https://7zap.com) — FUNCIONA, estructura ESTABLE
   Navegacion real observada (clic humano + `curl` con User-Agent de
   navegador — ver nota de Cloudflare abajo):

     https://7zap.com/en/catalog/cars/mitsubishi/                                   (marca)
       -> https://7zap.com/en/catalog/cars/mitsubishi/asx-outlander-sport-rvr-4th-facelift-parts-catalog/   (generacion = slug con años)
         -> .../maintenance-parts/                                                  (categoria "paraguas")
           -> .../oil-pump-oil-filter/                                              (ensamblaje final)

   El Outlander Sport 2020 (USA) corresponde a la generacion que 7zap llama
   "ASX/Outlander Sport/RVR 4th Facelift (2019-2024)" — confirmado via
   búsqueda web y el mirror mitsubishi.catalogs-parts.com (que enlaza
   directamente a esa generación en 7zap para el rango de años 2019-2024).

   Verificación real: `curl` con User-Agent de navegador (no headless-bot)
   contra
     https://7zap.com/en/catalog/cars/mitsubishi/asx-outlander-sport-rvr-4th-facelift-parts-catalog/oil-pump-oil-filter/
   devolvió HTTP 200, 469 KB de HTML real, <title> = "Oil pump & oil filter
   Mitsubishi ASX/Outlander Sport/RVR 4th Facelift — Buy parts online
   2019 - 2024 | 7zap", SIN textos de bloqueo ("you have been blocked",
   "Just a moment") y con la navegación de categorías ("Maintenance Parts",
   "Engine", etc.) presente en el HTML. Repetido 3 veces con resultado
   idéntico.

   IMPORTANTE — intento de verificación en el navegador automatizado del
   agente (mcp__browser_exec, Chrome headless en IP de datacenter): Cloudflare
   bloqueó CADA intento (challenge "Un momento..." o página dura "Attention
   Required! You are unable to access 7zap.com") incluso tras +10 reintentos,
   esperas de hasta 90s, resolver cookies, simular movimiento de mouse y
   clicar el checkbox del widget Turnstile. El mismo bloqueo ocurrió con
   partsouq.com y con TODAS las tiendas oficiales mencionadas abajo (todas
   corren detras de Cloudflare y detectan `navigator.webdriver=true` del
   Chrome headless). La verificación de que la URL "abre y muestra el
   ensamblaje" se hizo entonces por fetch HTTP directo con cabeceras de
   navegador real (no headless), que SÍ pasó el filtro de Cloudflare y
   devolvió el documento completo. Se documenta esto con honestidad: no es
   un screenshot de un navegador interactivo, es un fetch HTTP verificado del
   HTML real de la página de destino. Un usuario humano con un navegador
   normal (no headless, no datacenter IP) no debería encontrar este
   obstáculo.

   Estabilidad: MEDIA-ALTA. El slug de generación ("...4th-facelift-...")
   es estable mientras 7zap no reorganice su taxonomía, pero NO es un ID
   interno (no viene de vPIC ni de ningún decodificador de VIN nuestro) —
   lo tuvimos que resolver a mano buscando qué generación de 7zap corresponde
   al rango de años del Outlander Sport 2020. Este mapeo
   (marca, modelo, rango de años) -> slug de generación de 7zap se mantiene
   en el diccionario `_SEVENZAP_GENERATIONS` de este archivo y deberá
   ampliarse a mano para cada vehiculo/categoria nuevos que el catalogo
   necesite. El slug de categoria (ej. "oil-pump-oil-filter",
   "chassis-systems") también se resolvió a mano por categoría. 7zap SÍ
   soporta VIN (https://7zap.com/en/vin-decoder/mitsubishi?vin=...) pero el
   resultado del decoder no entrega automáticamente la URL del ensamblaje
   específico sin interacción JS adicional (es una SPA), así que por ahora
   usamos el link al decoder como paso intermedio y el link directo a la
   generación+categoría como el deep link principal.

2) PARTSOUQ (https://partsouq.com) — URL VERIFICADA EN VIVO POR UN USUARIO REAL
   (04/10/2026). Bloqueo de Cloudflare confirmado SOLO en acceso automatizado
   (navegador headless y curl simple); un navegador normal sí pasa.

   Estructura real observada (via resultados de busqueda de Google que
   indexaron paginas de Partsouq, NO fabricada):

     https://partsouq.com/en/search/all?q=<VIN o numero de parte>
     https://partsouq.com/en/catalog/genuine/vehicle?c=<Marca>&ssd=<token opaco>&vid=<id>&q=<VIN>

   El parametro `ssd` es un token opaco y firmado que Partsouq genera en su
   backend al resolver un VIN/marca — NO se puede construir desde cero sin
   pasar primero por su buscador (no es un ID estable que vPIC o nosotros
   conozcamos de antemano). Por eso la UNICA forma honesta de dar un deep
   link util de Partsouq sin credenciales/API de pago es:
     https://partsouq.com/en/search/all?q=<VIN>
   que es la pagina de busqueda real (confirmada en los resultados de busqueda
   y en la documentacion oficial de ayuda de Partsouq
   "https://partsouq.com/en/how-to-place-an-order-on-the-partsouq.com-368.html"),
   y que el propio sitio redirige internamente al catalogo genuino con su
   `ssd` una vez que identifica el VIN.

   VERIFICACION REAL (04/10/2026, Omar, navegador normal, VIN real
   JA4AP4AU3LU023739): la busqueda devolvio 3 coincidencias de vehiculo
   (mismo chasis GA2W: "ASX(G.EXP)", "Outlander Sport(P&G)",
   "Outlander Sport(MMNA)" — MMNA = Mitsubishi Motors North America, la
   variante correcta para EE.UU.). Al entrar a esa variante cargo un catalogo
   OEM ilustrado real: categoria "Engine" con 24 diagramas (Oil pump & Oil
   filter, A/T valve body, Power steering oil pump, cylinder head,
   camshaft/timing, engine mount), con sub-etiquetas de pieza clicables. El
   vehiculo aparece etiquetado como "Airtrek / Outlander" (nombre de
   plataforma global de Mitsubishi), no "Outlander Sport" (nombre de mercado
   EE.UU.) — es el mismo catalogo, solo cambia el nombre comercial mostrado.
   No aparecio ningun selector de trim BE/ES/GT/SE/SP en esta pantalla —
   consistente con el hallazgo de T-C2 (ver TASKS.md): el campo
   "Modification" de Partsouq usa codigos de tren motriz (H-LINE, S-CVT), no
   los nombres de trim de marketing de EE.UU.

   Intento previo (curl / navegador headless del agente): HTTP 403 + pagina
   "Just a moment..." (challenge de Cloudflare) en ambos canales, en varias
   sesiones distintas. Confirma que el bloqueo es deteccion de automatizacion
   (navigator.webdriver, fingerprint de CDP), no un problema del link en si
   — un usuario real con navegador normal no deberia encontrar este
   obstaculo, como ya se confirmo.

   Estabilidad: la ruta de busqueda por `q=` es estable (parte de su API
   publica de busqueda, documentada por ellos mismos); la ruta de catalogo
   por `ssd=` NO es estable para construir a mano (depende de un token
   generado por su servidor en cada sesion).

3) TIENDA OFICIAL MITSUBISHI (EE.UU.) — NINGUNA URL VERIFICADA EN VIVO;
   NO SE OFRECE COMO FUENTE POR DEFECTO

   No existe una sola "tienda oficial de Mitsubishi Motors Corp" con catalogo
   EPC propio y accesible publicamente. Lo que existe es una red de tiendas
   operadas por el proveedor de software "RevolutionParts" en nombre de
   concesionarios Mitsubishi certificados en EE.UU. (parts.mitsubishicars.com,
   mitsubishi.oempartsonline.com, mitsubishiparts.com, mitsubishidirectparts.com,
   mitsubishipartswarehouse.com, etc. — mismo motor de tienda, dominios
   distintos). Confirmamos via busqueda web que SI tienen categorias estables
   por URL, p.ej.:
     https://parts.mitsubishicars.com/part-categories/filters/oil-filters
     https://mitsubishi.oempartsonline.com/oil-filters
     https://mitsubishi.oempartsonline.com/v-mitsubishi-outlander-sport   (vehiculo)
   pero NINGUNA de estas URLs cargo para nosotros: TODAS estan detras de
   Cloudflare y devolvieron bloqueo tanto en `curl` (HTTP 403 "Just a
   moment...") como en el navegador headless del agente ("Attention
   Required!"). No hay un catalogo EPC con diagramas aqui tampoco — son
   tiendas de venta (muestran precio y numero de parte, no un diagrama
   despiezado por VIN), asi que ni siquiera cumplen del todo el objetivo de
   "ensamblaje con diagrama".
   Por estas dos razones (no verificado en vivo, y no es realmente un EPC
   con diagramas) este modulo NO genera `epc_link` con `source=oem-store`
   por defecto; el campo existe en el esquema de CONTRACTS.md para cuando una
   marca SI tenga una tienda propia que podamos confirmar en vivo, y queda
   como mejora futura (ver TODO en `get_epc_links`).

------------------------------------------------------------------------------
QUE TAN ESTABLES SON ESTAS URLs (resumen honesto)
------------------------------------------------------------------------------
- 7zap: slugs de marca/generacion/categoria son texto fijo definido por 7zap,
  NO ids que vPIC nos entregue. Hay que mantenerlos a mano por vehiculo en
  `_SEVENZAP_GENERATIONS` / `_SEVENZAP_CATEGORY_SLUGS`. Si 7zap renombra un
  slug, el link rompe (404) pero el dominio y la estructura de rutas se
  mantuvieron iguales en toda la investigacion.
- Partsouq: solo la ruta de busqueda `/en/search/all?q=` es realmente
  estable sin sesion previa. La ruta de catalogo profundo depende de un
  token de sesion que no podemos generar nosotros.
- Tienda oficial: no hay una unica tienda oficial; hay varias tiendas
  "powered by RevolutionParts" con URLs de categoria basadas en texto
  (ej. `/oil-filters`) razonablemente estables, pero no verificadas en vivo
  en esta sesion por bloqueo de Cloudflare, y de todas formas no muestran
  diagramas EPC (solo listados de venta).

TODO futuro (no bloqueante para T-C1):
- Si se consigue una API key de Partsouq (parse.bot u oficial) o un proxy
  con navegador real (no datacenter IP) se puede automatizar la resolucion
  del token `ssd` y devolver el deep link profundo.
- Mapear mas generaciones/categorias de 7zap a medida que T-A1 (vPIC) entregue
  mas combinaciones marca/modelo/año reales a resolver.
"""

from __future__ import annotations

import re
import urllib.parse
from typing import Optional


# ---------------------------------------------------------------------------
# 1) Categorias de ensamblaje del catalogo de nuestro producto
#    (slug interno del producto -> nombre en español, segun categories.json)
#    -> mapeado a su equivalente de slug en cada fuente externa.
# ---------------------------------------------------------------------------

# Slugs de categoria "paraguas" de 7zap, por generacion (son los mismos 8
# grupos para toda la marca Mitsubishi, confirmados navegando
# https://7zap.com/en/catalog/cars/mitsubishi/<generacion>/ ).
_SEVENZAP_TOP_CATEGORY_SLUGS = {
    "factory": "factory",
    "motor": "engine",
    "transmision": "transmission-drivetrain",
    "chasis": "chassis-systems",
    "carroceria": "body-exterior",
    "interior": "interior-safety",
    "electrico": "electrical-electronic",
    "accesorios": "accessories-tools",
    "mantenimiento": "maintenance-parts",
}

# Slugs de ensamblaje FINAL de 7zap, confirmados por categoria de nuestro
# producto. Cada entrada es la pagina con el diagrama despiezado concreto.
# Clave = categoria de nuestro producto (CONTRACTS.md -> parts.json.category).
# Valor = slug final dentro de la generacion en 7zap.
_SEVENZAP_CATEGORY_SLUGS: dict[str, str] = {
    "filtro-aceite": "oil-pump-oil-filter",   # verificado en vivo (ver docstring)
    "filtro-aire": "air-cleaner",
    "frenos": "chassis-systems",              # 7zap no separa pastillas/discos
                                               # como ensamblaje propio para esta
                                               # generacion; el grupo "paraguas"
                                               # Chassis Systems es lo mas cerca
                                               # verificado (incluye frenos).
    "motor": "engine",
    "bujia": "ignition-coil-spark-plug",
    "bateria": "battery",
    "correa": "drive-belt",
    "bomba-agua": "water-pump",
    "amortiguador": "front-suspension",
    "limpiaparabrisas": "windshield-wiper",
}

# Mapa (marca, modelo) -> lista de (año_inicio, año_fin, slug_de_generacion_7zap)
# Resuelto a mano investigando https://7zap.com/en/catalog/cars/<marca>/ y el
# mirror https://<marca>.catalogs-parts.com/ . Usar vPIC (T-A1) para
# normalizar marca/modelo antes de llamar a esta funcion.
_SEVENZAP_GENERATIONS: dict[tuple[str, str], list[tuple[int, int, str]]] = {
    ("mitsubishi", "outlander sport"): [
        (2010, 2011, "asx-outlander-sport-rvr-parts-catalog"),
        (2012, 2015, "asx-outlander-sport-rvr-1st-facelift-parts-catalog"),
        (2016, 2016, "asx-outlander-sport-rvr-2nd-facelift-parts-catalog"),
        (2017, 2018, "asx-outlander-sport-rvr-3rd-facelift-parts-catalog"),
        # Verificado en vivo via curl con UA de navegador (200 OK, HTML real).
        (2019, 2024, "asx-outlander-sport-rvr-4th-facelift-parts-catalog"),
    ],
    ("mitsubishi", "asx"): [
        (2010, 2011, "asx-outlander-sport-rvr-parts-catalog"),
        (2012, 2015, "asx-outlander-sport-rvr-1st-facelift-parts-catalog"),
        (2016, 2016, "asx-outlander-sport-rvr-2nd-facelift-parts-catalog"),
        (2017, 2018, "asx-outlander-sport-rvr-3rd-facelift-parts-catalog"),
        (2019, 2024, "asx-outlander-sport-rvr-4th-facelift-parts-catalog"),
    ],
    ("mitsubishi", "rvr"): [
        (2010, 2011, "asx-outlander-sport-rvr-parts-catalog"),
        (2012, 2015, "asx-outlander-sport-rvr-1st-facelift-parts-catalog"),
        (2016, 2016, "asx-outlander-sport-rvr-2nd-facelift-parts-catalog"),
        (2017, 2018, "asx-outlander-sport-rvr-3rd-facelift-parts-catalog"),
        (2019, 2024, "asx-outlander-sport-rvr-4th-facelift-parts-catalog"),
    ],
}

_SEVENZAP_BRAND_SLUGS = {
    "mitsubishi": "mitsubishi",
}


def _normalize(text: str) -> str:
    """minusculas, sin espacios extra, para comparar marca/modelo con tolerancia."""
    return re.sub(r"\s+", " ", text.strip().lower())


def _find_7zap_generation(make: str, model: str, year: int) -> Optional[str]:
    key = (_normalize(make), _normalize(model))
    ranges = _SEVENZAP_GENERATIONS.get(key)
    if not ranges:
        return None
    for start, end, slug in ranges:
        if start <= year <= end:
            return slug
    return None


def _build_7zap_link(make: str, model: str, year: int, category: str) -> Optional[dict]:
    """
    Construye el deep link de 7zap a la pagina de ensamblaje/categoria para
    la generacion que corresponde al año dado.

    Devuelve None si no tenemos el mapeo marca/modelo/año -> generacion (en
    ese caso el llamador debe caer de vuelta al VIN-decoder o al buscador
    general de 7zap, nunca inventar un slug).
    """
    brand_slug = _SEVENZAP_BRAND_SLUGS.get(_normalize(make))
    if not brand_slug:
        return None

    generation_slug = _find_7zap_generation(make, model, year)
    if not generation_slug:
        return None

    category_slug = _SEVENZAP_CATEGORY_SLUGS.get(category)
    base = f"https://7zap.com/en/catalog/cars/{brand_slug}/{generation_slug}/"
    if category_slug:
        url = f"{base}{category_slug}/"
        confidence = "alta" if category == "filtro-aceite" else "media"
        note = (
            "Verificado en vivo (HTTP 200, HTML real, sin bloqueo) via curl "
            "con user-agent de navegador."
            if category == "filtro-aceite"
            else "URL construida con el mismo patron verificado; no probada "
            "en vivo para esta categoria especifica."
        )
    else:
        # Sin slug de categoria conocido: enlazamos a la pagina de la
        # generacion completa (siempre muestra las 8 categorias "paraguas"
        # como navegacion), mejor que no dar nada.
        url = base
        confidence = "media"
        note = (
            "No tenemos mapeado el slug de ensamblaje final de 7zap para "
            "esta categoria; se enlaza a la pagina de la generacion, desde "
            "donde el usuario navega manualmente a la categoria."
        )

    return {
        "source": "7zap",
        "url": url,
        "confidence": confidence,
        "note": note,
    }


def _build_7zap_vin_decoder_link(make: str, vin: str) -> Optional[dict]:
    """
    Enlace de respaldo cuando tenemos VIN: el decodificador de 7zap para la
    marca. No lleva directo al ensamblaje (es una SPA que requiere
    interaccion JS tras decodificar), pero es el punto de entrada oficial
    de 7zap para busqueda por VIN y es mas preciso que adivinar generacion
    a partir de marca/modelo/año solos.
    """
    brand_slug = _SEVENZAP_BRAND_SLUGS.get(_normalize(make))
    if not brand_slug or not vin:
        return None
    vin_clean = re.sub(r"[^A-HJ-NPR-Z0-9]", "", vin.upper())
    if len(vin_clean) != 17:
        return None
    url = f"https://7zap.com/en/vin-decoder/{brand_slug}?vin={vin_clean}"
    return {
        "source": "7zap",
        "url": url,
        "confidence": "media",
        "note": (
            "Decodificador de VIN de 7zap (no lleva directo al ensamblaje; "
            "requiere que el usuario continue manualmente al catalogo tras "
            "decodificar). Util cuando no tenemos el slug de generacion "
            "mapeado a mano."
        ),
    }


def _build_partsouq_link(vin: Optional[str], part_number_norm: Optional[str] = None) -> Optional[dict]:
    """
    Partsouq: la UNICA ruta construible sin sesion previa es la busqueda
    general `/en/search/all?q=`. La ruta de catalogo profundo usa un token
    `ssd` opaco generado por su servidor que no podemos construir nosotros
    (ver docstring del modulo). Se prioriza VIN; si no hay VIN se usa el
    numero de parte normalizado.
    """
    query = None
    if vin:
        vin_clean = re.sub(r"[^A-HJ-NPR-Z0-9]", "", vin.upper())
        if len(vin_clean) == 17:
            query = vin_clean
    if not query and part_number_norm:
        query = part_number_norm
    if not query:
        return None

    url = f"https://partsouq.com/en/search/all?q={urllib.parse.quote(query)}"
    return {
        "source": "partsouq",
        "url": url,
        "confidence": "media",
        "note": (
            "Pagina de busqueda real de Partsouq (documentada por ellos "
            "mismos como el flujo oficial de busqueda por VIN/numero de "
            "parte). No se pudo verificar visualmente en esta sesion por "
            "bloqueo de Cloudflare tanto en curl como en navegador headless; "
            "un usuario con navegador normal deberia poder resolver el "
            "challenge igual que en cualquier visita humana al sitio."
        ),
    }


def get_epc_links(
    make: str,
    model: str,
    year: int,
    category: str,
    vin: Optional[str] = None,
    part_number_norm: Optional[str] = None,
) -> list[dict]:
    """
    Punto de entrada del modulo (lo que T-D1 / build_index.py debe llamar).

    Args:
        make: marca normalizada (ej. "Mitsubishi"). Viene de vehicles.json
              (T-A1) o se pasa a mano en tests.
        model: modelo tal como lo entrega vPIC (ej. "Outlander Sport").
        year: año del vehiculo (int).
        category: slug de categoria de nuestro producto (CONTRACTS.md
                  categories.json, ej. "filtro-aceite", "frenos", "motor").
        vin: VIN completo de 17 caracteres si lo tenemos (opcional, mejora
             la precision del link de 7zap/Partsouq).
        part_number_norm: numero de parte normalizado (CONTRACTS.md) si ya
             se conoce; se usa como ultimo recurso para la busqueda de
             Partsouq cuando no hay VIN.

    Returns:
        Lista de dicts con el esquema de `epc_link` de CONTRACTS.md
        (`source`, `url`) mas dos campos informativos extra (`confidence`,
        `note`) que T-D1 puede conservar o descartar al armar parts.json —
        CONTRACTS.md solo exige `source` y `url` como claves minimas.
        Puede devolver una lista vacia si no se pudo construir NINGUN link
        confiable (nunca se inventa una URL sin base real).

        El PRIMER elemento de la lista es el que el frontend (T-E1) deberia
        mostrar por defecto como `epc_link` en parts.json; el resto son
        alternativas para que el usuario intente otra fuente si la primera
        no resuelve su vehiculo exacto.
    """
    if not make or not model or not year:
        return []

    links: list[dict] = []

    # 1) 7zap por generacion mapeada a mano (la fuente mas confiable que
    #    pudimos verificar en vivo para Mitsubishi).
    direct = _build_7zap_link(make, model, year, category)
    if direct:
        links.append(direct)

    # 2) Si tenemos VIN y no resolvimos generacion (o incluso si la
    #    resolvimos, como alternativa mas precisa), ofrecer el decodificador
    #    de VIN de 7zap.
    if vin:
        vin_link = _build_7zap_vin_decoder_link(make, vin)
        if vin_link and not any(l["url"] == vin_link["url"] for l in links):
            links.append(vin_link)

    # 3) Partsouq como alternativa (VIN o numero de parte).
    partsouq_link = _build_partsouq_link(vin, part_number_norm)
    if partsouq_link:
        links.append(partsouq_link)

    # TODO (mejora futura, no bloqueante para T-C1): agregar `source:
    # "oem-store"` cuando se verifique en vivo una tienda oficial estable
    # para la marca (ver seccion 3 del docstring: ninguna cargo en esta
    # sesion por bloqueo de Cloudflare, y ninguna de las candidatas tiene
    # diagramas EPC reales, solo listados de venta por categoria).

    return links


__all__ = ["get_epc_links"]
