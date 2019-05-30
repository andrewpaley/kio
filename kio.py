import asyncio
from threading import Timer
import os
from random import randint
import time

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
        # some flags to see if we're taking a while to respond
        self.timeOfLastInput = None
        self.responsePending = False
        self.responseCheckerLoop = 0
        self.responseChecker = RepeatedTimer(2, self.responseStatusCheck, self)
        # grab or create a slack client to send message back
        slackToken = os.environ.get('SLACK_BOT_TOKEN')
        self.slackClient = slackClient if slackClient is not None else SlackClient(slackToken)
        self.utteranceid = 1

    def receiveMessage(self, message, user):
        # we're blocking on new messages if there's already a message, right?
        # if so:
        if self.responsePending:
            self.sendMessage("Sorry, I'm still thinking about the last request. One moment.")
            return None
        # message received -- fire it up
        self.responseInitiated()
        # now do the message passing
        self.messageHistory.append(message.text)
        self.sendMessageToCompanions(message.text, user)
        self.respond(message.text)

    def responseInitiated(self):
        self.timeOfLastInput = time.time()
        self.responsePending = True
        self.responseCheckerLoop = 0
        self.responseChecker.start()

    def responseComplete(self):
        self.responsePending = False
        self.responseChecker.stop()
        self.responseCheckerLoop = 0

    def respond(self, message):
        response = self.generateResponse(message)
        print("responding {0} in {1}".format(response, self.conversation.id))
        self.sendMessage(response)
        self.responseComplete()

    def sendMessage(self, message):
        self.slackClient.api_call(
            "chat.postMessage",
            channel=self.conversation.id,
            text=message
        )

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

    def responseStatusCheck(self):
        # this will get called every two seconds once a message is received
        # currently it just tracks the length of time until a response and provides user a sense that it's working
        # maybe also could poll companions and actually get the reply?
        # TODO
        if self.responsePending:
            if self.responseCheckerLoop == 1:
                self.sendMessage("This one's taking me a moment.")
            elif self.responseCheckerLoop == 5:
                self.sendMessage("Hm. Sorry, this might take more than a moment.")
            elif self.responseCheckerLoop > 15:
                # we should probably bail now, right? it's been 30 seconds
                self.sendMessage("My apologies, I can't answer that for you at the moment.")
                self.responseComplete()
            self.responseCheckerLoop += 1
        else:
            self.responseChecker.stop()

    def sendMessageToCompanions(self, message, user):
        self.agent.sendMessage(message, self.utteranceid, user)
        self.utteranceid += 2

# leveraged from here (nonblocking loop w/ sleep):
# https://stackoverflow.com/questions/474528/what-is-the-best-way-to-repeatedly-execute-a-function-every-x-seconds-in-python
class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer     = None
        self.interval   = interval
        self.function   = function
        self.args       = args
        self.kwargs     = kwargs
        self.is_running = False

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False
