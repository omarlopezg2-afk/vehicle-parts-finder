"""pipeline/fetch_autodoc.py — T-B13: el catálogo que SÍ da el número de parte.

QUÉ HACE
    Recorre, para cada vehículo de `data/seed/catalogo.vehiculos.json`, la cadena de la API
    de AUTODOC (TecDoc, vía RapidAPI) hasta las piezas: VIN -> fabricante -> modelo -> variante
    -> categorías -> artículos, y guarda en `data/build/catalogo.json` el número de parte
    (`articleNo`), la marca (`supplierName`), el nombre de la pieza y la foto.

POR QUÉ EXISTE
    Hasta ahora el sitio sabía decir "esta pieza le queda" (fitment de eBay, T-B8) pero no
    "este es el número". La prueba de T-B10 (docs/piloto-tb10-autodoc.md) demostró con datos
    reales que esta API devuelve el número como campo propio y que la referencia cruzada
    OEM <-> aftermarket funciona. Este módulo convierte esa prueba en catálogo.

REGLA DE ORO DE ESTE MÓDULO: EL PRESUPUESTO
    Cada consulta cuesta dinero o cuota. Por eso el cliente HTTP cuenta las llamadas y se
    detiene al llegar a `max_consultas` levantando `PresupuestoAgotado`. El orquestador lo
    captura y marca el resultado como incompleto en vez de gastar a ciegas. Una prueba nunca
    debe poder vaciar la cuota del mes.

DÓNDE VA LA CLAVE
    En el entorno (`RAPIDAPI_KEY`), que en el build viene de los secretos de GitHub Actions.
    NUNCA se imprime, ni se escribe en el archivo de salida, ni se registra en los mensajes.

ENDPOINTS (encadenados y verificados el 07/10/2026)
    GET /api/vin/decoder-v5/{vin}
    GET /api/manufacturers/list/type-id/1
    GET /api/models/list/type-id/1/manufacturer-id/{m}/lang-id/4/country-filter-id/{p}
    GET /api/types/type-id/1/list-vehicles-types/{modelId}/lang-id/4/country-filter-id/{p}
    GET /api/category/type-id/1/products-groups-variant-1/{vehicleId}/lang-id/4
    GET /api/articles/list/type-id/1/vehicle-id/{v}/category-id/{c}/lang-id/4

NUNCA ES FATAL
    Igual que `fetch_fitment.py`: si no hay credenciales o la API falla, el build sigue y el
    sitio simplemente no muestra números. El catálogo es una mejora, no un requisito para
    publicar.
"""
from __future__ import annotations

import json
import json
import re
import signal
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
# OJO CON LA RUTA: vive en su propia carpeta a propósito. `build_index._load_seed_parts` lee
# `data/seed/*.json` (glob no recursivo) esperando listas de PIEZAS; una semilla que es un
# objeto rompía el build entero. El 07/10/2026 lo cazó el propio build, no las pruebas.
SEMILLA = RAIZ / "data" / "seed" / "catalogo" / "vehiculos.json"
SALIDA = RAIZ / "data" / "build" / "catalogo.json"

HOST = "autodoc-parts-catalog.p.rapidapi.com"
LANG = 4        # inglés: son los nombres canónicos de TecDoc; la interfaz los traduce/envuelve
TIPO_TURISMO = 1


class PresupuestoAgotado(RuntimeError):
    """Se levantó la mano antes de gastar la última consulta disponible."""


# --------------------------------------------------------------------------------------
# utilidades de texto y de lectura de respuestas
# --------------------------------------------------------------------------------------

def normalizar(texto: str) -> str:
    """minúsculas, sin acentos, sin paréntesis ni espacios repetidos (para comparar nombres)."""
    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    t = re.sub(r"\(.*?\)", " ", t)
    t = re.sub(r"[^a-z0-9 ]+", " ", t.lower())
    return re.sub(r"\s+", " ", t).strip()


def _a_numero(valor) -> float | None:
    try:
        return float(str(valor).strip())
    except (TypeError, ValueError):
        return None


def _bloque_del_vin(bloque) -> dict:
    """Los bloques del decodificador traen el JSON como TEXTO dentro de `content`."""
    if not isinstance(bloque, dict):
        return {}
    contenido = bloque.get("content")
    if isinstance(contenido, dict):
        return contenido
    if isinstance(contenido, str):
        try:
            return json.loads(contenido)
        except json.JSONDecodeError:
            return {}
    return {}


# --------------------------------------------------------------------------------------
# cliente HTTP con presupuesto
# --------------------------------------------------------------------------------------

