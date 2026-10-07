// site/js/vinFicha.js
//
// Lo que la ficha de un VIN dice de un carro, en español y sin decimales absurdos.
//
// Medido en partexact.com el 07/10/2026: la ficha de un VIN que no está en el catálogo enseñaba
// "Motor: 2.998832712 L", "Combustible: Gasoline" y "Fabricado en: UNITED STATES (USA)" (la NHTSA
// contesta en inglés y con la cilindrada sin redondear). Aquí se arregla, sin red.
//
// Regla 3 del proyecto: nunca "gas" a secas. La traducción del combustible es la misma tabla que ya
// usa el catálogo (`traducirCombustible`), así "Gasoline" sale como "Gasolina".
import { origenDeVin } from "./vinOrigen.js";
import { traducirCombustible } from "./catalogoMap.js";

/** La cilindrada con un decimal ("3.0 L"). Si no es un número, no se enseña. */
export function litros(valor) {
  const n = Number(valor);
  return Number.isFinite(n) && n > 0 ? `${n.toFixed(1)} L` : "";
}

/** "Fabricado en …" por el inicio del VIN (en español); si el VIN no está en la tabla, lo que diga la NHTSA. */
export function paisDeFabricacion(d) {
  const propio = origenDeVin(d && d.vin);
  return (propio && propio.pais) || (d && d.plantCountry) || "";
}

/** Las filas [etiqueta, valor] de la ficha de un VIN decodificado. Las vacías no salen. */
export function filasDeVin(d) {
  const motor = [
    litros(d.displacementL),
    d.engineCylinders ? `${d.engineCylinders} cil.` : "",
    d.engineHP ? `${d.engineHP} HP` : "",
  ].filter(Boolean).join(" · ");
  return [
    ["Marca", d.make],
    ["Modelo", d.model],
    ["Año", d.year],
    ["Versión", d.trim || d.series],
    ["Carrocería", d.bodyClass],
    ["Motor", motor],
    ["Tracción", d.driveType],
    ["Transmisión", d.transmission],
    ["Combustible", traducirCombustible(d.fuelType)],
    ["Fabricado en", paisDeFabricacion(d)],
  ].filter(([, valor]) => valor);
}

/**
 * Para un VIN que SÍ está en el catálogo: la línea que dice dónde se fabricó. Es el país de fabricación,
 * no el mercado al que se vendió (un carro hecho en Japón pudo salir para EE.UU. o para RD).
 */
export function lineaDeOrigen(vin) {
  const o = origenDeVin(vin);
  return o
    ? `Por el inicio del VIN (${o.codigo}), tu carro fue fabricado en ${o.pais}. ` +
      "Eso dice dónde se hizo, no a qué mercado se vendió."
    : "";
}
