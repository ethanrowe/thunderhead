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
            for func in interface:
                setattr(self, func, self._wrapMethod(getattr(provider.api, func)))
        return self.provider

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

