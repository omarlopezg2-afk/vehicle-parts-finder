// site/tests/categoryTree.test.js
//
// Tests de Node (node --test, sin dependencias) para la parte PURA de
// site/js/categoryTree.js: groupCategories(categories). El resto del
// archivo (renderCategoryGrid/renderVehicleTree) construye DOM real
// (document.createElement) y no hay jsdom/Playwright instalado en este
// proyecto a propósito (ver site/tests/README.md, sección "NO
// automatizado") — por eso el acordeón de grupos (expandir/colapsar,
// aria-expanded, orden de Tab) se verifica a mano, ver "cómo probar" del
// PR de T-E7. Lo que SÍ se puede (y se debe) cubrir sin DOM es la lógica
// de agrupamiento en sí, que es la parte nueva de T-E7 con más
// superficie para bugs silenciosos (orden de grupos, fallback cuando
// falta group_slug/group_name_es, no mutar el arreglo de entrada).
//
// Cómo correr: desde site/ -> `node --test tests/`

import { test, describe } from "node:test";
import assert from "node:assert/strict";

import { groupCategories } from "../js/categoryTree.js";

const SAMPLE = [
  { slug: "filtro-aceite", name_es: "Filtro de aceite", svg: "filtro-aceite.svg", group_slug: "mantenimiento", group_name_es: "Mantenimiento" },
  { slug: "pastillas-freno", name_es: "Pastillas de freno", svg: "pastillas-freno.svg", group_slug: "frenos", group_name_es: "Frenos" },
  { slug: "discos-freno", name_es: "Discos de freno", svg: "discos-freno.svg", group_slug: "frenos", group_name_es: "Frenos" },
  { slug: "filtro-aire", name_es: "Filtro de aire", svg: "filtro-aire.svg", group_slug: "mantenimiento", group_name_es: "Mantenimiento" },
  { slug: "bujia", name_es: "Bujía", svg: "bujia.svg", group_slug: "motor", group_name_es: "Motor" },
];

describe("categoryTree.js -> groupCategories", () => {
  test("agrupa categorías por group_slug preservando orden de primera aparición", () => {
    const groups = groupCategories(SAMPLE);
    assert.deepEqual(
      groups.map((g) => g.slug),
      ["mantenimiento", "frenos", "motor"]
    );
  });

  test("cada grupo conserva sus slugs hoja en el orden original", () => {
    const groups = groupCategories(SAMPLE);
    const frenos = groups.find((g) => g.slug === "frenos");
    assert.deepEqual(
      frenos.categories.map((c) => c.slug),
      ["pastillas-freno", "discos-freno"]
    );
  });

  test("usa group_name_es como etiqueta visible del grupo", () => {
    const groups = groupCategories(SAMPLE);
    const motor = groups.find((g) => g.slug === "motor");
    assert.equal(motor.name_es, "Motor");
  });

  test("categorías sin group_slug/group_name_es caen en un grupo 'Otros' de respaldo", () => {
    const sinGrupo = [
      { slug: "generico-sin-foto", name_es: "Genérico (sin foto)", svg: "x.svg" },
    ];
    const groups = groupCategories(sinGrupo);
    assert.equal(groups.length, 1);
    assert.equal(groups[0].slug, "otros");
    assert.equal(groups[0].name_es, "Otros");
    assert.equal(groups[0].categories[0].slug, "generico-sin-foto");
  });

  test("mezcla de categorías con y sin group_slug no pierde ninguna", () => {
    const mixed = [
      ...SAMPLE,
      { slug: "generico-sin-foto", name_es: "Genérico (sin foto)", svg: "x.svg" },
    ];
    const groups = groupCategories(mixed);
    const totalLeaves = groups.reduce((sum, g) => sum + g.categories.length, 0);
    assert.equal(totalLeaves, mixed.length);
    assert.ok(groups.some((g) => g.slug === "otros"));
  });

  test("no muta el arreglo de entrada", () => {
    const copy = SAMPLE.map((c) => ({ ...c }));
    groupCategories(copy);
    assert.deepEqual(copy, SAMPLE);
  });

  test("arreglo vacío regresa [] sin lanzar error", () => {
    assert.deepEqual(groupCategories([]), []);
  });

  test("null/undefined regresa [] sin lanzar error", () => {
    assert.deepEqual(groupCategories(null), []);
    assert.deepEqual(groupCategories(undefined), []);
  });

  test("13 categorías reales de categories.json agrupan en 9 grupos (8 + Otros)", () => {
    // Mismos datos que data/build/categories.json (T-F2) al momento de
    // este PR, sin depender de leer el archivo del disco (evita que un
    // cambio futuro en el catálogo real rompa este test de la función
    // pura de agrupamiento en sí).
    const real = [
      { slug: "filtro-aceite", name_es: "Filtro de aceite", svg: "filtro-aceite.svg", group_slug: "mantenimiento", group_name_es: "Mantenimiento" },
      { slug: "filtro-aire", name_es: "Filtro de aire", svg: "filtro-aire.svg", group_slug: "mantenimiento", group_name_es: "Mantenimiento" },
      { slug: "pastillas-freno", name_es: "Pastillas de freno", svg: "pastillas-freno.svg", group_slug: "frenos", group_name_es: "Frenos" },
      { slug: "discos-freno", name_es: "Discos de freno", svg: "discos-freno.svg", group_slug: "frenos", group_name_es: "Frenos" },
      { slug: "bujia", name_es: "Bujía", svg: "bujia.svg", group_slug: "motor", group_name_es: "Motor" },
      { slug: "amortiguador", name_es: "Amortiguador", svg: "amortiguador.svg", group_slug: "suspension-direccion", group_name_es: "Suspensión y dirección" },
      { slug: "bateria", name_es: "Batería", svg: "bateria.svg", group_slug: "electrico", group_name_es: "Eléctrico" },
      { slug: "correa", name_es: "Correa (banda)", svg: "correa.svg", group_slug: "motor", group_name_es: "Motor" },
      { slug: "bomba-agua", name_es: "Bomba de agua", svg: "bomba-agua.svg", group_slug: "refrigeracion", group_name_es: "Refrigeración" },
      { slug: "alternador", name_es: "Alternador", svg: "alternador.svg", group_slug: "electrico", group_name_es: "Eléctrico" },
      { slug: "faro", name_es: "Faro", svg: "faro.svg", group_slug: "iluminacion", group_name_es: "Iluminación" },
      { slug: "limpiaparabrisas", name_es: "Limpiaparabrisas", svg: "limpiaparabrisas.svg", group_slug: "carroceria-exterior", group_name_es: "Carrocería y exterior" },
      { slug: "generico-sin-foto", name_es: "Genérico (sin foto)", svg: "generico-sin-foto.svg", group_slug: "otros", group_name_es: "Otros" },
    ];
    const groups = groupCategories(real);
    assert.equal(real.length, 13);
    assert.equal(groups.length, 9);
    const totalLeaves = groups.reduce((sum, g) => sum + g.categories.length, 0);
    assert.equal(totalLeaves, 13);
  });
});
