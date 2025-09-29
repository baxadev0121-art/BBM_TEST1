import os, sys
sys.path.insert(0, "/home/username/mytest")
os.environ['DJANGO_SETTINGS_MODULE'] = 'mytest.settings'
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()