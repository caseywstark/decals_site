from django.db import models

class Instrument(models.Model):
    """
    Arbitrary observational instrument.

    """
    name = models.CharField(max_length=256)

class Brick(models.Model):
    """
    A brick on the sky, part of decals decomposition.

    """
    ra = models.FloatField()
    dec = models.FloatField()
    ra_lo = models.FloatField()
    ra_hi = models.FloatField()
    dec_lo = models.FloatField()
    dec_hi = models.FloatField()

    class Meta:
        ordering = ('ra_lo', 'dec_lo')

    def __unicode__(self):
        return "Brick (%f, %f)" % (self.ra, self.dec)

class Image(models.Model):
    """
    A single exposure from the survey.

    """
    instrument = models.ForeignKey(Instrument)
    exposure_id = models.IntegerField()
    ccd_id = models.IntegerField()
    ra_lo = models.FloatField()
    ra_hi = models.FloatField()
    dec_lo = models.FloatField()
    dec_hi = models.FloatField()

class Reduction(models.Model):
    """

    """
    tractor_git_version = models.CharField(max_length=256)
    decals_dir = models.CharField(max_length=256)
    start = models.DateTimeField()
    end = models.DateTimeField()

class CatalogObject(models.Model):
    """
    """
    reduction = models.ForeignKey(Reduction)
    brick = models.ForeignKey(Brick)
    #object_type = models.ForeignKey(ObjectType)
    brick_x = models.FloatField()
    brick_y = models.FloatField()
    ra = models.FloatField()
    dec = models.FloatField()


"""
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
"""
