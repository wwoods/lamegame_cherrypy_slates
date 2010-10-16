import urllib
import urllib2

def allow_cookies():
    import cookielib
    cj = cookielib.LWPCookieJar()
    
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    urllib2.install_opener(opener)
allow_cookies()
del allow_cookies

def make_request(url, *args):
    """Makes a request to 'http://127.0.0.1:8080' + url.
    If a second argument is provided, it is a dict of
    arguments to be passed.
    """
    base = 'http://127.0.0.1:8080'
    data = None
    if len(args) > 0:
        data = urllib.urlencode(args[0])
    req = urllib2.urlopen(base + url, data)
    result = str(req.read())
    req.close()
    return result

