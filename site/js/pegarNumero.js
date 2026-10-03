// site/js/pegarNumero.js
//
// Caja reutilizable "¿Ya tienes el número de tu pieza? Pégalo aquí" — lleva
// al flujo de búsqueda por número de parte (searchPart vía dataClient.js,
// pero el fetch lo sigue haciendo solo dataClient.js; este módulo solo
// construye el formulario y delega el envío con un callback).

/**
 * @param {(value: string) => void} onSubmit
 * @returns {HTMLElement}
 */
export function renderPegarNumeroBox(onSubmit) {
  const box = document.createElement("section");
  box.className = "pegar-numero-box";
  box.setAttribute("aria-label", "Buscar por número de parte");

  const h3 = document.createElement("h3");
  h3.textContent = "¿Ya tienes el número de tu pieza? Pégalo aquí";
  box.appendChild(h3);

  const form = document.createElement("form");
  form.autocomplete = "off";

  const label = document.createElement("label");
  const inputId = `pegar-numero-${Math.random().toString(36).slice(2, 8)}`;
  label.htmlFor = inputId;
  label.className = "visually-hidden";
  label.textContent = "Número de parte";

  const input = document.createElement("input");
  input.type = "search";
  input.id = inputId;
  input.placeholder = "Ej: 1230A114";
  input.setAttribute("aria-label", "Número de parte");

  const btn = document.createElement("button");
  btn.type = "submit";
  btn.className = "btn btn-secondary";
  btn.textContent = "Buscar esta pieza";

  form.appendChild(label);
  form.appendChild(input);
  form.appendChild(btn);

  form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    const value = input.value.trim();
    if (value) onSubmit(value);
  });

  box.appendChild(form);
  return box;
}