class ClienteAutodoc:
    """Cliente mínimo. `fetch` se inyecta en las pruebas para no tocar la red."""

    def __init__(self, clave: str, *, max_consultas: int = 30, fetch=None, pausa: float = 0.2):
        self.clave = clave
        self.max_consultas = int(max_consultas)
        self.consultas = 0
        self.pausa = pausa
        self._fetch = fetch or self._fetch_http

    @staticmethod
    def _fetch_http(url: str, cabeceras: dict, timeout: int = 45) -> tuple[int, str]:
        """Una petición HTTP con DOS frenos.

        El `timeout` de urlopen cubre el caso normal, pero NO basta: la noche del 06/10/2026 el
        bloque de flota se quedó 4 horas y media parado con un socket ESTABLISHED y 0 bytes
        pendientes, sin CPU y sin excepción — el proceso esperando una respuesta que no llegaba y
        que el timeout no cortó. Una alarma del sistema operativo corta cualquier espera, venga de
        donde venga. Nunca lanza: devuelve estado 0 y el que llama decide (saltar y seguir).
        """
        def _cortar(_signum, _frame):
            raise TimeoutError(f"sin respuesta en {timeout}s")

        previo = None
        if hasattr(signal, "SIGALRM"):
            previo = signal.signal(signal.SIGALRM, _cortar)
            signal.alarm(timeout)  # red de seguridad: corta aunque el socket no respete el timeout
        try:
            req = urllib.request.Request(url, headers=cabeceras)
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    return r.status, r.read().decode("utf-8", "replace")
            except urllib.error.HTTPError as e:
                return e.code, e.read().decode("utf-8", "replace")
            except TimeoutError:
                return 0, ""
            except OSError:
                return 0, ""
        finally:
            if previo is not None:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, previo)

    def pedir(self, ruta: str):
        if self.consultas >= self.max_consultas:
            raise PresupuestoAgotado(
                f"tope de {self.max_consultas} consultas alcanzado (no se gasta más)"
            )
        url = f"https://{HOST}{ruta}"
        self.consultas += 1
        estado, cuerpo = self._fetch(
            url,
            {"X-RapidAPI-Key": self.clave, "X-RapidAPI-Host": HOST, "Accept": "application/json"},
        )
        if self.pausa:
            time.sleep(self.pausa)
        if estado != 200:
            print(f"  [autodoc] HTTP {estado} en {ruta}: {cuerpo[:160]}")
            return None
        try:
            return json.loads(cuerpo)
        except json.JSONDecodeError:
            print(f"  [autodoc] respuesta no JSON en {ruta}")
            return None


def clave_del_entorno() -> str:
    """`RAPIDAPI_KEY` del entorno o del `.env` del repo. El valor no se imprime jamás."""
    clave = (os.environ.get("RAPIDAPI_KEY") or "").strip()
    if clave:
        return clave
    env = RAIZ / ".env"
    if env.exists():
        for linea in env.read_text(encoding="utf-8").splitlines():
            if linea.startswith("RAPIDAPI_KEY="):
                return linea.split("=", 1)[1].strip()
    return ""


# --------------------------------------------------------------------------------------
# resolución: de un VIN (o un nombre) a los identificadores de AUTODOC
# --------------------------------------------------------------------------------------

def decodificar_vin(cliente: ClienteAutodoc, vin: str) -> dict | None:
    """La ficha del vehículo según la propia API. Devuelve None si no lo reconoce."""
    datos = cliente.pedir(f"/api/vin/decoder-v5/{urllib.parse.quote(vin)}")
    if not isinstance(datos, dict):
        return None
    info = _bloque_del_vin(datos.get("vin-data-2"))
    if not info:
        return None
    return {
        "vin": vin.upper(),
        "valido": str(info.get("error_text", "")).startswith("0"),
        "make": (info.get("make") or "").strip(),
        "model": (info.get("model") or "").strip(),
        "year": str(info.get("model_year") or "").strip(),
        "cilindrada_l": _a_numero(info.get("displacement_(l)")),
        "potencia_hp": _a_numero(info.get("engine_brake_(hp)_from")),
        "combustible": (info.get("fuel_type_-_primary") or "").strip(),
        "motor": (info.get("engine_model") or "").strip(),
    }


def resolver_fabricante(cliente: ClienteAutodoc, nombre: str, *, cache: dict | None = None):
    """Busca el fabricante por nombre en la lista de AUTODOC (698 fabricantes)."""
    lista = None
    if cache is not None and "fabricantes" in cache:
        lista = cache["fabricantes"]
    if lista is None:
        datos = cliente.pedir(f"/api/manufacturers/list/type-id/{TIPO_TURISMO}")
        lista = (datos or {}).get("manufacturers") if isinstance(datos, dict) else None
        if not isinstance(lista, list):
            return None
        if cache is not None:
            cache["fabricantes"] = lista
    # El primer nivel compara el nombre CRUDO. Importa: `normalizar` borra los paréntesis y su
    # contenido, así que "MITSUBISHI", "MITSUBISHI (BJC)" y "MITSUBISHI (GAC)" quedarían los tres
    # como "mitsubishi" y ganaría el primero de la lista — que es una empresa conjunta, no la
    # marca. Este error lo cazó una prueba el 07/10/2026.
    objetivo_crudo = re.sub(r"\s+", " ", str(nombre or "").strip().upper())
    for f in lista:
        if re.sub(r"\s+", " ", str(f.get("manufacturerName") or "").strip().upper()) == objetivo_crudo:
            return f

    # Segundo nivel: parecido, y ante la duda el nombre MÁS CORTO ("MITSUBISHI" antes que
    # "MITSUBISHI (BJC)"), que es la marca y no una filial o empresa conjunta.
    objetivo = normalizar(nombre)
    candidatos = []
    for f in lista:
        suyo = normalizar(f.get("manufacturerName") or "")
        if objetivo and suyo and (objetivo in suyo or suyo in objetivo):
            candidatos.append((len(suyo), f))
    if candidatos:
        candidatos.sort(key=lambda x: x[0])
        return candidatos[0][1]
    return None


