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

import xml.dom.minidom as minidom
import base64, time, datetime
from thunderhead import CachedResource as BaseCachedResource

def unixNow():
    return int(datetime.datetime.now().strftime('%s'))

class CachedResource(BaseCachedResource):
    timestamp = None
    interval = 60

    def __init__(self, basefunc):
        self.baseFunction = basefunc

    def merge(self, values):
        newset = dict(self.asset or {})
        for key, value in values.iteritems():
            if getattr(value, 'status', None) == 'DELETED' or (
                hasattr(value, 'has_key') and value.has_key('status') and value['status'] == 'DELETED'
            ):
                newset.pop(key, None)
            else:
                newset[key] = value
        return newset

    def needsUpdate(self):
        return self.timestamp and (self.timestamp + self.interval) <= unixNow()

    def initialize(self, *args, **kwargs):
        self.timestamp = unixNow()
        self.asset = self.baseFunction(*args, **kwargs)

    def update(self, *args, **kwargs):
        if self.needsUpdate():
            timestamp = unixNow()
            self.asset = self.merge(self.baseFunction(*args, **dict({'since': self.timestamp}, **kwargs)))
            self.timestamp = timestamp
        

xmlns = 'http://docs.rackspacecloud.com/servers/api/v1.0'

serverManagementInterface = [
    {'name': 'Server', 'wrapper': None},
    'createServer',
    'createSharedIPGroup',
    'deleteServer',
    'deleteSharedIPGroup',
    {'name': 'getFlavors', 'wrapper': CachedResource},
    {'name': 'getImages', 'wrapper': CachedResource},
    'getPublicIPs',
    {'name': 'getServers', 'wrapper': CachedResource},
    'getSharedIPGroups',
    'shareIP',
]

def queryString(since):
    return (since and '?changes-since=' + str(since)) or ''

def deleteServer(conn, server):
    (body, code) = conn.request('DELETE', '/servers/' + server)
    return code

def deleteSharedIPGroup(conn, group):
    (body, code) = conn.request('DELETE', '/shared_ip_groups/' + group)
    return code

def getSharedIPGroups(conn):
    (data, code) = conn.request('GET', '/shared_ip_groups')
    if data:
        nodes = data.getElementsByTagName('sharedIpGroup')
        result = ((nodes and [SharedIPGroup.fromXML(node) for node in nodes]) or [])
        result = dict([(s.id, s) for s in result])
    else:
        result = {}
    return result

def createSharedIPGroup(conn, sharedipgroup):
    (data, code) = conn.request('POST', '/shared_ip_groups', sharedipgroup.toXML())
    return data

def shareIP(conn, sharedip, serverId, address):
    (body, code) = conn.request('PUT', '/servers/' + serverId + '/ips/public/' + address, sharedip.toXML())
    return code

# This just dumbly fetches public IPs for the moment
# TODO: figure out a way to determine whether an IP has been shared or not
def getPublicIPs(conn, server):
    (ips, code) = conn.request('GET', '/servers/' + server + '/ips/public')
    return manualIndexedChildHash(
        ips,
        'ip',
        {
            'addr': str,
        },
    )

def getServers(conn, since=None):
    (data, code) = conn.request('GET', '/servers/detail' + queryString(since))
    if data:
        nodes = data.getElementsByTagName('server')
        result = ((nodes and [Server.fromXML(node) for node in nodes]) or [])
        result = dict([(s.id, s) for s in result])
    else:
        result = {}
    return result

def createServer(conn, server):
    (created, code) = conn.request('POST', '/servers', server.toXML())
    return Server.fromXML(created)

def deleteServer(conn, server):
    (result, code) = conn.request('DELETE', '/servers/' + str(getattr(server, 'id', server)))
    return True

def attributeHash(node, attrs):
    ident = lambda (x): x
    return dict([
        (k, (t or ident)(node.getAttribute(k))) for (k, t) in attrs.iteritems() if node.hasAttribute(k)
    ])

def indexedChildHash(node, tag, attrs):
    result = {}
    if node:
        for child in node.getElementsByTagName(tag):
            item = attributeHash(child, attrs)
            result[item['id']] = item
    return result

def manualIndexedChildHash(node, tag, attrs):
    result = {}
    myid = 1
    for child in node.getElementsByTagName(tag):
        item = attributeHash(child, attrs)
        result[myid] = item
        myid += 1
    return result
 
 
def getFlavors(conn, since=None):
    (flavors, code) = conn.request('GET', '/flavors/detail' + queryString(since))
    return indexedChildHash(
        flavors,
        'flavor',
        {
            'id': int, 
            'ram': int,
            'disk': int,
            'name': False,
        },
    )

# timezones are a mess, so for now, we'll leave these as strings.
def convertTimestamp(ts):
    return str(ts)

def getImages(conn, since=None):
    (images, code) = conn.request('GET', '/images/detail' + queryString(since))
    return indexedChildHash(
        images,
        'image',
        {
            'id': int,
            'name': str,
            'status': str,
            'updated': convertTimestamp,
            'created': convertTimestamp,
            'progress': int,
            'serverId': int,
        },
    )


class APIObject(object):
    simpleAttributes = []
    integerAttributes = []
    xmlAttributes = []

    def __init__(self, *args, **kwargs):
        self.initializeAttributes(*args, **kwargs)

    def initializeAttributes(self, *args, **kwargs):
        for simpleAttr in self.simpleAttributes:
            if kwargs.has_key(simpleAttr): setattr(self, simpleAttr, kwargs[simpleAttr])
        for intAttr in self.integerAttributes:
            if kwargs.has_key(intAttr): setattr(self, intAttr, int(kwargs[intAttr]))

