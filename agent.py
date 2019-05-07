from pythonian import *
import logging
import time
logger = logging.getLogger('KioAgent')


class KioAgent(Pythonian):
    name = "Kio"  # This is the name of the agent to register with

    def __init__(self, **kwargs):
        super(KioAgent, self).__init__(**kwargs)
        self.add_achieve("export", self.export)
        self.add_ask('test_junk_mail', self.test_junk_mail, '(test_junk_mail ?x)', True)

    def test_junk_mail(self, data):
        logger.debug('testing inserting data into Companion with data: ' + str(data))
        return "Send a million dollars to this address"

    def more_junk_mail(self, data):
        logger.debug('more junk mail has arrived')
        self.update_query('(test_junk_mail ?x)', data)

    def export(self):
        logger.debug('Testing achieve export')

    def insertInfo(self, data):
        Pythonian.insert_data(self,'session-reasoner', data)


def instantiate():
    kio = KioAgent(host='localhost',port=9000, localPort=8951, debug=True)
    return kio



if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    kioAgent = KioAgent(host='localhost', port=9000, localPort=8951, debug=True)
    # a.test_insert_to_Companion('(started TestAgent)')
    # time.sleep(10)
    # kioAgent.more_junk_mail('Click here for...')
    # time.sleep(10)
    # kioAgent.more_junk_mail('You have won!  Just send your SSN to us and we will send you the money')