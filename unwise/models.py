from django.db.models import Model, IntegerField, CharField, FloatField, IPAddressField, DateTimeField, ManyToManyField, TextField, BooleanField

class Tile(Model):
    row = IntegerField(db_index=True)
    coadd = CharField(max_length=8, primary_key=True)
    ra  = FloatField()
    dec = FloatField()

    x = FloatField()
    y = FloatField()
    z = FloatField()
    
    class Meta():
        ordering = ['coadd']

    def __unicode__(self):
        return self.coadd

PRODUCT_COADD = 'coadd'
PRODUCT_SDSSPHOT = 'sdssphot'
product_choices = [(PRODUCT_COADD, PRODUCT_COADD),
                   (PRODUCT_SDSSPHOT, PRODUCT_SDSSPHOT)]

class UserCoordSearch(Model):
    product = CharField(default='coadd', max_length=20,
                        choices=product_choices)
    ip = IPAddressField()
    time = DateTimeField(auto_now=True)
    
    coord_str = CharField(max_length=100, blank=True)
    radius_str = CharField(max_length=100, blank=True)
    
    ra = FloatField(null=True)
    dec = FloatField(null=True)
    radius = FloatField(null=True)

    def __str__(self):
        return ('UserCoordSearch(%s, %s, %s from %s at %s)' %
                (self.product, self.coord_str, self.radius_str,
                 self.ip, self.time))

class UserRaDecSearch(Model):
    product = CharField(default='coadd', max_length=20,
                        choices=product_choices)
    ip = IPAddressField()
    time = DateTimeField(auto_now=True)
    
    ra_str = CharField(max_length=100, blank=True)
    dec_str = CharField(max_length=100, blank=True)
    radius_str = CharField(max_length=100, blank=True)
    
    ra = FloatField(null=True)
    dec = FloatField(null=True)
    radius = FloatField(null=True)

    def __str__(self):
        return ('UserRaDecSearch(%s, %s, %s, %s from %s at %s)' %
                (self.product, self.ra_str, self.dec_str, self.radius_str,
                 self.ip, self.time))

    
