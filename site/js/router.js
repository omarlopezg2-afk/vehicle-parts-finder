// site/js/router.js
//
// Router por hash: el estado de la vista vive en la URL.
//
// POR QUÉ EXISTE (T-E5): alguien probó el sitio, buscó una pieza, pulsó "atrás"
// y volvió al inicio: las vistas (número de parte, categoría, árbol del vehículo,
// VIN) se pintaban encima del mismo documento SIN dejar entrada en el historial,
// así que el botón atrás no tenía a dónde volver. Además, sin URL propia ninguna
// pieza se podía compartir.
//
// CÓMO SE USA: la app llama a `navegar(...)` SOLO en los puntos donde el usuario
// actúa (enviar el buscador, elegir vehículo, clic en una categoría, clic en el
// árbol, breadcrumb, "cambiar vehículo"). Al restaurar una vista NO se llama a
// `navegar`, así que restaurar nunca ensucia el historial ni provoca bucles.
//
// Rutas canónicas:
//   #/                                   inicio
//   #/numero/<n>                         búsqueda por número de parte
//   #/categoria/<slug>                   categoría (todo el catálogo)
//   #/vehiculo/<marca>/<modelo>/<año>    árbol de categorías del vehículo
//   #/vehiculo/<marca>/<modelo>/<año>/<slug>   categoría dentro del vehículo
//   #/vehiculo/<marca>/<modelo>/<año>/<slug>/<variante>   categoría con el motor ya elegido
//   #/vin/<vin>                          vehículo resuelto por VIN
//
// El último tramo (T-B25) es la VARIANTE elegida: sin él, recargar la página volvería a preguntar el
// motor (o, peor, a elegir uno por su cuenta) y el enlace que alguien comparte no diría de qué motor
// es el número. El estado del sitio vive en la URL, también esta parte.

const INICIO = "#/";

function codificar(valor) {
  return encodeURIComponent(String(valor ?? "").trim());
}

/** Convierte el hash de la URL en un estado de vista. Nunca lanza: lo que no
 *  reconoce o está incompleto se trata como "inicio". */
export function estadoDesdeHash(hash) {
  const limpio = String(hash ?? "").replace(/^#/, "").replace(/^\/+/, "");
  const partes = limpio.split("/").filter(Boolean).map((p) => {
    try {
      return decodeURIComponent(p);
    } catch {
      return p; // un porcentaje mal formado no debe romper la app
    }
  });

  if (partes.length === 0) return { vista: "inicio" };
  const [tipo, ...resto] = partes;

  if (tipo === "numero" && resto[0]) return { vista: "numero", numero: resto[0] };
  if (tipo === "categoria" && resto[0]) return { vista: "categoria", categoria: resto[0] };
  if (tipo === "vin" && resto[0]) return { vista: "vin", vin: resto[0] };
  if (tipo === "vehiculo" && resto.length >= 3) {
    const [make, model, year, categoria, variante] = resto;
    const estado = { vista: "vehiculo", make, model, year };
    if (categoria) estado.categoria = categoria;
    if (categoria && variante) estado.variante = variante;
    return estado;
  }
  return { vista: "inicio" };
}

/** Convierte un estado de vista en su hash canónico. */
export function hashDesdeEstado(estado) {
  switch (estado?.vista) {
    case "numero":
      return estado.numero ? `#/numero/${codificar(estado.numero)}` : INICIO;
    case "categoria":
      return estado.categoria ? `#/categoria/${codificar(estado.categoria)}` : INICIO;
    case "vin":
      return estado.vin ? `#/vin/${codificar(estado.vin)}` : INICIO;
    case "vehiculo": {
      if (!estado.make || !estado.model || !estado.year) return INICIO;
      const base = `#/vehiculo/${codificar(estado.make)}/${codificar(estado.model)}/${codificar(estado.year)}`;
      if (!estado.categoria) return base;
      const conCategoria = `${base}/${codificar(estado.categoria)}`;
      // La variante solo tiene sentido detrás de una categoría (es dentro de la categoría donde se
      // pregunta el motor); sin categoría no se escribe, para no inventar un tramo vacío.
      return estado.variante ? `${conCategoria}/${codificar(estado.variante)}` : conCategoria;
    }
    default:
      return INICIO;
  }
}

// Último hash ya atendido: popstate y hashchange pueden dispararse juntos por el
// mismo cambio (atrás/adelante), y no queremos renderizar dos veces.
let ultimoHashAtendido = null;

// Aviso de que la vista cambió. Existe para que la app ajuste el aspecto (por
// ejemplo recoger la portada cuando hay resultados) sin tener que acordarse de
// llamar en los seis puntos donde se navega: se registra una vez y ya.
let _alNavegar = null;

/** Registra `fn(estado)` para que se llame en cada navegación. */
export function alNavegar(fn) {
  _alNavegar = fn;
}

/** Escribe la vista en la URL. `reemplazar` evita dejar entrada nueva (por
 *  ejemplo al corregir la URL tras una búsqueda fallida). No dispara render:
 *  el hash se marca como atendido para que los eventos no vuelvan a pintarlo. */
export function navegar(estado, { reemplazar = false } = {}) {
  const destino = hashDesdeEstado(estado);
  if (window.location.hash === destino) {
    ultimoHashAtendido = destino;
    return;
  }
  if (reemplazar) window.history.replaceState(null, "", destino);
  else window.history.pushState(null, "", destino);
  ultimoHashAtendido = destino;
  if (_alNavegar) _alNavegar(estado);
}

/** Estado actual según la URL. */
export function rutaActual() {
  return estadoDesdeHash(window.location.hash);
}

/** Llama a `callback(estado)` cuando el usuario navega con atrás/adelante o
 *  edita el hash a mano. Devuelve la función que atiende, por si hace falta
 *  soltarla. */
export function alCambiarRuta(callback) {
  const atender = () => {
    if (window.location.hash === ultimoHashAtendido) return;
    ultimoHashAtendido = window.location.hash;
    callback(estadoDesdeHash(window.location.hash));
  };
  window.addEventListener("popstate", atender);
  window.addEventListener("hashchange", atender);
  return atender;
}
