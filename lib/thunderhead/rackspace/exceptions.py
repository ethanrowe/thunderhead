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
for fault in faultList:
    klass = type(fault[0].upper() + fault[1::] + 'Exception', (RackspaceException,), {'fault': fault})
    globals()[klass.__name__] = klass
    registerHandler(fault, klass)