def resolver_modelo(cliente: ClienteAutodoc, manufacturer_id: int, nombre: str, anio, pais: int):
    """Modelo del fabricante que coincide en nombre y cubre el año pedido."""
    datos = cliente.pedir(
        f"/api/models/list/type-id/{TIPO_TURISMO}/manufacturer-id/{manufacturer_id}"
        f"/lang-id/{LANG}/country-filter-id/{pais}"
    )
    lista = (datos or {}).get("models") if isinstance(datos, dict) else None
    if not isinstance(lista, list):
        return None
    objetivo, anio = normalizar(nombre), str(anio or "").strip()
    palabras_obj = objetivo.split()
    candidatos = []
    for m in lista:
        suyo = normalizar(m.get("modelName"))
        palabras_suyas = suyo.split()
        if not palabras_suyas or not palabras_obj:
            continue
        # POR PALABRAS, no por trozos de texto. Con subcadenas, "outlander i" (generación I) es
        # prefijo de "outlander iii" (generación III) y se devolvía la generación equivocada —
        # exactamente el error que convertiría la promesa "esta pieza le queda" en una mentira.
        # Lo cazó una prueba el 07/10/2026.
        if palabras_obj == palabras_suyas:
            puntaje = 3
        elif palabras_suyas[: len(palabras_obj)] == palabras_obj:
            puntaje = 2
        elif set(palabras_obj) <= set(palabras_suyas):
            puntaje = 1
        else:
            continue
        if anio:
            desde = str(m.get("modelYearFrom") or "")[:4]
            hasta = str(m.get("modelYearTo") or "")[:4]
            if desde and anio < desde:
                continue
            if hasta and anio > hasta:      # modelYearTo nulo = sigue en producción
                continue
            puntaje += 1
        candidatos.append((puntaje, m))
    if not candidatos:
        return None
    # DESEMPATE por generación. Varias generaciones se llaman igual ("COROLLA") y TecDoc suele
    # dejar `modelYearTo` VACÍO en las viejas, así que el filtro por año no las descarta: todas
    # empatan y ganaba la primera de la lista — la de 1970. Con eso, "Corolla 2016" devolvía 42
    # variantes de las cuales NINGUNA era de 2016 (lo cazó el piloto de flota del 07/10/2026).
    # Se prefiere la que EMPIEZA más tarde sin pasarse del año pedido: la generación que existía.
    def clave(item):
        m = item[1]
        desde = str(m.get("modelYearFrom") or "")[:4]
        return (-item[0], -(int(desde) if desde.isdigit() else 0))

    candidatos.sort(key=clave)
    return candidatos[0][1]


def resolver_variante(cliente: ClienteAutodoc, model_id: int, pais: int, *,
                      cilindrada_l=None, potencia_hp=None, anio=None, combustible=None):
    """La variante concreta (vehicleId) que corresponde al motor que dice el VIN.

    Esto es lo que el VIN aporta de verdad: sin él habría que elegir a ojo entre las 30
    variantes del modelo. Se prioriza la cilindrada, luego la potencia, y se descarta lo que
    no encaje en el año. Nunca se inventa: si nada encaja, devuelve None.
    """
    datos = cliente.pedir(
        f"/api/types/type-id/{TIPO_TURISMO}/list-vehicles-types/{model_id}"
        f"/lang-id/{LANG}/country-filter-id/{pais}"
    )
    lista = (datos or {}).get("modelTypes") if isinstance(datos, dict) else None
    if not isinstance(lista, list):
        return None

    combustible = normalizar(combustible or "")
    quiere_gasolina = any(p in combustible for p in ("gas", "petrol"))

    vistas, candidatos = set(), []
    for v in lista:
        clave = (v.get("vehicleId"), v.get("engId"))
        if clave in vistas:        # la misma variante puede venir repetida por código de motor
            continue
        vistas.add(clave)
        if quiere_gasolina and "diesel" in normalizar(v.get("fuelType")):
            continue
        anio_v = str(anio or "")[:4]
        desde = str(v.get("constructionIntervalStart") or "")[:4]
        hasta = str(v.get("constructionIntervalEnd") or "")[:4]
        if anio_v and desde and anio_v < desde:
            continue
        if anio_v and hasta and anio_v > hasta:
            continue
        puntaje = 0.0
        cap = _a_numero(v.get("capacityLt"))
        if cilindrada_l is not None and cap is not None:
            if abs(cap - float(cilindrada_l)) < 0.05:
                puntaje += 3
            else:
                continue
        ps = _a_numero(v.get("powerPs"))
        if potencia_hp is not None and ps is not None:
            if abs(ps - float(potencia_hp)) <= 3:
                puntaje += 3
            elif abs(ps - float(potencia_hp)) <= 12:
                puntaje += 1
        candidatos.append((puntaje, v))
    if not candidatos:
        return None
    candidatos.sort(key=lambda x: -x[0])
    return candidatos[0][1]


