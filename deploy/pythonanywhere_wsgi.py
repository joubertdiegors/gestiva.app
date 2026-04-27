"""
Cole o conteúdo deste ficheiro no WSGI configuration file do PythonAnywhere
(Web → (link do ficheiro WSGI em /var/www/...)).

Ajuste PROJECT_HOME se o repositório estiver noutro caminho no servidor.
"""
import os
import sys

# Pasta que contém manage.py e o pacote "core/"
PROJECT_HOME = "/home/joubertdiegors/gestiva.app"
if PROJECT_HOME not in sys.path:
    sys.path.insert(0, PROJECT_HOME)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
