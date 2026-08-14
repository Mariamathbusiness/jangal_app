#!/bin/bash
set -e
echo "=== D?marrage de Jangal_App ==="

# 1. Forcer l'activation de l'environnement virtuel cach? de Render
if [ -f "/opt/render/project/src/.venv/bin/activate" ]; then
    source "/opt/render/project/src/.venv/bin/activate"
    echo "? Environnement virtuel .venv activ? avec succ?s."
else
    echo "? Erreur: .venv non trouv? dans /opt/render/project/src/"
    exit 1
fi

# 2. Lancer l'application avec gunicorn (qui est maintenant dans le PATH)
exec gunicorn wsgi:app --bind 0.0.0.0:$PORT
