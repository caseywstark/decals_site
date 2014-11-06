from django import forms
from django.core.exceptions import ValidationError
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest, QueryDict, StreamingHttpResponse

from astrometry.util.starutil_numpy import *

from unwise.models import *
from unwise import settings

import subprocess

def tar_files(req, files, download_fn, basedir=settings.DATA_DIR):
    cmd = ['tar', '-c', '-z'] + files
    cmd = ' '.join(cmd)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            shell=True, 
                            bufsize=4096, close_fds=True,
                            cwd=basedir)
    pipe = proc.stdout
    res = StreamingHttpResponse(pipe,
                                content_type='application/x-compressed')
    res['Content-Disposition'] = 'attachment; filename="%s"' % download_fn
    return res

def unwise_tiles_near_radec(ra, dec, rad, tablename='unwise_tile',
                            extra_where='', tileclass=Tile):
    '''
    ra,dec,rad in degrees
    '''
    dec = np.deg2rad(dec)
    ra = np.deg2rad(ra)
    cosd = np.cos(dec)
    x,y,z = cosd * np.cos(ra), cosd * np.sin(ra), np.sin(dec)
    radius = rad + np.sqrt(2.)/2. * 2048 * 2.75 / 3600. * 1.01
    r2 = deg2distsq(radius)
    tiles = tileclass.objects.raw(
        ('SELECT *, ((x-(%g))*(x-(%g))+(y-(%g))*(y-(%g))+(z-(%g))*(z-(%g))) as r2'
         + ' FROM %s where r2 <= %g %s ORDER BY r2') %
        (x,x,y,y,z,z, tablename, r2, extra_where))
    return tiles

def parse_ra(rastr):
    try:
        ra = float(rastr)
    except:
        try:
            ra = hmsstring2ra(rastr)
        except:
            raise ValidationError('Failed to parse RA string: "%s" -- allowed formats are decimal degrees or HH:MM:SS' % rastr)
    return ra
        
def parse_dec(decstr):
    try:
        dec = float(decstr)
    except:
        try:
            dec = dmsstring2dec(decstr)
        except:
            raise ValidationError('Failed to parse Dec string: "%s" -- allowed formats are decimal degrees or +-DD:MM:SS' % decstr)
    return dec

def parse_coord(txt):
    words = txt.split()
    if not len(words) == 2:
        raise ValidationError('Need RA and Dec (as two space-separated words)')
    rastr,decstr = words
    ra = parse_ra(rastr)
    dec = parse_dec(decstr)
    return ra,dec

class CoordSearchForm(forms.Form):
    coord = forms.CharField(required=True, validators=[parse_coord],
                            initial='41 10')
    radius = forms.FloatField(required=False, initial=0)

class RaDecSearchForm(forms.Form):
    ra  = forms.FloatField(required=False, validators=[parse_ra])
    dec = forms.FloatField(required=False, validators=[parse_dec])
    radius = forms.FloatField(required=False)