# --------------------------------------------------------------------------------------
# categorías y artículos
# --------------------------------------------------------------------------------------

def categorias_del_vehiculo(cliente: ClienteAutodoc, vehicle_id: int) -> list[dict]:
    """El árbol de categorías (TecDoc) de ese vehículo. Se queda con los nodos que llevan
    `categoryId2`, que es el nivel que acepta el endpoint de artículos."""
    datos = cliente.pedir(
        f"/api/category/type-id/{TIPO_TURISMO}/products-groups-variant-1/{vehicle_id}/lang-id/{LANG}"
    )
    lista = (datos or {}).get("categories") if isinstance(datos, dict) else None
    if not isinstance(lista, list):
        return []
    out = []
    for c in lista:
        if c.get("categoryId2"):
            nombres = [c.get(f"categoryName{i}") for i in (1, 2, 3, 4) if c.get(f"categoryName{i}")]
            out.append({
                "categoryId": c["categoryId2"],
                "categoriaId1": c.get("categoryId1"),
                "nombre": c.get("categoryName2") or c.get("categoryName1"),
                "ruta": " / ".join(nombres),
            })
    return out


def elegir_categorias(arbol: list[dict], buscadas: list[str], tope: int = 12) -> list[dict]:
    """Las categorías que de verdad busca la gente, en el orden en que importan.

    Se compara por texto normalizado, así que no depende de ids fijos de TecDoc (que cambian
    entre vehículos y mercados). `tope` existe porque cada categoría es una consulta.

    Entre varias coincidencias se queda con la MÁS PROFUNDA (la ruta más larga), no con la
    primera. Cazado el 07/10/2026 con datos reales: "control arm" enganchó la rama
    "Body Parts/Wing/Bumper" y trajo sensores de aparcamiento — piezas que sí son de ese
    vehículo, pero no lo que el visitante pidió. Es mejor no mostrar nada que mostrar otra cosa.
    """
    elegidas, vistos = [], set()
    for fragmento in buscadas:
        f = normalizar(fragmento)
        if not f:
            continue
        candidatos = []
        for nodo in arbol:
            if nodo["categoryId"] in vistos:
                continue
            texto = normalizar(nodo.get("ruta") or nodo.get("nombre"))
            if f in texto:
                candidatos.append((len(nodo.get("ruta") or ""), nodo))
        if candidatos:
            candidatos.sort(key=lambda x: -x[0])          # la ruta más larga = la más específica
            nodo = candidatos[0][1]
            elegidas.append({**nodo, "buscado": fragmento})
            vistos.add(nodo["categoryId"])
        if len(elegidas) >= tope:
            break
    return elegidas


def oem_del_vehiculo(cliente: ClienteAutodoc, vehicle_id: int, producto: str) -> list[dict]:
    """Los números ORIGINALES del fabricante para ese vehículo y ese grupo de producto.

    Esto es el equivalente al catálogo oficial del concesionario (el EPC): *"para TU coche, la
    pastilla de freno original es MN102628"*. Es la capa que faltaba: la lista de piezas por
    categoría traía 75 marcas distintas (un volcado de marcas, como señaló el usuario el
    07/10/2026), mientras que aquí salen unos pocos números **del fabricante** para ese vehículo
    exacto.

    Verificado el 07/10/2026 con su Outlander Sport: una sola consulta devuelve los "Brake Pad Set,
    disc brake" y los "Accessory Kit, disc brake pad" originales de Mitsubishi. Una consulta por
    producto y vehículo: mucho más barato que pedir el detalle de 75 artículos.

    OJO: la respuesta NO trae `articleId`, así que los equivalentes aftermarket se piden aparte,
    por número original (ver `equivalentes_de_oem`).
    """
    datos = cliente.pedir(
        f"/api/articles-oem/selecting-oem-parts-vehicle-modification-description-product-group"
        f"/type-id/{TIPO_TURISMO}/vehicle-id/{vehicle_id}/lang-id/{LANG}"
        f"/search-param/{urllib.parse.quote(producto)}"
    )
    lista = datos if isinstance(datos, list) else ((datos or {}).get("articles") if isinstance(datos, dict) else None)
    if not isinstance(lista, list):
        return []
    salida, vistos = [], set()
    for item in lista:
        numero = str(item.get("articleOemNo") or "").strip()
        nombre = str(item.get("articleProductName") or "").strip()
        if not numero:
            continue
        clave = f"{numero}|{nombre}".upper()
        if clave in vistos:
            continue
        vistos.add(clave)
        salida.append({"numero": numero, "pieza": nombre})
    return salida


