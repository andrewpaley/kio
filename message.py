from typing import List

        
class SlackUser:
    def __init__(self, id: str):
        self.id = id
        self.email = None
        self.fname = None
        self.lname = None
        self.phone = None

class Conversation:
    def __init__(self, id: str, present_users: List[SlackUser]):
        self.id = id
        self.present_users = present_users
        
class PublicChannel(Conversation):
    def __init__(self, id: str, present_users: List[SlackUser]):
        Conversation.__init__(self, id, present_users)
          
class PrivateChannel(Conversation):
    def __init__(self, id: str, present_users: List[SlackUser]):
        Conversation.__init__(self, id, present_users)      
        
class IM(Conversation):
    def __init__(self, id: str, present_users: List[SlackUser]):
        Conversation.__init__(self, id, present_users)
        
class Message:
    def __init__(self, text: str, utterer: SlackUser, conversation: Conversation):
        self.text = text
        self.utter = utterer
        self.conversation = conversation