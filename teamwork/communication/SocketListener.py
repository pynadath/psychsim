import os
import re
import select
import socket
import string
import sys
import thread
import time
from types import *
import SocketServer
from xml.dom.minidom import parseString
from teamwork.communication.generic import *

def getANS():
    """Returns host and port of ANS, as set in KQML_ANS environment
    variable, or as in default setting if no environment variable set"""
    host = 'vibhagam.isi.edu'
    port = 5500
    try:
        exp = re.match("(.*):(.*)",os.environ['KQML_ANS'])
        if exp:
            host = exp.group(1)
            prot = int(exp.group(2))
    except KeyError:
        pass
    return host,port

myClass = SocketServer.ThreadingTCPServer

class KQMLListener(GenericCommunication,myClass):
    port = 1200

    def __init__(self,args={}):
        try:
            port = args['port']
        except KeyError:
            port = KQMLListener.port
        self.connections = {}
        self.queue = []
        self.handlers = []
	self.lock = thread.allocate_lock()
        # Start server on first available port
        while 1:
            try:
                myClass.__init__(self,('127.0.0.1',port),KQMLConn)
                break
            except socket.error:
                port += 1
        print 'Listening on',self.server_address

    def start(self):
        thread.start_new_thread(self.serve_forever,())
        
    def addMsg(self,str,conn=None):
        if conn:
            name = conn.label()
        else:
            name = None
        self.lock.acquire()
        self.queue.insert(0,(name,str))
        self.lock.release()
        print 'New msg:',str
        for handler in self.handlers:
            apply(handler,([(name,str)],))

    def registerHandler(self,fun):
        self.handlers.append(fun)
        
    def receive(self):
        self.lock.acquire()
        msgs = self.queue[:]
        self.queue = []
        self.lock.release()
        return msgs

    def send(self,addr,str,retry=1):
        try:
            print 'Sending to:',addr
            conn = self.connections[addr]
        except KeyError:
            for res in socket.getaddrinfo(addr[0], addr[1],
                                          socket.AF_UNSPEC,socket.SOCK_STREAM):
                af, socktype, proto, canonname, sa = res
                try:
                    sock = socket.socket(af, socktype, proto)
                except socket.error, msg:
                    sock = None
                    continue
                try:
                    sock.connect(sa)
                except socket.error, msg:
                    sock.close()
                    sock = None
                    continue
                break
            else:
                print 'Unable to open socket'
                return None
##            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
##            sock.connect(addr)
            self.process_request(sock,addr)
            for count in range(10):
                if self.connections.has_key(addr):
                    break
                time.sleep(1)
            else:
                print 'Unable to connect:',addr
                return None
            conn = self.connections[addr]
        try:
            conn.sendMsg(str)
        except ValueError:
            del self.connections[addr]
            if retry:
                self.sendMsg(addr,str,None)
            else:
                print 'Unable to send message.'
        return conn

    def stop(self):
        self.server_close()
        
    def server_close(self):
        for conn in self.connections.values():
            try:
                conn.close()
            except socket.error:
                pass
        myClass.server_close(self)
        print 'Listener closed.'
        
class KQMLConn(SocketServer.BaseRequestHandler):
    def handle(self):
        self.name = None
        print 'New connection:',self.client_address
        self.server.connections[self.label()] = self
        self.running = 1
        while self.running:
            time.sleep(1)
            infd,outfd,errfd = select.select([self.request],[self.request],
                                             [self.request])
            if self.request in infd:
                try:
                    data = os.read(self.request.fileno(),16384)
                except OSError:
                    data = None
                if data:
                    self.server.addMsg(string.strip(data),self)
                else:
                    self.close()
        print 'Connection closed:',self.label()
                
    def sendMsg(self,str):
        os.write(self.request.fileno(),str+'\n\r')
        print 'Message sent'

    def label(self):
        if not self.name:
            self.name = self.request.getpeername()
        return self.name

    def close(self):
        del self.server.connections[self.label()]
        self.running = None
        
def printTree(doc):
    str = '\n'+doc.nodeName
    if doc.hasChildNodes():
        node = doc.firstChild
        while node:
            substr = printTree(node)
            str += substr.replace('\n','\n\t')
            node = node.nextSibling
    return str

def interactive(router):
    router.registerHandler(lambda m: sys.stdout.write(`m`+'\n'))
    router.start()
    addr = None
    while 1:
        str = sys.stdin.readline()
        str = string.strip(str)
        if str == 'quit':
            break
        elif str == 'get':
            msgs = router.receive()
            print msgs
        elif str == 'reply':
            addr = msgs[0][0]
        else:
            if not addr:
                pos = string.index(str,' ')
                addr = ('127.0.0.1',int(str[:pos]))
                str = str[pos+1:]
            router.send(addr,str)
            addr = None
    
if __name__ == "__main__" :
    import time

    args = {}
    try:
        args['port'] = int(sys.argv[1])
    except IndexError:
        pass
    router = KQMLListener(args)
    
    try:
        interactive(router)
    except KeyboardInterrupt:
        pass
    router.server_close()
