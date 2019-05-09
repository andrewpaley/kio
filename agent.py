from pythonian import *
import logging
import time
logger = logging.getLogger('KioAgent')


class KioAgent(Pythonian):
    name = "Kio"  # This is the name of the agent to register with

    def __init__(self, **kwargs):
        super(KioAgent, self).__init__(**kwargs)
        self.add_achieve("tell_kio", self.tell_kio)

    def insertInfo(self, data):
        Pythonian.insert_data(self,'session-reasoner', data)
        
    def sendMessage(self, msg, msgId):
        content = ["interpret", msgId, msg]
        Pythonian.achieve_on_agent(self,'interaction-manager', content)

# def instantiate():
#     kio = KioAgent(host='localhost',port=9000, localPort=8951, debug=True)
#     return kio

    def tell_kio(self, response):
        print(response)
        return response

if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    kioAgent = KioAgent(host='localhost', port=9000, localPort=8951, debug=True)
    # a.test_insert_to_Companion('(started TestAgent)')
    # time.sleep(10)
    # kioAgent.more_junk_mail('Click here for...')
    # time.sleep(10)
    # kioAgent.more_junk_mail('You have won!  Just send your SSN to us and we will send you the money')