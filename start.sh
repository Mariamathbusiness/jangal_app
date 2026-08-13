#!/bin/bash
# On utilise 'python' qui pointe automatiquement vers l'environnement virtuel de Render
exec python -m gunicorn wsgi:app --bind 0.0.0.0:$PORT
