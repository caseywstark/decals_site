import os
import tempfile

import simplejson

from django.shortcuts import render
from django.http import HttpResponse

from astrometry.util.util import *
from astrometry.util.resample import *
from astrometry.util.fits import *

from scipy.ndimage.filters import gaussian_filter

def index(request):
    """
    index serves up the html page containing the leaflet source
    and required url's

    """
    # some defaults
    default_layer = "decals"
    default_ra = 244.7
    default_dec = 7.4
    default_zoom = 13

    layer = request.GET.get("layer", default_layer)

    try:
        zoom = int( request.GET.get("zoom", default_zoom) )
    except ValueError:
        pass
    try:
        ra = float( request.GET.get("ra", default_ra) )
    except ValueError:
        pass
    try:
        dec = float( request.GET.get("dec", default_dec) )
    except ValueError:
        pass

    lat, lon = dec, 180.0 - ra

    tile_url = "/maps/{s}/{id}/{z}/{x}/{y}.jpg"
    catalog_url = "/maps/{id}/{z}/{x}/{y}.cat.json"

    polygons = ""
    base_url = request.path + '?layer=%s&' % layer

    return render(request, "maps.html",
        dict(page={"title": "maps"},
            ra=ra, dec=dec, lat=lat, lon=lon, zoom=zoom,
            layer=layer, tile_url=tile_url, polygons=polygons,
            base_url=base_url, catalog_url=catalog_url))

# util function
def get_tile_wcs(zoom, x, y):
    zoom = int(zoom)
    zoom_scale = 2.0**zoom
    x = int(x)
    y = int(y)
    if zoom < 0 or x < 0 or y < 0 or x >= zoom_scale or y >= zoom_scale:
        raise RuntimeError("Invalid zoom, x, y %i, %i, %i" % (zoom, x, y))

    W, H = 256, 256
    if zoom == 0:
        rx = ry = 0.5
    else:
        rx = zoom_scale / 2.0 - x
        ry = zoom_scale / 2.0 - y
    rx = rx * W
    ry = ry * H
    wcs = anwcs_create_mercator_2(180.0, 0.0, rx, ry,
                                  zoom_scale, W, H, 1)
    print x, y, wcs
    return wcs, W, H, zoom_scale, zoom, x, y

# util function
def get_scaled(scalepat, scalekwargs, scale, basefn):
    if scale <= 0:
        return basefn
    fn = scalepat % dict(scale=scale, **scalekwargs)
    if not os.path.exists(fn):
        sourcefn = get_scaled(scalepat, scalekwargs, scale-1, basefn)
        #print 'Source:', sourcefn
        if sourcefn is None or not os.path.exists(sourcefn):
            print 'No source'
            return None
        I = fitsio.read(sourcefn)
        #print 'source image:', I.shape
        H,W = I.shape
        # make even size; smooth down
        if H % 2 == 1:
            I = I[:-1,:]
        if W % 2 == 1:
            I = I[:,:-1]
        im = gaussian_filter(I, 1.)
        #print 'im', im.shape
        # bin
        I2 = (im[::2,::2] + im[1::2,::2] + im[1::2,1::2] + im[::2,1::2])/4.
        #print 'I2:', I2.shape
        # shrink WCS too
        wcs = Tan(sourcefn, 0)
        # include the even size clip; this may be a no-op
        H,W = im.shape
        wcs = wcs.get_subimage(0, 0, W, H)
        subwcs = wcs.scale(0.5)
        hdr = fitsio.FITSHDR()
        subwcs.add_to_header(hdr)
        fitsio.write(fn, I2, header=hdr, clobber=True)
        #print 'Wrote', fn
    return fn

def map_decals(request, zoom, x, y):
    return map_coadd_bands(request, zoom, x, y, 'grz', 'decals', 'decals')

def map_decals_model(request, zoom, x, y):
    return map_coadd_bands(request, zoom, x, y, 'grz', 'decals-model', 'decals-model', imagetag='model')

