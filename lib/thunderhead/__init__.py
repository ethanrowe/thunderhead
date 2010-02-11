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
                info = (hasattr(item, 'has_key') and item) or {'name': item}
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

class Role(object):
    """
NAME
    Role

DESCRIPTION
    The Role class represents a "role" within your cloud operations.

    This allows you to design common server configurations -- consisting of
    image, flavor, properties, etc. -- for reuse within your operations at
    a higher level than basic images.

IMPLEMENTING ROLES
    To implement a role, you need to do a couple of basic things:

    1. Inherit from thunderhead.Role

    2. Define the "serverDefaults" attribute in your class; this should be a dictionary
    of keyword arguments that would get passed to account.Server() under the hood

    3. Define the "isMember" method in your class; this should, given a server object,
    return True/False depending on whether or not the server has the role represented
    by your class.

    4. Define the account to use in association with this role, as the "account"
    attribute.

    5. Optionally, define the "initServer" method which, given a new server object as
    input, can modify that server object in arbitrary ways.  The result of this method
    will be the result of the Server() call on the role class.

    For now, things should be set at the class level.

METHODS
    Server(): invoke to create a new server object configured for use as the role in question.

    getServers(): return the dictionary of servers implementing this role.

    createServer(server): convenience function to pass through the server object <server>
    to account.createServer().

    """

    serverDefaults = {}
    account = None
    @classmethod
    def serverInit(self, server): return server
    
    @classmethod
    def Server(self, *args, **kwargs):
        server = self.account.Server(*args, **dict(self.serverDefaults, **kwargs))
        return self.serverInit(server)

    @classmethod
    def getServers(self, *args, **kwargs):
        servers = self.account.getServers(*args, **kwargs)
        return dict([(id, s) for id, s in servers.iteritems() if self.isMember(s)])

    @classmethod
    def isMember(self, server): return False

    @classmethod
    def createServer(self, *args, **kwargs):
        return self.account.createServer(*args, **kwargs)

