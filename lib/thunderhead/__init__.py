
class Account(object):
    def __init__(self, provider, *creds, **namedCreds):
        if creds: self.credentials = creds
        if namedCreds: self.namedCredentials = namedCreds
        self._bindToProvider(provider)

    def _bindToProvider(self, provider):
        self.provider = provider
        interface = getattr(provider.api, 'serverManagementInterface')
        if interface:
            for func in interface:
                setattr(self, func, self._wrapMethod(getattr(provider.api, func)))
        return self.provider

    def _wrapMethod(self, func):
        def wrappedFunc(*args, **kwargs):
            return func(self.session.serverManager, *args, **kwargs)
        return wrappedFunc

    def _getSession(self):
        if not hasattr(self, '_session'):
            args = (getattr(self, 'credentials') or [])
            kwargs = (getattr(self, 'namedCredentials') or {})
            self._session = self.provider.Authorization(*args, **kwargs)
        return self._session

    session = property(
        _getSession,
        None,
        None,
        None,
    )

