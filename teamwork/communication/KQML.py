import socket
import SocketServer
import string
import thread
from threading import *
from types import *
from UserDict import UserDict

from teamwork.communication.generic import *

class KQMLListener(GenericCommunication,SocketServer.ThreadingTCPServer):

    LABEL_REGISTER = 'register'
    
    def __init__(self,args):
        try:
            self.port = int(args['port'])
            port = self.port
        except KeyError:
            self.port = None
            port = 13579
        ok = None
        while not ok:
            try:
                TCPServer.__init__(self,('localhost',port),
                                   KQMLRequestHandler)
                ok = 1
            except socket.error,e:
                if self.port:
                    raise socket.error,e
                else:
                    port = port + 1
        self.port = port
        self.host = socket.gethostname()
        print 'Successful socket bind:',self.socket.getsockname()
        self.lock = Lock()
        self.queue = []
        self.connections = {}
        # If ANS info, then register
        if args.has_key('ANS'):
            addr = args['ANS']
            thread.start_new_thread(self.connect,('ANS',addr))

    def register(self,name):
        try:
            handler = self.connections['ANS']
        except KeyError:
            return None
        handler.send('(register :content ('+name+' '+\
                     self.host+' ' +self.port+') :sender '+name+\
                     ' :reply-with '+self.LABEL_REGISTER+')')
        
    def connect(self,name,addr):
        sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        sock.connect(addr)
        handler = KQMLRequestHandler(sock,addr,self,name)
        
    def start(self):
        self.listener = thread.start_new_thread(self.serve_forever,())

    def send(self,msg):
        if msg.has_key('address'):
            # Message has (host,port) in it
            addr = msg['address']
            del msg['address']
        else:
            # Need to look up (host,port)
            addr = None
        if addr:
            thread.start_new_thread(self.connect,(msg['receiver'],addr))
            ready = None
            while not ready:
                time.sleep(1)
                self.lock.acquire()
                ready = self.connections.has_key(msg['receiver'])
                self.lock.release()
            self.connections[msg['receiver']].send(`msg`)
            
    def addMsg(self,msg):
        self.lock.acquire()
        self.queue.insert(0,msg)
        self.lock.release()

    def receive(self):
        msgs = []
        self.lock.acquire()
        while len(self.queue) > 0:
            msgs.append(self.queue.pop())
        self.lock.release()
        return msgs

    def addConnection(self,name,handler):
        self.lock.acquire()
        self.connections[name] = handler
        self.lock.release()
        
class KQMLRequestHandler(SocketServer.StreamRequestHandler):
    def __init__(self, request, client_address, server,name=None):
        self.name = name
        if self.name:
            server.addConnection(self.name,self)
        SocketServer.BaseRequestHandler.__init__(self, request,
                                                 client_address, server)
        
    def handle(self):
        input = self.rfile.readline()
        while input:
            msg = KQMLMessage(string.strip(input))
            if not self.name and msg.has_key('sender'):
                self.name = msg['sender']
                self.server.addConnection(self.name,self)
            self.server.addMsg(msg)
            input = self.rfile.readline()

    def send(self,str):
        if not type(str) is StringType:
            str = `str`
        self.wfile.write(str+'\r\n')
        
class KQMLMessage(GenericMessage,UserDict):
    def __init__(self,initialdata=None):
        if initialdata:
            if type(initialdata) is StringType:
                UserDict.__init__(self,self.parse(initialdata))
            else:
                UserDict.__init__(self,initialdata)
        else:
            UserDict.__init__(self)

    def parse(self,str):
        # Transforms a string representation of a KQML message into a
        # structured dictionary
        msg = {}
        if str[0] in ['"','(']:
            str = str[1:len(str)-1]
        elements = string.split(string.strip(str))
        depth = 0
        key = None
        content = ''
        for element in elements:
            if depth > 0:
                # Processing multi-word value
                last = len(element) - 1
                if (delimiter == '"' and element[last] == '"') or \
                       delimiter == '(' and element[last] == ')':
                    # Finished with multi-word value
                    content = content + ' ' + element[:last]
                    depth = depth - 1
                else:
                    # Continuing on with multi-word value
                    content = content + ' ' + element
            elif key:
                if element[0] in ['"','(']:
                    # Beginning multi-word value
                    content = element[1:]
                    depth = depth + 1
                    delimiter = element[0]
                else:
                    # Single-word value
                    content = element
            elif element[0] == ':':
                # We have a new key-value pair
                key = element[1:]
            else:
                # Performative appears without a key
                key = 'performative'
                content = element

            if depth == 0 and key and len(content) > 0:
                # Completed one key-value pair
                msg[key] = content
                key = None
                content = ''
        return msg

    def __repr__(self):
        str = ''
        str = '('+self['performative']
        for key,value in self.items():
            if key != 'performative':
                str = str + ' :' + key + ' '
                if ' ' in value:
                    str = str + '(' + value + ')'
                else:
                    str = str + value
        str = str + ')'
        
if __name__ == '__main__':
    import sys
    import time

    args = {}
    try:
        args['port'] = int(sys.argv[1])
    except IndexError:
        pass

    me = KQMLListener(args)
    me.start()
    done = None
    while not done:
        try:
            time.sleep(1)
            print me.receive()
        except KeyboardInterrupt:
            done = 1            
    me.stop()
