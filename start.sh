#!/bin/bash
# 1. Forcer l'activation de l'environnement virtuel de Render
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "/opt/render/project/venv" ]; then
    source /opt/render/project/venv/bin/activate
fi

# 2. Lancer l'application avec gunicorn
exec gunicorn wsgi:app --bind 0.0.0.0:$PORT
