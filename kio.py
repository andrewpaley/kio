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
        # some flags to manage response loop
        self.timeOfLastInput = None
        self.responsePending = False
        self.responseCheckerLoop = 0
        self.responseChecker = RepeatedTimer(1, self.responseStatusCheck, self)
        # grab or create a slack client to send message back
        slackToken = os.environ.get('SLACK_BOT_TOKEN')
        self.slackClient = slackClient if slackClient is not None else SlackClient(slackToken)
        self.utteranceid = 1

    def receiveMessage(self, message, user):
        # we're blocking on new messages if there's already a message, right?
        # and that includes messages from this or TEMPORARILY any Kio (so KioAgent doesn't get gummed up)
        # so we can only currently support one Kio convo at a time ACROSS ALL CONVERSATIONS
        # if so:
        if self.responsePending:
            self.sendMessage("Sorry, I'm still thinking about the last request. One moment.")
            return None
        if self.agent.responsePending or self.agent.latestResponse:
            # if the former, KioAgent is waiting on a response from companion
            # if the latter, KioAgent has a response and someone (another Kio) needs to pick it up
            # this could be reimplemented as a queue, but likely better to suss out multiple i/o on agent
            # side rather than manage lists across Kio instances
            self.sendMessage("Sorry, I'm busy at the moment. Please try again shortly.")
        # now do the message passing
        self.messageHistory.append(message.text)
        self.sendMessageToCompanions(message.text, user)
        # self.respond(message.text)
        # message received -- fire it up
        self.responseInitiated()

    def responseInitiated(self):
        self.timeOfLastInput = time.time()
        self.responsePending = True
        self.responseCheckerLoop = 0
        self.responseChecker.start()

    def responseComplete(self):
        # turn off the flags on the KioAgent
        if self.agent.latestResponse:
            self.agent.latestResponse = None
        if self.agent.responsePending:
            self.agent.responsePending = False
        # now reset the flags here
        self.responsePending = False
        self.responseChecker.stop()
        self.responseCheckerLoop = 0

    def respond(self, message):
        print("responding {0} in {1}".format(response, self.conversation.id))
        self.sendMessage(message)
        self.responseComplete()

    def sendMessage(self, message):
        self.slackClient.api_call(
            "chat.postMessage",
            channel=self.conversation.id,
            text=message
        )

    def responseStatusCheck(self):
        # this will get called every second once a message is received
        # it keeps track of if a response is taking a while and will also poll
        # the kio agent to see if agent.latestResponse exists...if so, it's the reply
        # there would be better ways to do this if we had message ids coming back from
        # companions -- 1) register each kio in a dict in KioAgent by convo ID and route
        # as appropriate as a lookup in tell_kio from KioAgent, or 2) do something like
        # the below, except it's not a single value, it's a set of "mailboxes" by convo id
        if self.responsePending:
            if self.agent.latestResponse:
                # a response is there...we're done...
                # this call should 1) send the response and
                # 2) stop this loop from continuing
                self.respond(self.agent.latestResponse)
                return False
            elif self.responseCheckerLoop == 2:
                self.sendMessage("Um, one moment...")
            elif self.responseCheckerLoop == 8:
                self.sendMessage("Hm. Sorry, this might take more than a moment.")
            elif self.responseCheckerLoop > 30:
                # we should probably bail now, right? it's been 30 seconds
                self.sendMessage("My apologies, I guess I can't answer that for you at the moment.")
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