def equivalentes_de_oem(cliente: ClienteAutodoc, oem_numero: str) -> list[dict]:
    """Las piezas de otras marcas que equivalen a ese número original (y los demás OEM que sirven).

    Verificado con el filtro de aceite del Corolla (04152YZZA1 -> 20-50517-SX de STELLOX, más los
    otros OEM de Toyota y Daihatsu). Esto es lo que el concesionario no te da: la alternativa de
    otra marca para el MISMO número original, a otro precio.
    """
    datos = cliente.pedir(
        f"/api/articles-oem/search-all-equal-oem-no/lang-id/{LANG}"
        f"/article-oem-no/{urllib.parse.quote(oem_numero)}"
    )
    lista = datos if isinstance(datos, list) else None
    if not isinstance(lista, list):
        return []
    salida = []
    for item in lista:
        numero = str(item.get("articleNo") or "").strip()
        if not numero:
            continue
        salida.append({
            "numero": numero,
            "articleId": item.get("articleId"),
            "articleSearchNo": item.get("articleSearchNo") or None,
            "oemEquivalentes": [o.get("oemDisplayNo") for o in (item.get("oemNo") or []) if o.get("oemDisplayNo")],
        })
    return salida


def detalles_de_articulo(cliente: ClienteAutodoc, article_id) -> dict:
    """Las especificaciones de UNA pieza: posición, medidas, material... y sus números originales.

    Es la capa que convierte una lista de marcas en *"esta es la de delante, 16 disc"*. La respuesta
    trae `articleAllSpecifications` (nombre + valor de cada criterio) y `articleOemNo` (los números
    originales que le corresponden) en la MISMA consulta.

    Como los `articleId` de TecDoc son globales, el resultado se puede cachear y reutilizar entre
    vehículos: el coste no crece con la flota.
    """
    datos = cliente.pedir(f"/api/articles/details/article-id/{article_id}/lang-id/{LANG}")
    if not isinstance(datos, dict) or not datos.get("article"):
        return {}
    art = datos["article"]
    especificaciones = {}
    for c in datos.get("articleAllSpecifications") or []:
        nombre, valor = c.get("criteriaName"), c.get("criteriaValue")
        if nombre and valor:
            especificaciones[str(nombre)] = str(valor)
    oem = []
    for o in (datos.get("articleOemNo") or []):
        numero, marca = o.get("oemDisplayNo"), o.get("oemBrand")
        if numero:
            oem.append({"numero": numero, "marca": marca})
    return {
        "articleId": art.get("articleId"),
        "numero": art.get("articleNo"),
        "marca": art.get("supplierName"),
        "pieza": art.get("articleProductName"),
        "especificaciones": especificaciones,
        "oem": oem,
    }


def articulos_de_categoria(cliente: ClienteAutodoc, vehicle_id: int, category_id) -> list[dict]:
    """Las piezas de esa categoría para ese vehículo, con su número de parte."""
    datos = cliente.pedir(
        f"/api/articles/list/type-id/{TIPO_TURISMO}/vehicle-id/{vehicle_id}"
        f"/category-id/{category_id}/lang-id/{LANG}"
    )
    lista = (datos or {}).get("articles") if isinstance(datos, dict) else None
    if not isinstance(lista, list):
        return []
    out = []
    for a in lista:
        nombre = (a.get("articleProductName") or "").strip()
        marca = (a.get("supplierName") or "").strip()
        numero = (a.get("articleNo") or "").strip()
        if not numero or not marca:      # sin número o sin marca no sirve para nada
            continue
        out.append({
            "numero": numero,
            "marca": marca,
            "pieza": nombre,
            "articleId": a.get("articleId"),
            "foto": a.get("s3image") or None,
            "tipoFoto": a.get("articleMediaType") or None,
        })
    return out


# --------------------------------------------------------------------------------------
# orquestador
# --------------------------------------------------------------------------------------

