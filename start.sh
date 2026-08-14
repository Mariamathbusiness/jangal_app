#!/bin/bash
set -e
echo "=== D?BUT DU DIAGNOSTIC RENDER ==="
echo "Dossier actuel : $(pwd)"
echo "PATH actuel : $PATH"
echo "Recherche de gunicorn dans le syst?me..."
find /opt/render -name "gunicorn" -type f 2>/dev/null || echo "Non trouv? dans /opt/render"
echo "Tentative d'activation de l'environnement virtuel..."
if [ -f "/opt/render/project/venv/bin/activate" ]; then
    source "/opt/render/project/venv/bin/activate"
    echo "? Activ? : /opt/render/project/venv"
elif [ -f "/opt/render/project/src/venv/bin/activate" ]; then
    source "/opt/render/project/src/venv/bin/activate"
    echo "? Activ? : /opt/render/project/src/venv"
elif [ -f "venv/bin/activate" ]; then
    source "venv/bin/activate"
    echo "? Activ? : venv local"
else
    echo "? Aucun venv trouv? !"
fi
echo "PATH apr?s activation : $PATH"
echo "=== FIN DU DIAGNOSTIC ==="
exec gunicorn wsgi:app --bind 0.0.0.0:$PORT