def map_coadd_bands(request, zoom, x, y, bands, tag, image_path,
                    image_tag="image2", rgbkwargs={}):
    try:
        wcs, W, H, zoomscale, zoom, x, y = get_tile_wcs(zoom, x, y)
    except RuntimeError as e:
        return HttpResponse(e.strerror)

    base_path = "map_data"
    tile_path = os.path.join(base_path, "tiles", tag, '%i/%i/%i.jpg' % (zoom, x, y))
    if os.path.exists(tile_path):
        print "cached:", tile_path
        f = open(tile_path)
        return HttpResponse(f, content_type="image/jpeg")

    ok, r, d = wcs.pixelxy2radec([1,1,1,W/2,W,W,W,W/2],
                                 [1,H/2,H,H,H,H/2,1,1])
    # print 'RA,Dec corners', r,d
    # print 'RA range', r.min(), r.max()
    # print 'Dec range', d.min(), d.max()
    # print 'Zoom', zoom, 'pixel scale', wcs.pixel_scale()

    coadd_path = os.path.join(base_path, "coadd", image_path, image_tag + '-%(brick)06i-%(band)s.fits')
    scaled = 0
    scale_path = None
    if zoom < 14:
        scaled = (14 - zoom)
        scaled = np.clip(scaled, 1, 8)
        dirnm = os.path.join(base_path, "scaled", image_path)
        scale_pat = os.path.join(dirnm, imagetag + '-%(brick)06i-%(band)s-%(scale)i.fits')
        if not os.path.exists(dirnm):
            try:
                os.makedirs(dirnm)
            except:
                pass

    D = Decals()
    B = D.get_bricks()
    I = D.bricks_touching_radec_box(B, r.min(), r.max(), d.min(), d.max())
    rimgs = []

    # If any problems are encountered during tile rendering, don't save
    # the results... at least it'll get fixed upon reload.
    save_cache = True

    for band in bands:
        rimg = np.zeros((H,W), np.float32)
        rn = np.zeros((H,W), np.uint8)
        for brick_id in B.brickid[I]:
            fnargs = dict(brick=brick_id, band=band)
            basefn = basepat % fnargs
            fn = get_scaled(scalepat, fnargs, scaled, basefn)
            if fn is None:
                savecache = False
                continue
            if not os.path.exists(fn):
                savecache = False
                continue
            try:
                bwcs = Tan(fn, 0)
            except:
                print 'Failed to read WCS:', fn
                savecache = False
                continue

            ok,xx,yy = bwcs.radec2pixelxy(r, d)
            xx = xx.astype(np.int)
            yy = yy.astype(np.int)
            #print 'x,y', x,y
            imW,imH = int(bwcs.get_width()), int(bwcs.get_height())
            M = 10
            #print 'brick coordinates of tile: x', xx.min(), xx.max(), 'y', yy.min(), yy.max()
            xlo = np.clip(xx.min() - M, 0, imW)
            xhi = np.clip(xx.max() + M, 0, imW)
            ylo = np.clip(yy.min() - M, 0, imH)
            yhi = np.clip(yy.max() + M, 0, imH)
            #print 'brick size', imW, 'x', imH
            #print 'clipped brick coordinates: x', xlo, xhi, 'y', ylo,yhi
            if xlo >= xhi or ylo >= yhi:
                #print 'skipping'
                continue

            subwcs = bwcs.get_subimage(xlo, ylo, xhi-xlo, yhi-ylo)
            slc = slice(ylo,yhi), slice(xlo,xhi)
            try:
                f = fitsio.FITS(fn)[0]
                img = f[slc]
            except:
                print 'Failed to read image and WCS:', fn
                savecache = False
                continue
            #print 'Subimage shape', img.shape
            #print 'Sub-WCS shape', subwcs.get_height(), subwcs.get_width()
            try:
                Yo,Xo,Yi,Xi,nil = resample_with_wcs(wcs, subwcs, [], 3)
            except OverlapError:
                #print 'Resampling exception'
                #import traceback
                #traceback.print_exc()
                continue

            # resampling...
            rimg[Yo, Xo] += img[Yi,Xi]
            rn[Yo, Xo] += 1
        rimg /= np.maximum(rn, 1)
        rimgs.append(rimg)
    rgb = get_rgb(rimgs, bands, **rgbkwargs)

    try:
        os.makedirs(os.path.dirname(tile_path))
    except:
        pass

    if not save_cache:
        f, tile_path = tempfile.mkstemp(suffix='.jpg')
        os.close(f)

    plt.imsave(tile_path, rgb)
    f = open(tile_path)
    if not save_cache:
        os.unlink(tile_path)

    return HttpResponse(f, content_type="image/jpeg")
