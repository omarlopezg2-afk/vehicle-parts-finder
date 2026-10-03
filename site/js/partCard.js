// site/js/partCard.js
//
// Renderiza la "ficha" de una parte: imagen (o SVG de categoría si no hay
// foto), nombre, marca, equivalencias, epc_link y ofertas. No hace fetch:
// recibe la parte y la lista de categorías ya cargadas por app.js.

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
 * @returns {Promise<HTMLElement>}
 */
export async function renderPartCard(part, categories, resolveEquivalent) {
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

  // --- ofertas / precios ---
  const offers = Array.isArray(part.offers) ? part.offers : [];
  if (offers.length > 0) {
    const offersTitle = document.createElement("p");
    offersTitle.textContent = "Ofertas:";
    offersTitle.style.margin = "0.5rem 0 0";
    body.appendChild(offersTitle);

    const offersList = document.createElement("ul");
    offersList.className = "offers-list";
    offers.forEach((offer) => {
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