def expandir_flota(semilla: dict, cliente: ClienteAutodoc, cache: dict | None = None) -> list[dict]:
    """Convierte una FLOTA (marca + modelo + años) en vehículos concretos, uno por variante.

    POR QUÉ POR VARIANTE: un "Corolla 2016" tiene varios motores y **las pastillas no son las
    mismas** para cada uno. Si el catálogo se guardara por modelo-año, el sitio volvería a mostrar
    una mezcla — justo lo que el usuario rechazó con razón el 07/10/2026 ("eso no es exactitud").
    La variante es la unidad mínima que garantiza que la pieza le queda.

    Resuelve los identificadores de AUTODOC una vez por modelo (fabricante, modelo y sus variantes)
    y no necesita VIN: por eso sirve para catalogar la flota de un país, donde no tenemos el VIN de
    cada coche. Los identificadores quedan escritos en la entrada, así que el resto del recorrido
    no gasta ni una consulta más en resolverlos.
    """
    cache = cache if cache is not None else {}
    pais = int(semilla.get("pais") or 261)
    tope = int(semilla.get("variantes_por_modelo_anio") or 2)
    salida = []

    for bloque in semilla.get("flota", []):
        make, model = (bloque.get("make") or "").strip(), (bloque.get("model") or "").strip()
        if not make or not model:
            continue
        print(f"\n[flota] {make} {model}: {bloque.get('years')}")
        f = resolver_fabricante(cliente, make, cache=cache)
        if not f or not f.get("manufacturerId"):
            print(f"  [!] fabricante no encontrado: {make}")
            continue
        for anio in bloque.get("years", []):
            m = resolver_modelo(cliente, int(f["manufacturerId"]), model, str(anio), pais)
            if not m or not m.get("modelId"):
                print(f"  [!] {anio}: modelo no encontrado")
                continue
            datos = cliente.pedir(
                f"/api/types/type-id/{TIPO_TURISMO}/list-vehicles-types/{int(m['modelId'])}"
                f"/lang-id/{LANG}/country-filter-id/{pais}"
            )
            variantes = (datos or {}).get("modelTypes") if isinstance(datos, dict) else None
            if not isinstance(variantes, list):
                print(f"  [!] {anio}: sin variantes")
                continue
            vistas, elegidas = set(), []
            for v in variantes:
                anio_v, desde = str(anio), str(v.get("constructionIntervalStart") or "")[:4]
                hasta = str(v.get("constructionIntervalEnd") or "")[:4]
                if desde and anio_v < desde:
                    continue
                if hasta and anio_v > hasta:
                    continue
                if v.get("vehicleId") in vistas:
                    continue
                vistas.add(v.get("vehicleId"))
                elegidas.append(v)
            elegidas = elegidas[:tope]
            print(f"  {anio}: {len(variantes)} variantes en el catálogo, {len(elegidas)} elegidas"
                  f" -> {[v.get('typeEngineName') for v in elegidas]}")
            for v in elegidas:
                salida.append({
                    "etiqueta": f"{make} {model} {anio} {v.get('typeEngineName') or ''}".strip(),
                    "autodoc": {
                        "manufacturerId": int(f["manufacturerId"]),
                        "modelId": int(m["modelId"]),
                        "vehicleId": int(v["vehicleId"]),
                        "_variante": v.get("typeEngineName"),
                    },
                    "_anio": anio,
                })
    return salida


