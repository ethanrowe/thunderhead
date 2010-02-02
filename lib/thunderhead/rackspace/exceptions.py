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

_typeRegistry = {}

def registerHandler(type, klass):
    _typeRegistry[type] = klass
    return klass

def handlerFor(type):
    return ((_typeRegistry.has_key(type) and _typeRegistry[type]) or None)

def throw(type, *args):
    klass = handlerFor(type) or UnknownExceptionType
    raise klass(*args)

class RackspaceException(Exception): pass
class BadCredentialsException(RackspaceException): pass
class UnknownExceptionType(RackspaceException): pass

# base list of Rackspace Cloud Servers faults; each maps
# to a similarly-named exception (e.g. "cloudServersFault" => "CloudServersFaultException")
faultList = [
    'cloudServersFault',
    'serviceUnavailable',
    'unauthorized',
    'badRequest',
    'overLimit',
    'badMediaType',
    'badMethod',
    'itemNotFound',
    'buildInProgress',
    'serverCapacityUnavailable',
    'backupOrResizeInProgress',
    'resizeNotAllowed',
    'notImplemented',
]

# build out the exception classes from the base list
# Note support for 2.4 annoyances.  Curse you, RHEL/CentOS 5.x!

import sys
_useOldClasses = sys.version_info[0:2] < (2, 5)
for fault in faultList:
    if _useOldClasses:
        klassname = fault[0].upper() + fault[1::] + 'Exception'
        exec 'class ' + klassname + '(RackspaceException): pass'
        klass = globals()[klassname]
        setattr(klass, 'fault', fault)
    else:
        klass = type(fault[0].upper() + fault[1::] + 'Exception', (RackspaceException,), {'fault': fault})
        globals()[klass.__name__] = klass
    registerHandler(fault, klass)

