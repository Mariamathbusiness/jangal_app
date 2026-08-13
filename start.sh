#!/bin/bash
python3 -m pip install --quiet gunicorn
gunicorn wsgi:app --bind 0.0.0.0:$PORT