def construir(semilla: dict, cliente: ClienteAutodoc, *, solo: str | None = None,
              solo_oem: bool = False, cache_detalles: dict | None = None) -> dict:
    """Recorre los vehículos de la semilla. Nunca levanta por un vehículo que falle: lo anota.

    `solo_oem` salta el volcado de categorías y pide únicamente los números ORIGINALES: sirve para
    completar el catálogo de un vehículo que ya tiene sus categorías, gastando solo 1 consulta por
    producto en vez de una por categoría.
    """
    pais = int(semilla.get("pais") or 261)
    buscadas = semilla.get("categorias_buscadas") or []
    cache: dict = {}
    salida = {
        "generado_en": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "fuente": "AUTODOC Parts Catalog (TecDoc) vía RapidAPI",
        "pais_filtro": pais,
        "incompleto": False,
        "consultas": 0,
        "vehiculos": [],
    }

    # La flota se expande ANTES de recorrer: cada variante es un vehículo con sus identificadores
    # ya resueltos, así que el recorrido de abajo no necesita VIN ni gasta consultas resolviendo.
    vehiculos = list(semilla.get("vehiculos", []))
    if semilla.get("flota"):
        try:
            vehiculos += expandir_flota(semilla, cliente, cache)
        except PresupuestoAgotado as e:
            print(f"  [!] {e}: la flota quedó a medias")

    for v in vehiculos:
        etiqueta = v.get("etiqueta") or v.get("vin") or "?"
        if solo and normalizar(solo) not in normalizar(etiqueta):
            continue
        print(f"\n=== {etiqueta} ===")
        registro = {"etiqueta": etiqueta, "vin": v.get("vin"), "avisos": [], "categorias": []}
        try:
            dec = decodificar_vin(cliente, v["vin"]) if v.get("vin") else None
            if dec:
                registro["vehiculo"] = {k: dec[k] for k in
                                        ("make", "model", "year", "cilindrada_l", "potencia_hp",
                                         "combustible", "motor", "valido")}
                print(f"  VIN -> {dec['make']} {dec['model']} {dec['year']} "
                      f"({dec['cilindrada_l']} L, {dec['potencia_hp']} HP)")
            ids = dict(v.get("autodoc") or {})
            if ids.get("_variante") and not dec:
                # viene de la flota: los nombres ya se conocieron al expandir
                ids["_modelo"] = ids.get("_modelo") or None
            fab_id = int(ids["manufacturerId"]) if ids.get("manufacturerId") else None
            if fab_id is None and dec:
                f = resolver_fabricante(cliente, dec["make"], cache=cache)
                if f and f.get("manufacturerId"):
                    fab_id = int(f["manufacturerId"])
                    ids["_fabricante"] = f.get("manufacturerName")
            if fab_id is not None:
                ids["manufacturerId"] = fab_id

            mod_id = int(ids["modelId"]) if ids.get("modelId") else None
            if mod_id is None and dec and fab_id is not None:
                m = resolver_modelo(cliente, fab_id, dec["model"], dec["year"], pais)
                if m and m.get("modelId"):
                    mod_id = int(m["modelId"])
                    ids["_modelo"] = m.get("modelName")
            if mod_id is not None:
                ids["modelId"] = mod_id

            var_id = int(ids["vehicleId"]) if ids.get("vehicleId") else None
            if var_id is None and dec and mod_id is not None:
                var = resolver_variante(
                    cliente, mod_id, pais,
                    cilindrada_l=dec.get("cilindrada_l"), potencia_hp=dec.get("potencia_hp"),
                    anio=dec.get("year"), combustible=dec.get("combustible"),
                )
                if var and var.get("vehicleId"):
                    var_id = int(var["vehicleId"])
                    ids["_variante"] = var.get("typeEngineName")
            if var_id is not None:
                ids["vehicleId"] = var_id
            registro["autodoc"] = {k: val for k, val in ids.items() if not k.startswith("_")}
            registro["nombres"] = {k.lstrip("_"): val for k, val in ids.items() if k.startswith("_")}
            print(f"  catálogo -> fabricante {ids.get('manufacturerId')}, modelo {ids.get('modelId')}, "
                  f"variante {ids.get('vehicleId')} ({ids.get('_variante')})")

            if var_id is None:
                registro["avisos"].append("no se pudo resolver la variante en AUTODOC")
                salida["vehiculos"].append(registro)
                continue

            # ORDEN A PROPÓSITO: primero los números ORIGINALES (T-B16) y después el volcado de
            # categorías. Si el presupuesto se agota a mitad, lo que se pierde es la lista larga de
            # marcas, no el número del fabricante, que es el dato que el visitante necesita.
            productos_oem = semilla.get("productos_oem") or []
            cuantos_eq = int(semilla.get("equivalentes_por_producto") or 0)
            if productos_oem:
                registro["oem"] = []
                for producto in productos_oem:
                    oems = oem_del_vehiculo(cliente, var_id, producto)
                    if not oems:
                        continue
                    for o in oems[:cuantos_eq]:
                        o["equivalentes"] = equivalentes_de_oem(cliente, o["numero"])
                    registro["oem"].append({"buscado": producto, "numeros": oems})
                    print(f"    ORIGINALES {producto:<14} {len(oems):>3} números del fabricante"
                          + (f" (+ equivalentes de {min(cuantos_eq, len(oems))})" if cuantos_eq else ""))

            if not solo_oem:
                arbol = categorias_del_vehiculo(cliente, var_id)
                elegidas = elegir_categorias(arbol, buscadas, tope=int(semilla.get("max_categorias", 10)))
                print(f"  categorías: {len(arbol)} en el árbol, {len(elegidas)} elegidas")
                cuantos_det = int(semilla.get("detalles_por_categoria") or 0)
                for cat in elegidas:
                    arts = articulos_de_categoria(cliente, var_id, cat["categoryId"])
                    # T-B16: las especificaciones (posición, medida, tipo) y los números originales
                    # de cada pieza. Es lo que convierte "75 marcas" en "esta es la de delante,
                    # 302 mm". Se piden SOLO las primeras (`detalles_por_categoria`) porque cada una
                    # es una consulta, y NUNCA se vuelven a pedir: `cache_detalles` viene del
                    # catálogo anterior (los articleId de TecDoc son globales y no cambian).
                    if cuantos_det:
                        cache_detalles = cache_detalles if cache_detalles is not None else {}
                        hechos = 0
                        for art in arts:
                            if hechos >= cuantos_det:
                                break
                            aid = art.get("articleId")
                            if not aid:
                                continue
                            guardado = cache_detalles.get(str(aid))
                            if guardado:
                                art["especificaciones"] = guardado.get("especificaciones") or {}
                                art["oem"] = guardado.get("oem") or []
                                continue
                            det = detalles_de_articulo(cliente, aid)
                            if det:
                                art["especificaciones"] = det.get("especificaciones") or {}
                                art["oem"] = det.get("oem") or []
                                hechos += 1
                    print(f"    - {cat['nombre']:<28} {len(arts):>3} piezas con número"
                          + (f" ({sum(1 for a in arts if a.get('especificaciones'))} con especificaciones)" if cuantos_det else ""))
                    registro["categorias"].append({
                        "nombre": cat["nombre"], "ruta": cat["ruta"],
                        "buscado": cat.get("buscado"), "categoryId": cat["categoryId"],
                        "articulos": arts,
                    })
                registro["categorias"] = [c for c in registro["categorias"] if c["articulos"]]
        except PresupuestoAgotado as e:
            print(f"  [!] {e}: se detiene aquí y se marca el resultado como incompleto")
            registro["avisos"].append(str(e))
            salida["incompleto"] = True
            salida["vehiculos"].append(registro)
            break
        except Exception as e:                      # nunca fatal (ver cabecera)
            print(f"  [!] fallo inesperado: {type(e).__name__}: {e}")
            registro["avisos"].append(f"{type(e).__name__}: {e}")
        salida["vehiculos"].append(registro)

    salida["consultas"] = cliente.consultas
    return salida


