from pythonian import *
import logging
import time
logger = logging.getLogger('KioAgent')

class KioAgent(Pythonian):
    name = "Kio"  # This is the name of the agent to register with

    def __init__(self, **kwargs):
        super(KioAgent, self).__init__(**kwargs)
        self.add_achieve("tell-user", self.tell_kio)
        self.latestResponse = None
        self.responsePending = False

    def insertInfo(self, data):
        self.insert_data('session-reasoner', data)

    def sendMessage(self, msg, msgId, user):
        content = ["interpret", msgId, msg, user]
        self.achieve_on_agent('interaction-manager', content)
        self.responsePending = True

    def tell_kio(self, response):
        print("start dids")
        print(response)
        # this sets the value and Kio is polling every second for it
        # if we can get convo/user ids here, this will be built into a "mailbox" system
        # for now, we don't have that...so we can only handle one convo at a time...
        self.latestResponse = response
        self.responsePending = False
        print("dids")
        return response

if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    kioAgent = KioAgent(host='localhost', port=9000, localPort=8950, debug=True)
