from flask import request,url_for

def url_for_other_page(page):
    args = request.args.copy()
    args['page'] = page
    return url_for(request.endpoint, **args) # pylint: disable=W0142

def datetimeformat(value, format='%H:%M / %d-%m-%Y'):
    return value.strftime(format)
