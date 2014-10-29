"""
WSGI config for unwise project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

import os
import site
import sys

rootpath=os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
unwisepath=os.path.join(rootpath, 'unwise')

# This will make Django run in a virtual env
# Remember original sys.path.
prev_sys_path = list(sys.path)

# Add each new site-packages directory.
site.addsitedir(os.path.join(rootpath, 'lib', 'python2.6', 'site-packages'))

# Reorder sys.path so new directories at the front.
new_sys_path = []
for item in list(sys.path):
    if item not in prev_sys_path:
        new_sys_path.append(item)
        sys.path.remove(item)

new_sys_path.append(os.path.dirname(rootpath))

sys.path[:0] = new_sys_path

for i in [rootpath, unwisepath]:
    sys.path.append(i)

#print os.environ
# for x in sys.path:
#     print x
# import astrometry.util.util
# print astrometry.util.util.__file__
# import tractor
# print tractor.__file__
    
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'unwise.settings')
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

