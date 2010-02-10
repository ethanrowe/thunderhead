##  Copyright (c) 2009-2010 Ethan Rowe (ethan@endpoint.com)
##  For more information, see http://github.com/ethanrowe/thunderhead
##
##  This file is part of Thunderhead.
##
##  Thunderhead is free software: you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation, either version 3 of the License, or
##  (at your option) any later version.
##
##  Thunderhead is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License for more details.
##
##  You should have received a copy of the GNU General Public License
##  along with Thunderhead.  If not, see <http://www.gnu.org/licenses/>.

class Account(object):
    def __init__(self, provider, *creds, **namedCreds):
        if creds: self.credentials = creds
        if namedCreds: self.namedCredentials = namedCreds
        self._bindToProvider(provider)

    def _bindToProvider(self, provider):
        self.provider = provider
        interface = getattr(provider.api, 'serverManagementInterface')
        if interface:
            for item in interface:
                info = item if hasattr(item, 'has_key') else {'name': item}
                func = self._getProviderFunction(**info)
                setattr(self, info['name'], self._wrapMethod(func))
        return self.provider

    def _getProviderFunction(self, **kwargs):
        func = getattr(self.provider.api, kwargs['name'])
        if kwargs.has_key('wrapper'):
            func = kwargs['wrapper'](func)
        return func

    def _wrapMethod(self, func):
        def wrappedFunc(*args, **kwargs):
            return func(self.session.serverManager, *args, **kwargs)
        return wrappedFunc

    def _getSession(self):
        if not hasattr(self, '_session'):
            args = (getattr(self, 'credentials', None) or [])
            kwargs = (getattr(self, 'namedCredentials', None) or {})
            self._session = self.provider.Authorization(*args, **kwargs)
        return self._session

    session = property(
        _getSession,
        None,
        None,
        None,
    )

class CachedResource(object):
    """
    NAME
        CachedResource

    DESCRIPTION
        General utility class for providing function/method wrapper objects
        with basic caching scheme.

        A concrete implementation needs to define:
        * an initialize method
        * an update method
        * an optional representation method

        Each method should operate on an underlying "asset" attribute that contains
        the cached state.

        The initialize method will should perform the relevant logic for determining the
        first value for the asset.

        The update method should do whatever is necessary to determine whether the asset
        needs to be updated, and perform that update logic as needed as well.

        The representation method's return value is used for the return value of
        __call__ on the wrapper object.  By default, it simply returns the cached
        asset.

        All three methods are passed along any positional and keyword arguments that were
        provided to the initial invocation.  This allows for strategies such as the asset
        maintaining a full set of data, maintained by initialize/update, with representation
        returning a subset of the asset data by appying filters based on the arguments.
    """
    initialized = False
    asset = None

    def representation(self, *args, **kwargs):
        return self.asset

    def __call__(self, *args, **kwargs):
        if not self.initialized:
            self.initialize(*args, **kwargs)
            self.initialized = True
        else:
            self.update(*args, **kwargs)
        return self.representation(*args, **kwargs)

