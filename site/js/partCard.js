// site/js/partCard.js
//
// Renderiza la "ficha" de una parte: imagen (o SVG de categoría si no hay
// foto), nombre, marca, equivalencias, epc_link, tabla de fitment (T-E6) y
// ofertas. No hace fetch directo: recibe la parte y funciones ya conectadas
// a dataClient.js por app.js (regla de escalado, CONTRACTS.md).

function formatPrice(offer) {
  if (typeof offer.price !== "number") return "Precio no disponible";
  const currency = offer.currency || "USD";
  return `${offer.price.toFixed(2)} ${currency}`;
}

/**
 * @param {object} part objeto con la forma de data/build/parts.json
 * @param {Array<{slug,name_es,svg}>} categories para resolver el SVG de
 *   respaldo cuando la parte no tiene foto.
 * @param {(id: string) => Promise<object|null>} resolveEquivalent función
 *   para pedir el nombre/número de cada id en equivalents (normalmente
 *   getPart de dataClient.js, inyectada por app.js).
 * @param {() => Promise<Array<object>>} [getAllVehicles] función para
 *   listar TODOS los vehículos del catálogo (normalmente getVehicles de
 *   dataClient.js, inyectada por app.js), usada para resolver
 *   `fitment_ids` -> filas de año/marca/modelo (T-E6). Si se omite y
 *   `fitment_ids` tiene elementos, la tabla no se muestra (degrada en vez
 *   de romper).
 * @returns {Promise<HTMLElement>}
 */
export async function renderPartCard(part, categories, resolveEquivalent, getAllVehicles) {
  const card = document.createElement("article");
  card.className = "part-card";

  const imgWrap = document.createElement("div");
  imgWrap.className = "part-image";
  const img = document.createElement("img");
  if (part.image && part.image.url) {
    img.src = part.image.url;
    img.alt = `Foto de ${part.name}`;
  } else {
    const cat = categories.find((c) => c.slug === part.category);
    const svgFile = cat ? cat.svg : "generico-sin-foto.svg";
    img.src = `./assets/categories/${svgFile}`;
    img.alt = "";
    img.setAttribute("aria-hidden", "true");
  }
  imgWrap.appendChild(img);
  card.appendChild(imgWrap);

  const body = document.createElement("div");
  body.className = "part-body";

  const h3 = document.createElement("h3");
  h3.textContent = part.name;
  body.appendChild(h3);

  const brandLine = document.createElement("p");
  brandLine.className = "part-brand";
  brandLine.textContent = `${part.brand} · N.º de parte: ${part.part_number}${
    part.type ? ` · ${part.type === "OEM" ? "Original (OEM)" : "Aftermarket"}` : ""
  }`;
  body.appendChild(brandLine);

  // --- other_names: sinónimos (T-D2, campo opcional agregado a CONTRACTS.md) ---
  if (Array.isArray(part.other_names) && part.other_names.length > 0) {
    const otherNamesP = document.createElement("p");
    otherNamesP.className = "search-hint";
    otherNamesP.textContent = `También conocida como: ${part.other_names.join(", ")}.`;
    body.appendChild(otherNamesP);
  }

  // --- epc_link: botón claro hacia la fuente del diagrama/número ---
  if (part.epc_link && part.epc_link.url) {
    const epcBox = document.createElement("div");
    epcBox.className = "epc-link-box";
    const epcLink = document.createElement("a");
    epcLink.href = part.epc_link.url;
    epcLink.target = "_blank";
    epcLink.rel = "noopener noreferrer";
    epcLink.className = "btn";
    epcLink.textContent = "Ver diagrama y número en la fuente";
    epcBox.appendChild(epcLink);
    const note = document.createElement("p");
    note.className = "search-hint";
    note.textContent = `Fuente: ${part.epc_link.source || "externa"} (se abre en una pestaña nueva).`;
    epcBox.appendChild(note);
    body.appendChild(epcBox);
  }

  // --- equivalencias ---
  if (Array.isArray(part.equivalents) && part.equivalents.length > 0) {
    const eqTitle = document.createElement("p");
    eqTitle.textContent = "Equivalencias:";
    eqTitle.style.margin = "0.5rem 0 0";
    body.appendChild(eqTitle);

    const eqList = document.createElement("ul");
    eqList.className = "equivalents-list";
    for (const eqId of part.equivalents) {
      const li = document.createElement("li");
      const eqPart = await resolveEquivalent(eqId);
      li.textContent = eqPart
        ? `${eqPart.brand} ${eqPart.part_number} — ${eqPart.name}`
        : `(no encontrado: ${eqId})`;
      eqList.appendChild(li);
    }
    body.appendChild(eqList);
  }

  // --- tabla de fitment (T-E6) ---
  // Si fitment_ids tiene elementos, se resuelve cada id a un vehículo real
  // (vía getAllVehicles, normalmente getVehicles() de dataClient.js) y se
  // muestra una tabla Año/Marca/Modelo — no solo el conteo ni los ids
  // crudos. Si fitment_ids está vacío (o no se puede resolver ningún id),
  // la sección entera se omite: no mostramos una tabla vacía.
  if (Array.isArray(part.fitment_ids) && part.fitment_ids.length > 0) {
    const fitmentSection = await _renderFitmentTable(part.fitment_ids, getAllVehicles);
    if (fitmentSection) body.appendChild(fitmentSection);
  }

  // --- ofertas / precios ---
  const offers = Array.isArray(part.offers) ? part.offers : [];
  if (offers.length > 0) {
    const offersTitle = document.createElement("p");
    offersTitle.textContent = "Ofertas:";
    offersTitle.style.margin = "0.5rem 0 0";
    body.appendChild(offersTitle);

    const offersList = document.createElement("ul");
    offersList.className = "offers-list";

    // Orden por precio ascendente (dirección B). El visitante viene a COMPARAR, y
    // una lista en el orden en que la devuelve la API lo obliga a leerla entera
    // para saber cuál es la más barata; además el precio más bajo es el único que
    // va destacado en verde, así que ese destacado tiene que ser verdad.
    // Se ordena una copia: no se toca el dato del catálogo. Las ofertas sin precio
    // van al final, porque no se pueden comparar con las demás.
    const ofertasOrdenadas = [...offers].sort((a, b) => {
      const precioA = Number(a && a.price);
      const precioB = Number(b && b.price);
      const aTiene = Number.isFinite(precioA);
      const bTiene = Number.isFinite(precioB);
      if (!aTiene && !bTiene) return 0;
      if (!aTiene) return 1;
      if (!bTiene) return -1;
      return precioA - precioB;
    });

    ofertasOrdenadas.forEach((offer) => {
      const li = document.createElement("li");
      li.className = "offer-row";

      const info = document.createElement("span");
      info.innerHTML = "";
      const storeSpan = document.createElement("span");
      storeSpan.textContent = `${offer.store}${offer.condition ? ` · ${offer.condition}` : ""} — `;
      const priceSpan = document.createElement("span");
      priceSpan.className = "offer-price";
      priceSpan.textContent = formatPrice(offer);
      info.appendChild(storeSpan);
      info.appendChild(priceSpan);

      const buyBtn = document.createElement("a");
      buyBtn.href = offer.url;
      buyBtn.target = "_blank";
      buyBtn.rel = "noopener noreferrer";
      buyBtn.className = "btn btn-secondary";
      buyBtn.textContent = `Comprar en ${offer.store}`;

      li.appendChild(info);
      li.appendChild(buyBtn);
      offersList.appendChild(li);
    });
    body.appendChild(offersList);
  } else {
    const noOffers = document.createElement("p");
    noOffers.className = "search-hint";
    noOffers.textContent = "Todavía no hay ofertas registradas para esta pieza.";
    body.appendChild(noOffers);
  }

  card.appendChild(body);
  return card;
}

