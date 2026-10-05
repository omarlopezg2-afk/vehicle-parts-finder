// site/js/confianza.js
//
// Banda de confianza del inicio (dirección B, 05/10/2026).
//
// POR QUÉ CALCULA EN VEZ DE LLEVAR LAS CIFRAS ESCRITAS: si los números van a mano
// en el HTML, el día que el pipeline traiga más piezas el sitio sigue presumiendo
// de 28 y de 1.194 — es decir, promete algo que ya no es cierto. Aquí se cuentan
// del catálogo real en cada carga.
//
// Y si los datos que se cargaron son de DESARROLLO (fixture), la banda no se
// muestra: no se presume de cifras que no son del catálogo real.

import { getResumenCatalogo } from "./dataClient.js";

// Formato dominicano: el separador de miles lo decide el propio navegador para
// es-DO, en vez de que yo lo escriba a mano y me equivoque de convención.
const numero = new Intl.NumberFormat("es-DO");

/**
 * Pinta la banda de confianza dentro de `container`.
 * Si no hay datos reales, deja el contenedor vacío y oculto (nunca cifras falsas).
 *
 * @param {HTMLElement|null} container
 * @returns {Promise<void>}
 */
export async function renderBandaDeConfianza(container) {
  if (!container) return;

  try {
    const { partes, ofertas, categorias, usandoFixture } = await getResumenCatalogo();

    if (usandoFixture) {
      container.replaceChildren();
      container.hidden = true;
      return;
    }

    const cifras = [
      { valor: numero.format(partes), texto: "números de parte verificados uno por uno" },
      { valor: numero.format(ofertas), texto: "ofertas reales de eBay" },
      { valor: numero.format(categorias), texto: "categorías de piezas" },
      {
        valor: "0",
        texto: "cookies: tu vehículo se queda en tu navegador",
        clase: "cifra-verde",
      },
    ];

    container.replaceChildren(
      ...cifras.map(({ valor, texto, clase }) => {
        const celda = document.createElement("div");
        celda.className = clase ? `cifra ${clase}` : "cifra";

        const fuerte = document.createElement("b");
        fuerte.textContent = valor;

        const etiqueta = document.createElement("span");
        etiqueta.textContent = texto;

        celda.append(fuerte, etiqueta);
        return celda;
      })
    );
    container.hidden = false;
  } catch (error) {
    // Sin catálogo no hay cifras que dar. Se oculta en vez de inventarlas.
    console.error("confianza: no se pudo calcular la banda", error);
    container.replaceChildren();
    container.hidden = true;
  }
}
