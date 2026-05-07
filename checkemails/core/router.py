from optisolve.core.middleware import get_current_db_name


class DatabaseRouter (object):
    def _default_db( self ):
        db = get_current_db_name()
        if db:
            return db
        else:
            return 'default'

    def db_for_read( self, model, **hints ):
        return self._default_db()

    def db_for_write( self, model, **hints ):
        return self._default_db()