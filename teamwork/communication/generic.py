class GenericCommunication:

    def start(self):
        pass

    def stop(self):
        pass

    def send(self,msg):
        raise NotImplementedError

    def receive(self):
        return []
    
class GenericMessage:

    def content(self):
        return ''
    