def fusionar(previo: dict, nuevo: dict) -> dict:
    """Une un recorrido parcial sobre el catálogo que ya existe, vehículo por vehículo.

    Existe por un motivo concreto: `--solo-oem` NO vuelve a pedir las categorías (que son la parte
    cara), así que su resultado viene sin ellas. Si se escribiera tal cual, se perderían las piezas
    ya guardadas. El 07/10/2026 un build parcial sobreescribió `parts.json` y se perdió el build
    real (lo cazó el CI); esto es para que no vuelva a pasar con el catálogo.

    Regla: lo que trae el recorrido nuevo manda; lo que no trae, se conserva del anterior.
    """
    if not previo or not previo.get("vehiculos"):
        return nuevo

    por_clave = {}
    for v in previo["vehiculos"]:
        for clave in (v.get("vin"), v.get("etiqueta")):
            if clave:
                por_clave[clave] = v

    for v in nuevo.get("vehiculos", []):
        anterior = None
        for clave in (v.get("vin"), v.get("etiqueta")):
            if clave and clave in por_clave:
                anterior = por_clave[clave]
                break
        if not anterior:
            continue
        # lo nuevo manda; lo que no vino esta vez, se conserva
        for campo in ("vehiculo", "autodoc", "nombres"):
            if not v.get(campo) and anterior.get(campo):
                v[campo] = anterior[campo]
        if not v.get("categorias") and anterior.get("categorias"):
            v["categorias"] = anterior["categorias"]
            v["avisos"] = list(dict.fromkeys((v.get("avisos") or []) + (anterior.get("avisos") or [])))

    # los vehículos que no se recorrieron esta vez se quedan como estaban
    claves_nuevas = {v.get("vin") or v.get("etiqueta") for v in nuevo["vehiculos"]}
    for v in previo["vehiculos"]:
        if (v.get("vin") or v.get("etiqueta")) not in claves_nuevas:
            nuevo["vehiculos"].append(v)

    nuevo["consultas"] = int(nuevo.get("consultas") or 0) + int(previo.get("consultas") or 0)
    nuevo["fusionado_con"] = previo.get("generado_en")
    return nuevo


def guardar(resultado: dict, ruta: Path | None = None) -> Path:
    """Escribe el catálogo. Va aparte del CLI para poder reusarlo desde build_index.py."""
    destino = ruta or SALIDA
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(resultado, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return destino


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    solo = None
    tope_cli = None
    solo_oem = "--solo-oem" in argv
    for i, a in enumerate(argv):
        if a == "--solo" and i + 1 < len(argv):
            solo = argv[i + 1]
        if a == "--max-consultas" and i + 1 < len(argv):
            tope_cli = int(argv[i + 1])

    clave = clave_del_entorno()
    if not clave:
        print("[autodoc] sin RAPIDAPI_KEY: se omite (el catálogo no es requisito para publicar)")
        return 0
    if not SEMILLA.exists():
        print(f"[autodoc] no hay semilla en {SEMILLA}")
        return 0

    semilla = json.loads(SEMILLA.read_text(encoding="utf-8"))
    tope = tope_cli or int(semilla.get("max_consultas") or 30)
    cliente = ClienteAutodoc(clave, max_consultas=tope)
    # El catálogo anterior también es el CACHÉ de especificaciones: los articleId de TecDoc son
    # globales, así que lo que ya se pidió una vez no se vuelve a pedir nunca. El coste por vehículo
    # baja solo con el tiempo en vez de crecer con la flota.
    cache_detalles = {}
    previo = None
    if SALIDA.exists():
        try:
            previo = json.loads(SALIDA.read_text(encoding="utf-8"))
            for v in previo.get("vehiculos", []):
                for cat in v.get("categorias", []):
                    for art in cat.get("articulos", []):
                        if art.get("articleId") and art.get("especificaciones"):
                            cache_detalles[str(art["articleId"])] = {
                                "especificaciones": art["especificaciones"], "oem": art.get("oem") or [],
                            }
            if cache_detalles:
                print(f"[autodoc] caché de especificaciones: {len(cache_detalles)} artículos ya conocidos (0 consultas)")
        except (OSError, json.JSONDecodeError):
            previo = None

    resultado = construir(semilla, cliente, solo=solo, solo_oem=solo_oem,
                          cache_detalles=cache_detalles)

    # Un recorrido parcial no puede borrar lo que ya estaba: se fusiona.
    if previo:
        try:
            resultado = fusionar(previo, resultado)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[autodoc] aviso: no se pudo leer el catálogo previo para fusionar ({exc})")

    guardar(resultado)
    con_piezas = sum(1 for v in resultado["vehiculos"] for c in v["categorias"] if c["articulos"])
    total_piezas = sum(len(c["articulos"]) for v in resultado["vehiculos"] for c in v["categorias"])
    print(f"\n[autodoc] OK: {len(resultado['vehiculos'])} vehículo(s), {con_piezas} categorías con "
          f"piezas, {total_piezas} piezas, {resultado['consultas']} consultas"
          + (" (INCOMPLETO: se agotó el presupuesto)" if resultado["incompleto"] else "")
          + f" -> {SALIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