class Server(APIObject):
    simpleAttributes = ['name', 'status', 'hostId', 'metadata', 'publicIPs', 'privateIPs', 'files', 'adminPass']
    integerAttributes = ['id', 'imageId', 'flavorId', 'progress', 'sharedIpGroupId']
    xmlAttributes = [
        'name',
        'status',
        'hostId',
        'id',
        'imageId',
        'flavorId',
        'progress',
        'sharedIpGroupId',
        'adminPass',
    ]

    @classmethod
    def fromXML(self, xml):
        hash = dict([(str(attr.name), attr.value) for attr in xml.attributes.values()])
        data = dict([(node.nodeName, node) for node in xml.childNodes])
        meta = data.has_key('metadata') and data['metadata'].getElementsByTagName('meta')
        if meta:
            hash['metadata'] = dict([
                (n.getAttribute('key'), n.firstChild and n.firstChild.data) for n in meta
            ])
        if data.has_key('addresses') and data['addresses'].hasChildNodes():
            for addrs in data['addresses'].childNodes:
                if hasattr(addrs, 'nodeName') and hasattr(addrs, 'getElementsByTagName'):
                    key = ((addrs.nodeName == 'public' and 'publicIPs') or 'privateIPs')
                    ips = addrs.getElementsByTagName('ip')
                    if ips:
                        hash[key] = [ip.getAttribute('addr') for ip in ips]
        return self(**hash)

    def toXML(self):
        doc = minidom.Document()
        node = minidom.Element('server')
        node.setAttribute('xmlns', xmlns)
        for attr in self.xmlAttributes:
            if hasattr(self, attr):
                node.setAttribute(attr, str(getattr(self, attr)))
        addr = minidom.Element('addresses')
        for (attr, name) in (('privateIPs', 'private'), ('publicIPs', 'public')):
            if hasattr(self, attr):
                addrList = minidom.Element(name)
                for ip in getattr(self, attr):
                    ipNode = minidom.Element('ip')
                    ipNode.setAttribute('addr', ip)
                    addrList.appendChild(ipNode)
                if addrList.hasChildNodes(): addr.appendChild(addrList)
        if addr.hasChildNodes(): node.appendChild(addr)
        if hasattr(self, 'metadata'):
            meta = minidom.Element('metadata')
            for (key, val) in self.metadata.iteritems():
                metaNode = minidom.Element('meta')
                metaNode.setAttribute('key', key)
                metaNode.appendChild(doc.createTextNode(val))
                meta.appendChild(metaNode)
            if meta.hasChildNodes(): node.appendChild(meta)
        if hasattr(self, 'files'):
            personality = minidom.Element('personality')
            for (key, val) in self.files.iteritems():
                fileNode = minidom.Element('file')
                fileNode.setAttribute('path', key)
                fileNode.appendChild(doc.createTextNode(base64.encodestring(val)))
                personality.appendChild(fileNode)
            if personality.hasChildNodes(): node.appendChild(personality)
        return node 

class SharedIP(APIObject):
    simpleAttributes = ['configureServer']
    integerAttributes = ['sharedIpGroupId']
    xmlAttributes = ['configureServer', 'sharedIpGroupId']

    def toXML(self):
        doc = minidom.Document()
        node = minidom.Element('shareIp')
        node.setAttribute('xmlns', xmlns)
        for attr in self.xmlAttributes:
            if hasattr(self, attr):
                node.setAttribute(attr, str(getattr(self, attr)))
        return node


class SharedIPGroup(APIObject):
    simpleAttributes = ['name']
    integerAttributes = ['id']
    xmlAttributes = ['name', 'id']

    def __init__(self, *args, **kwargs):
        self.initializeAttributes(*args, **kwargs)
        servers = (kwargs.has_key('servers') and dict(zip(kwargs['servers'], [1] * len(kwargs['servers'])))) or {}
        if kwargs.has_key('server_id'): servers[kwargs['server_id']] = 1
        servers = servers.keys()
        servers.sort()
        self.servers = servers

    def _XMLifyServer(self, id):
        server = minidom.Element('server')
        server.setAttribute('id', str(id))
        return server

    def toXML(self):
        doc = minidom.Document()
        node = minidom.Element('sharedIpGroup')
        node.setAttribute('xmlns', xmlns)
        for attr in self.xmlAttributes:
            if hasattr(self, attr):
                node.setAttribute(attr, str(getattr(self, attr)))
        if len(self.servers) > 0:
            if len(self.servers) == 1:
                servers = self._XMLifyServer(self.servers[0])
            else:
                servers = minidom.Element('servers')
                for id in self.servers:
                    servers.appendChild(self._XMLifyServer(id))
            node.appendChild(servers)
        return node

    @classmethod
    def fromXML(self, xml):
        hash = dict([(str(attr.name), attr.value) for attr in xml.attributes.values()])
        data = dict([(node.nodeName, node) for node in xml.childNodes])
        servers = None
        if data.has_key('server'):
            servers = [int(data['server'].getAttribute('id'))]
        elif data.has_key('servers'):
            servers = [int(server.getAttribute('id')) for server in data['servers'].getElementsByTagName('server')]
        if servers: hash['servers'] = servers
        return self(**hash)

