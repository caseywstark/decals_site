import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "unwise.settings")

from sdssphot.models import *

from astrometry.util.fits import *
from astrometry.util.starutil_numpy import *

import fitsio

for (dataset,version) in [
    ('sdss-dr10d', 'sdss-dr10d'),
    ('sdss-dr13', 'sdss-dr13'),
    ('eboss', 'eboss'),
    ]:

    tiles = PhotTile.objects.filter(version=version)
    print 'Found', tiles.count(), 'existing tiles for version', version
    if tiles.count():
        print 'Deleting.'
        tiles.delete()

    N0 = PhotTile.objects.all().count()
    
    T = fits_table('%s-atlas.fits' % dataset)
    print len(T), 'rows'
    T.cut(np.argsort(T.coadd_id))
    T.xyz = radectoxyz(T.ra, T.dec)
    tiles = []
    for i in range(len(T)):
        tile = PhotTile(version=version,
                        coadd=T.coadd_id[i], ra=T.ra[i], dec=T.dec[i],
                        x=T.xyz[i,0], y=T.xyz[i,1], z=T.xyz[i,2])
        tiles.append(tile)
    while len(tiles):
        N = 100
        PhotTile.objects.bulk_create(tiles[:N])
        tiles = tiles[N:]

    print 'Loaded', PhotTile.objects.all().count() - N0, 'objects into db'
