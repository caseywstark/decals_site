from unwise.models import UserCoordSearch, UserRaDecSearch
from coadd.models import UserDownload

from django.contrib.sessions.models import Session

class UnwiseDatabaseRouter(object):
    def __init__(self):
        self.usage = [ UserDownload, UserCoordSearch, UserRaDecSearch ]
        self.session = [ Session ]

    def _db(self, model, **hints):
        if model in self.usage:
            return 'usage'
        if model in self.session:
            return 'session'
        return 'default'
        
    def db_for_read(self, model, **hints):
        return self._db(model, **hints)

    def db_for_write(self, model, **hints):
        return self._db(model, **hints)

    def allow_syncdb(self, db, model):
        print 'allow_syncdb: db', db, 'model', model
        if db == 'usage':
            return model in self.usage
        if db == 'session':
            return model in self.session
        if db == 'default':
            if model in self.usage:
                return False
            if model in self.session:
                return False
        return None
