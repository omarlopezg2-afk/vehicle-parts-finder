#!/usr/bin/env bash
#
# Carga las llaves de eBay desde .env a los GitHub Secrets del repo, SIN
# imprimir los valores en pantalla ni pasarlos por la línea de comandos
# (los argumentos de un proceso son visibles para otros usuarios del sistema;
# la entrada estándar no).
#
# Uso:  scripts/seed-secrets.sh
#
# Se niega a correr si el .env tiene valores vacíos, para no dejar secretos
# a medias que hacen fallar el pipeline de forma confusa (el código cae a modo
# mock sin avisar).
set -euo pipefail

REPO="omarlopezg2-afk/vehicle-parts-finder"
ENV_FILE="${ENV_FILE:-.env}"
VARS=(EBAY_CLIENT_ID EBAY_CLIENT_SECRET)

if [ ! -f "$ENV_FILE" ]; then
  echo "No existe $ENV_FILE — cópialo de .env.example y rellénalo primero." >&2
  exit 1
fi

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

for var in "${VARS[@]}"; do
  value="${!var:-}"
  if [ -z "$value" ]; then
    echo "Falta $var en $ENV_FILE (vacío). No se toca ningún secreto." >&2
    exit 1
  fi
  printf '%s' "$value" | gh secret set "$var" --repo "$REPO" >/dev/null
  echo "  $var -> cargado (${#value} caracteres)"
done

echo
echo "Secretos en $REPO:"
gh secret list --repo "$REPO"
