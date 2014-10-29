"""
WSGI config for the DECaLS site.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/

"""

import os
import site
import sys

root_path = "/project/projectdirs/cosmo/webapp/decals_proto"
app_path = os.path.join(root_path, "decals_django")
venv_path = os.path.join(root_path, "venv_decals")

# This will make Django run in a virtual env
# Remember original sys.path.
prev_sys_path = list(sys.path)

# Add each new site-packages directory.
site.addsitedir(os.path.join(venv_path, "lib/python2.6/site-packages"))

# Reorder sys.path so new directories at the front.
new_sys_path = []
for item in list(sys.path):
    if item not in prev_sys_path:
        new_sys_path.append(item)
        sys.path.remove(item)

new_sys_path.append(os.path.dirname(root_path))

sys.path[:0] = new_sys_path

for i in [root_path, app_path]:
    sys.path.append(i)

os.environ["DJANGO_SETTINGS_MODULE"] = "unwise.settings"

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

