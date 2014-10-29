import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "unwise.settings")

from unwise.models import *

from astrometry.util.fits import *
from astrometry.util.starutil_numpy import *


import fitsio

T = fits_table('allsky-atlas.fits')
T.delete_column('row')
print len(T), 'rows'
T.cut(np.argsort(T.coadd_id))

if False:
    from astrometry.libkd.spherematch import *
    print 'Build tree...'
    kd = tree_build_radec(T.ra, T.dec)
    fn = 'allsky.kd'
    print 'Save tree...'
    tree_save(kd, fn)
    I = np.arange(int(len(T))).astype(np.int32)
    print 'Permute...', I.dtype, I.shape
    tree_permute(kd, I)
    tree_free(kd)
    K = T[I]
    print 'Append...'
    K.delete_column('ra')
    K.delete_column('dec')
    K.writeto(fn, append=True)
    print 'Wrote', fn

T.xyz = radectoxyz(T.ra, T.dec)
tiles = []
for i in range(len(T)):
    tile = Tile(row=i, coadd=T.coadd_id[i], ra=T.ra[i], dec=T.dec[i],
                x=T.xyz[i,0], y=T.xyz[i,1], z=T.xyz[i,2])
    tiles.append(tile)
while len(tiles):
    N = 100
    Tile.objects.bulk_create(tiles[:N])
    tiles = tiles[N:]

print 'Loaded', Tile.objects.all().count(), 'objects into db'
