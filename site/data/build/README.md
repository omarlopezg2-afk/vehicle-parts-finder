# site/data/build/

Copia de los JSON reales de `data/build/` (raíz del repo) para que `site/`
pueda servirse como carpeta estática independiente
(`cd site && python3 -m http.server`) sin rutas que salgan de su raíz.

**Esto es temporal y manual.** Cuando T-G2 (`deploy-site.yml`) esté listo,
el workflow de deploy debe copiar `data/build/*.json` aquí automáticamente
antes de publicar en GitHub Pages, y este directorio puede dejar de vivir en
git (o seguir como snapshot de desarrollo, a decidir en T-G2).

Mientras tanto: si corres `python3 pipeline/build_index.py` desde la raíz y
cambian los datos, vuelve a copiarlos aquí a mano para que el frontend local
los vea actualizados:

```
cp data/build/{parts,vehicles,categories,search_index}.json site/data/build/
```
