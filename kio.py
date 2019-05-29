import os
from random import randint

from slackclient import SlackClient

from quotes import QUOTES

QUOTE_COUNT = len(QUOTES)

class Kio(object):
    '''The Kio class. The KioManager will instantiate one of these for each discrete conversation.
    We can hang whatever ephemeral state we want to here (but if it requires persistence, that goes
    elsewhere). It also handles any surface-level intent parsing/quick replies, message passing down
    to companions, as well as replying out to the Slack API once a reply has been handed back.'''
    def __init__(self, conversation, agent, slackClient=None):
        self.conversation = conversation
        # TODO: how do we want to handle this? Also, should we store both ways or just inbound?
        self.messageHistory = []        
        self.agent = agent
        # grab or create a slack client to send message back
        slackToken = os.environ.get('SLACK_BOT_TOKEN')
        self.slackClient = slackClient if slackClient is not None else SlackClient(slackToken)
        self.utteranceid = 1

    def receiveMessage(self, message, user):
        self.messageHistory.append(message.text)
        self.sendMessageToCompanions(message.text, user)
        self.respond(message.text)

    def respond(self, message):
        response = self.generateResponse(message)
        print("responding {0} in {1}".format(response, self.conversation.id))
        self.slackClient.api_call(
            "chat.postMessage",
            channel=self.conversation.id,
            text=response
        )
    def sendMessageToCompanions(self, message, user):
        self.agent.sendMessage(message, self.utteranceid, user)
        self.utteranceid += 2


    def generateResponse(self, message):
        # TODO: implement the basic check that would get routed right out to response
        # TODO: implement the bridge to the pythonian/companions jazz here.
        # likely involves passing message, user id (self.op["id"]), and...?
        # also involves getting a response and routing to self.respond
        response = None

        message = message.lower()

        if message.startswith("help"):
            response = "Sorry, you're kinda on your own at the moment!"

        if message.startswith("thank"):
            response = "You're very welcome!"

        if not response:
            quote = QUOTES[randint(0,QUOTE_COUNT-1)]
            starters = [
                        "Sorry, under construction. In the meantime, fun fact: ",
                        "Yup, I'm super unhelpful at this point. But hey, ",
                        "AFK. Also, ",
                        "I can't understand you, sorry, but I can tell you that "
                    ]
            response = starters[randint(0,len(starters)-1)] + \
              quote["author"] + " once said \"" + quote["quote"] + "\""

        return response
