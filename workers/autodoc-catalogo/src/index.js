// workers/autodoc-catalogo/src/index.js
//
// T-B20: el Worker que cataloga POR DEMANDA.
//
// EL PROBLEMA QUE RESUELVE
// Pre-catalogar todos los años de todos los modelos son años de trabajo: el parque dominicano tiene
// 30 años de ancho (hay Corollas del 92 todavía rodando) y cada vehículo cuesta ~60 consultas. Con
// el plan de 20.000 al mes, "catalogarlo todo" no se termina nunca.
//
// LA RESPUESTA
// No catalogar por adelantado lo que no sabemos si alguien va a pedir: catalogar LO QUE PIDEN. Este
// Worker es el que puede hacerlo, porque es el único sitio donde la clave de AUTODOC puede vivir
// sin exponerse (el sitio es estático: si la clave viaja al navegador, cualquiera la lee y consume
// la cuota en un día).
//
// CÓMO FUNCIONA
//   1. El sitio pregunta por un vehículo que NO tiene en su catálogo precalculado.
//   2. El Worker mira su caché (Cloudflare KV). Si lo tiene, lo devuelve al instante y con CERO
//      consultas: el primero paga, los demás no.
//   3. Si no lo tiene, comprueba la CUOTA DEL MES. Si ya se gastó el tope, se niega (mejor decir
//      "vuelve el mes que viene" que dejar la cuenta a cero a mitad de mes).
//   4. Consulta a AUTODOC la cadena completa (fabricante -> modelo -> variante -> categorías ->
//      artículos con especificaciones), guarda el resultado en la caché y lo devuelve.
//
// LA CUOTA ES LO PRIMERO
// Cada consulta cuesta dinero. El contador del mes está en KV y se comprueba ANTES de cualquier
// llamada; el worker también deja de pedir si una respuesta se acerca al tope. Es la misma regla
// del pipeline (PresupuestoAgotado), aplicada al borde.

const HOST = "autodoc-parts-catalog.p.rapidapi.com";
const TIPO_TURISMO = 1; // PC
const LANG = 4; // inglés: los nombres canónicos de TecDoc
const TOPE_MES = 18000; // tope duro; el plan son 20.000
const DIAS_CACHE = 90; // los articleId de TecDoc no cambian: la caché puede ser generosa

// ---------------------------------------------------------------------------
// Utilidades
// ---------------------------------------------------------------------------

function json(cuerpo, estado = 200) {
  return new Response(JSON.stringify(cuerpo), {
    status: estado,
    headers: {
      "content-type": "application/json; charset=utf-8",
      // El sitio es de otro origen (partexact.com): sin esto el navegador no deja leer la respuesta.
      "access-control-allow-origin": "*",
      "cache-control": "no-store",
    },
  });
}

