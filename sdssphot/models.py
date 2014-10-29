from django.db.models import Model, IntegerField, CharField, FloatField, IPAddressField, DateTimeField, ManyToManyField, TextField, BooleanField

from unwise.models import *

class PhotTile(Model):
    version = CharField(max_length=20)

    coadd = CharField(max_length=8)
    ra  = FloatField()
    dec = FloatField()

    x = FloatField()
    y = FloatField()
    z = FloatField()
    
    class Meta():
        ordering = ['coadd']

    def __unicode__(self):
        return self.coadd
    

    
