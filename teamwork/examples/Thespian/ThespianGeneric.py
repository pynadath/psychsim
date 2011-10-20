__author__ = 'Mei Si <meisi@isi.edu>'


from teamwork.agent.Generic import *

class ThespianGenericModel(GenericModel):
    option_messages = []

    def __init__(self,name=''):
        GenericModel.__init__(self,name)
        self.option_messages = []
        self.real_option_messages = []

    def __repr__(self):
        """Returns a string representation of this entity"""
        content = GenericModel.__repr__(self)
        content += '\n\tOption_messages:\n'
        content += '\t\t'+`self.option_messages`
        return content
    
    def importDict(self,generic):
        """Updates generic model from dictionary-style spec"""
        GenericModel.importDict(self,generic)
        # Option_messages
        if generic.has_key('option_messages'):
            for entry in generic['option_messages']:
                if not entry in self.option_messages:
                    self.option_messages.append(copy.copy(entry))

        if generic.has_key('real_option_messages'):
            for entry in generic['real_option_messages']:
                if not entry in self.real_option_messages:
                    self.real_option_messages.append(copy.copy(entry))