/** minúsculas, sin acentos y sin paréntesis: para comparar nombres de la misma forma que el pipeline. */
export function normalizar(texto) {
  return String(texto || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\(.*?\)/g, " ")
    .replace(/[^a-zA-Z0-9 ]+/g, " ")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

function aNumero(v) {
  const n = parseFloat(String(v == null ? "" : v).replace(",", "."));
  return Number.isFinite(n) ? n : null;
}

/** Cliente con presupuesto: cuenta y se detiene. Nunca imprime la clave. */
function cliente(env, tope) {
  const estado = { consultas: 0 };
  async function pedir(ruta) {
    if (estado.consultas >= tope) throw new Error("tope de consultas alcanzado");
    estado.consultas += 1;
    const r = await fetch(`https://${HOST}${ruta}`, {
      headers: {
        "X-RapidAPI-Key": env.RAPIDAPI_KEY,
        "X-RapidAPI-Host": HOST,
        accept: "application/json",
      },
    });
    if (!r.ok) return null;
    try {
      return await r.json();
    } catch (_e) {
      return null;
    }
  }
  return { pedir, estado };
}

// ---------------------------------------------------------------------------
// Resolución (mismo criterio que pipeline/fetch_autodoc.py, con sus dos trampas ya resueltas)
// ---------------------------------------------------------------------------

async function resolverFabricante(c, nombre) {
  const datos = await c.pedir(`/api/manufacturers/list/type-id/${TIPO_TURISMO}`);
  const lista = (datos && datos.manufacturers) || [];
  const objetivo = String(nombre || "").trim().toUpperCase().replace(/\s+/g, " ");
  // Nivel 1: nombre CRUDO. Importa: normalizar borra los paréntesis, así que "MITSUBISHI",
  // "MITSUBISHI (BJC)" y "MITSUBISHI (GAC)" quedarían iguales y ganaría una empresa conjunta.
  for (const f of lista) {
    if (String(f.manufacturerName || "").trim().toUpperCase().replace(/\s+/g, " ") === objetivo) return f;
  }
  const n = normalizar(nombre);
  const candidatos = lista.filter((f) => {
    const suyo = normalizar(f.manufacturerName);
    return n && suyo && (suyo.includes(n) || n.includes(suyo));
  });
  // Ante la duda, el nombre MÁS CORTO: la marca, no una filial.
  candidatos.sort((a, b) => String(a.manufacturerName).length - String(b.manufacturerName).length);
  return candidatos[0] || null;
}

async function resolverModelo(c, manufacturerId, nombre, anio, pais) {
  const datos = await c.pedir(
    `/api/models/list/type-id/${TIPO_TURISMO}/manufacturer-id/${manufacturerId}` +
      `/lang-id/${LANG}/country-filter-id/${pais}`
  );
  const lista = (datos && datos.models) || [];
  const objetivo = normalizar(nombre).split(" ").filter(Boolean);
  const a = String(anio || "").trim();
  const candidatos = [];
  for (const m of lista) {
    const suyas = normalizar(m.modelName).split(" ").filter(Boolean);
    if (!suyas.length || !objetivo.length) continue;
    // POR PALABRAS, no por trozos: "outlander i" es prefijo de texto de "outlander iii".
    let puntaje = 0;
    if (objetivo.join(" ") === suyas.join(" ")) puntaje = 3;
    else if (suyas.slice(0, objetivo.length).join(" ") === objetivo.join(" ")) puntaje = 2;
    else if (objetivo.every((p) => suyas.includes(p))) puntaje = 1;
    else continue;
    if (a) {
      const desde = String(m.modelYearFrom || "").slice(0, 4);
      const hasta = String(m.modelYearTo || "").slice(0, 4);
      if (desde && a < desde) continue;
      if (hasta && a > hasta) continue;
      puntaje += 1;
    }
    candidatos.push({ puntaje, m });
  }
  if (!candidatos.length) return null;
  // Desempate por generación: la que EMPIEZA más tarde sin pasarse del año (la que existía).
  candidatos.sort((x, y) => {
    if (y.puntaje !== x.puntaje) return y.puntaje - x.puntaje;
    const dx = parseInt(String(x.m.modelYearFrom || "").slice(0, 4), 10) || 0;
    const dy = parseInt(String(y.m.modelYearFrom || "").slice(0, 4), 10) || 0;
    return dy - dx;
  });
  return candidatos[0].m;
}

async function variantesDelModelo(c, modelId, pais) {
  const datos = await c.pedir(
    `/api/types/type-id/${TIPO_TURISMO}/list-vehicles-types/${modelId}/lang-id/${LANG}/country-filter-id/${pais}`
  );
  return (datos && datos.modelTypes) || [];
}

function elegirVariante(variantes, { anio, cilindrada, potencia }) {
  const a = String(anio || "").slice(0, 4);
  const vistas = new Set();
  const candidatos = [];
  for (const v of variantes) {
    const clave = `${v.vehicleId}|${v.engId}`;
    if (vistas.has(clave)) continue;
    vistas.add(clave);
    const desde = String(v.constructionIntervalStart || "").slice(0, 4);
    const hasta = String(v.constructionIntervalEnd || "").slice(0, 4);
    if (a && desde && a < desde) continue;
    if (a && hasta && a > hasta) continue;
    let puntaje = 0;
    const cap = aNumero(v.capacityLt);
    if (cilindrada != null && cap != null) {
      if (Math.abs(cap - cilindrada) < 0.05) puntaje += 3;
      else continue;
    }
    const ps = aNumero(v.powerPs);
    if (potencia != null && ps != null) {
      if (Math.abs(ps - potencia) <= 3) puntaje += 3;
      else if (Math.abs(ps - potencia) <= 12) puntaje += 1;
    }
    candidatos.push({ puntaje, v });
  }
  if (!candidatos.length) return null;
  candidatos.sort((x, y) => y.puntaje - x.puntaje);
  return candidatos[0].v;
}

async function decodificarVin(c, vin) {
  const datos = await c.pedir(`/api/vin/decoder-v5/${encodeURIComponent(vin)}`);
  const bloque = datos && datos["vin-data-2"];
  let info = {};
  try {
    info = JSON.parse((bloque && bloque.content) || "{}");
  } catch (_e) {
    return null;
  }
  if (!info || !info.make) return null;
  return {
    make: info.make,
    model: info.model,
    year: String(info.model_year || ""),
    cilindrada: aNumero(info["displacement_(l)"]),
    potencia: aNumero(info["engine_brake_(hp)_from"]),
    combustible: info["fuel_type_-_primary"] || "",
  };
}

/** La cadena completa: de un vehículo a sus categorías con piezas y números originales. */
async function construir(c, { make, model, year, pais, cilindrada, potencia, combustible }) {
  const f = await resolverFabricante(c, make);
  if (!f) return { error: `no encontramos la marca "${make}"` };
  const m = await resolverModelo(c, f.manufacturerId, model, year, pais);
  if (!m) return { error: `no encontramos el modelo "${model}" de ${year}` };
  const variantes = await variantesDelModelo(c, m.modelId, pais);
  const v = elegirVariante(variantes, { anio: year, cilindrada, potencia });
  if (!v) return { error: `no hay variante que encaje con ${make} ${model} ${year}` };

  return {
    vehiculo: {
      make: f.manufacturerName,
      model: m.modelName,
      year: String(year || ""),
      variante: v.typeEngineName || null,
      vehicleId: v.vehicleId,
      motor: v.engineCodes || null,
      cilindradaLt: v.capacityLt || null,
      potenciaPs: v.powerPs || null,
      combustible: v.fuelType || null,
    },
    piezas: [], // se rellena por el llamador si quiere el detalle (cuesta 1 consulta por categoría)
  };
}

/** Las piezas de las categorías indicadas, con especificaciones y números originales. */
async function piezasDeCategorias(c, vehicleId, categoryIds) {
  const salida = [];
  for (const catId of categoryIds) {
    const datos = await c.pedir(
      `/api/articles/list/type-id/${TIPO_TURISMO}/vehicle-id/${vehicleId}` +
        `/category-id/${catId}/lang-id/${LANG}`
    );
    const arts = (datos && datos.articles) || [];
    const utiles = [];
    for (const a of arts) {
      if (!a.articleNo || !a.supplierName) continue;
      // El detalle trae las especificaciones (posición, medida) y los números originales: es lo
      // que convierte el número en "la pieza exacta". Una consulta por pieza.
      const det = await c.pedir(`/api/articles/details/article-id/${a.articleId}/lang-id/${LANG}`);
      const especificaciones = {};
      for (const x of (det && det.articleAllSpecifications) || []) {
        if (x.criteriaName && x.criteriaValue) especificaciones[x.criteriaName] = String(x.criteriaValue);
      }
      const oem = ((det && det.articleOemNo) || [])
        .filter((o) => o.oemDisplayNo)
        .map((o) => ({ numero: o.oemDisplayNo, marca: o.oemBrand || null }));
      utiles.push({
        numero: a.articleNo,
        marca: a.supplierName,
        pieza: a.articleProductName || null,
        foto: a.s3image || null,
        especificaciones,
        originales: oem,
      });
      if (utiles.length >= 3) break; // tres piezas por categoría: lo justo y exacto
    }
    if (utiles.length) salida.push({ categoryId: catId, articulos: utiles });
  }
  return salida;
}

// ---------------------------------------------------------------------------
// El handler
// ---------------------------------------------------------------------------

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/salud") return json({ ok: true, topeMes: TOPE_MES });
    if (url.pathname !== "/vehiculo") return json({ error: "ruta desconocida" }, 404);

    const q = url.searchParams;
    const vin = (q.get("vin") || "").trim().toUpperCase();
    let make = (q.get("make") || "").trim();
    let model = (q.get("model") || "").trim();
    let year = (q.get("year") || "").trim();
    const pais = parseInt(q.get("pais") || "67", 10) || 67;
    const categorias = (q.get("categorias") || "").split(",").map((x) => x.trim()).filter(Boolean);

    if (!vin && !(make && model && year)) {
      return json({ error: "hace falta el VIN o marca+modelo+año" }, 400);
    }

    const claveCache = `cat:${pais}:${vin || `${normalizar(make)}:${normalizar(model)}:${year}`}`;
    try {
      const guardado = await env.CATALOGO.get(claveCache, "json");
      if (guardado) return json({ fuente: "cache", ...guardado });
    } catch (_e) {
      // Sin caché disponible se sigue: mejor pagar consultas que no dar servicio.
    }

    const mes = new Date().toISOString().slice(0, 7);
    let usadas = 0;
    try {
      usadas = parseInt((await env.CUOTA.get(`mes:${mes}`)) || "0", 10) || 0;
    } catch (_e) {
      usadas = 0;
    }
    if (usadas >= TOPE_MES) {
      return json(
        { error: "cuota de este mes agotada", usadas, tope: TOPE_MES,
          sugerencia: "el catálogo se amplía el mes que viene" },
        503
      );
    }

    const c = cliente(env, TOPE_MES - usadas);
    let decodificado = null;
    try {
      if (vin) {
        decodificado = await decodificarVin(c, vin);
        if (!decodificado) return json({ error: `no pudimos identificar el VIN ${vin}` }, 404);
        make = decodificado.make;
        model = decodificado.model;
        year = decodificado.year;
      }
      const base = await construir(c, {
        make, model, year, pais,
        cilindrada: decodificado && decodificado.cilindrada,
        potencia: decodificado && decodificado.potencia,
        combustible: decodificado && decodificado.combustible,
      });
      if (base.error) {
        await registrarGasto(env, mes, usadas, c.estado.consultas);
        return json({ error: base.error, consultas: c.estado.consultas }, 404);
      }
      const piezas = categorias.length
        ? await piezasDeCategorias(c, base.vehiculo.vehicleId, categorias)
        : [];
      const respuesta = { ...base, piezas, consultas: c.estado.consultas };
      await registrarGasto(env, mes, usadas, c.estado.consultas);
      if (piezas.length) {
        try {
          await env.CATALOGO.put(claveCache, JSON.stringify(respuesta), {
            expirationTtl: DIAS_CACHE * 24 * 60 * 60,
          });
        } catch (_e) {
          // si la caché falla, la respuesta se sirve igual
        }
      }
      return json({ fuente: "autodoc", ...respuesta });
    } catch (e) {
      await registrarGasto(env, mes, usadas, c.estado.consultas);
      return json({ error: String(e.message || e), consultas: c.estado.consultas }, 429);
    }
  },
};

async function registrarGasto(env, mes, antes, usadasAhora) {
  try {
    await env.CUOTA.put(`mes:${mes}`, String(antes + usadasAhora));
  } catch (_e) {
    // el contador es importante, pero no puede tumbar la respuesta
  }
}
