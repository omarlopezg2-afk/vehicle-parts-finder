# site/data/build/

Copia de los JSON de `data/build/` (raíz del repo) para que `site/` pueda servirse
como carpeta estática independiente (`cd site && python3 -m http.server`) sin rutas
que salgan de su raíz. El frontend **solo** lee de aquí, vía `site/js/dataClient.js`
(regla de escalado, ver `CONTRACTS.md`).

## Estos .json NO están en git

Son un **artefacto del deploy**: `.github/workflows/deploy-site.yml` los copia desde
`data/build/` justo antes de publicar en GitHub Pages, así que en producción siempre
están frescos.

Antes sí estaban versionados a mano, y eso ya causó un problema real: la copia
commiteada se quedó en **2 partes y 6 ofertas** mientras el catálogo real tenía 28 y
1.194. Cualquiera que levantara el sitio en su máquina veía cifras que no eran las
del producto (y la banda de confianza del inicio, que cuenta el catálogo real, las
mostraba). Por eso se sacaron de git: un artefacto que se regenera no debe vivir en
el historial, donde envejece sin que nadie lo note.

## Para trabajar en local

```bash
# 1. Trae los datos reales a la carpeta que lee el frontend
cp data/build/{parts,vehicles,categories,search_index}.json site/data/build/

# 2. Sirve el sitio
cd site && python3 -m http.server
```

Si no haces el paso 1 (o abres `site/index.html` con `file://`), `dataClient.js` cae
a las fixtures de desarrollo de `site/js/fixtures/`. En ese caso el sitio muestra un
aviso de "datos de desarrollo" y la banda de confianza **se oculta**: no presume de
cifras que no vienen del catálogo real.