/**
 * @param {Array<string>} fitmentIds
 * @param {() => Promise<Array<object>>} [getAllVehicles]
 * @returns {Promise<HTMLElement|null>} sección con <table> de Año/Marca/
 *   Modelo, o null si no hay forma de resolver ningún vehículo (sin
 *   función inyectada, o ningún id coincide con el catálogo).
 */
async function _renderFitmentTable(fitmentIds, getAllVehicles) {
  if (typeof getAllVehicles !== "function") {
    // app.js no inyectó getVehicles (p. ej. una llamada vieja a
    // renderPartCard con 3 argumentos): degradamos sin romper, en vez de
    // lanzar. No se muestra conteo ni lista de ids crudos — ver T-E6.
    return null;
  }

  let allVehicles;
  try {
    allVehicles = await getAllVehicles();
  } catch (err) {
    console.warn("partCard: no se pudo cargar getVehicles() para la tabla de fitment", err);
    return null;
  }
  if (!Array.isArray(allVehicles)) return null;

  const byId = new Map(allVehicles.map((v) => [v.id, v]));
  const rows = fitmentIds
    .map((id) => byId.get(id))
    .filter((v) => v && v.year !== undefined && v.make && v.model)
    .sort((a, b) => Number(b.year) - Number(a.year) || a.make.localeCompare(b.make) || a.model.localeCompare(b.model));

  if (rows.length === 0) return null;

  const section = document.createElement("div");
  section.className = "fitment-box";

  const title = document.createElement("p");
  title.textContent = "Esta pieza aplica para:";
  title.style.margin = "0.5rem 0 0.4rem";
  section.appendChild(title);

  const table = document.createElement("table");
  table.className = "fitment-table";

  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  ["Año", "Marca", "Modelo"].forEach((text) => {
    const th = document.createElement("th");
    th.scope = "col";
    th.textContent = text;
    headRow.appendChild(th);
  });
  thead.appendChild(headRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  rows.forEach((v) => {
    const tr = document.createElement("tr");
    [v.year, v.make, v.model].forEach((text) => {
      const td = document.createElement("td");
      td.textContent = String(text);
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);

  section.appendChild(table);
  return section;
}
