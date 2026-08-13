#!/bin/bash
exec python3 -m gunicorn wsgi:app --bind 0.0.0.0:$PORT
