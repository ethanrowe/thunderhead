
import xml.dom.minidom as minidom
import base64

xmlns = 'http://docs.rackspacecloud.com/servers/api/v1.0'

def getServers(conn, since=None):
    (data, code) = conn.request('GET', '/servers/detail')
    nodes = data.getElementsByTagName('server')
    result = [Server.fromXML(node) for node in nodes] if nodes else []
    return result

def getFlavors(conn, since=None):
    (flavors, code) = conn.request('GET', '/flavors/detail')
    result = {}
    for flavor in flavors.getElementsByTagName('flavor'):
        item = dict([
            (key, int(flavor.getAttribute(key))) for key in ['id', 'ram', 'disk']
        ])
        item['name'] = flavor.getAttribute('name')
        result[item['id']] = item
    return result


class Server(object):
    simpleAttributes = ['name', 'status', 'hostId', 'metadata', 'publicIPs', 'privateIPs', 'files']
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
    ]

    def __init__(self, *args, **kwargs):
        for simpleAttr in self.simpleAttributes:
            if kwargs.has_key(simpleAttr): setattr(self, simpleAttr, kwargs[simpleAttr])
        for intAttr in self.integerAttributes:
            if kwargs.has_key(intAttr): setattr(self, intAttr, int(kwargs[intAttr]))

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
                    key = 'publicIPs' if addrs.nodeName == 'public' else 'privateIPs'
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
