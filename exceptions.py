import types

class AuthenticateFailure(Exception):
    code = 30001
    name = "authenticate-failure"

    def __init__(self, description=None):
        Exception.__init__(self, '%d %s' % (self.code, self.name))
        if description is not None:
            if isinstance(description, types.StringType):
                description = description.decode("utf-8")
            self.description = description

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        if 'description' in self.__dict__:
            txt = self.description
        else:
            txt = self.name
        return u'%d: %s' % (self.code, txt)

    def __repr__(self):
        return '<%s \'%s\'>' % (self.__class__.__name__, self)

class PropertyError(Exception):
    code = 30003
    name = "property-error"

    def __init__(self, description=None):
        Exception.__init__(self, '%d %s' % (self.code, self.name))
        if description is not None:
            if isinstance(description, types.StringType):
                description = description.decode("utf-8")
            self.description = description

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        if 'description' in self.__dict__:
            txt = self.description
        else:
            txt = self.name
        return u'%d: %s' % (self.code, txt)

    def __repr__(self):
        return '<%s \'%s\'>' % (self.__class__.__name__, self)

class InvalidAction(Exception):
    code = 30004
    name = "invalid-action"

    def __init__(self, description=None):
        Exception.__init__(self, '%d %s' % (self.code, self.name))
        if description is not None:
            if isinstance(description, types.StringType):
                description = description.decode("utf-8")
            self.description = description

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        if 'description' in self.__dict__:
            txt = self.description
        else:
            txt = self.name
        return u'%d: %s' % (self.code, txt)

    def __repr__(self):
        return '<%s \'%s\'>' % (self.__class__.__name__, self)

class InvalidStatus(Exception):
    code = 30005
    name = "invalid-status"

    def __init__(self, description=None):
        Exception.__init__(self, '%d %s' % (self.code, self.name))
        if description is not None:
            if isinstance(description, types.StringType):
                description = description.decode("utf-8")
            self.description = description

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        if 'description' in self.__dict__:
            txt = self.description
        else:
            txt = self.name
        return u'%d: %s' % (self.code, txt)

    def __repr__(self):
        return '<%s \'%s\'>' % (self.__class__.__name__, self)