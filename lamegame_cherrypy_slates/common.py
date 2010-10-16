import cherrypy

def log(message):
    if log.enabled:
        cherrypy.log(message, 'LGTOOLS.SLATES')
log.enabled = False

