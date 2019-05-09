import os
import time
import re

from slackclient import SlackClient
from message import *

from kio import Kio
from agent import KioAgent


class KioManager(object):
    '''The chat stream manager -- gets instantiated on program start. Polls the slack api at
    regular interval (self.readDelay) for new messages, and susses out if they're @Kio or to
    Kio in a DM. If so, manages the message passing to the appropriate (new or existing,
    if ongoing conversation) Kio instance.'''
    def __init__(self, agent=None):
        self.agent = agent
        self.readDelay = 1 # 1 second delay between reading from RTM
        self.kios = {} # agents for each conversation
        self.slackClient = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))
        
        # populate known conversations
        self.queryConversations()
        # ...and start message polling
        self.startSlackPolling()
        
    def startSlackPolling(self):
        # start polling the slack api
        if self.slackClient.rtm_connect(with_team_state=False):
            print("Connected to Slack.")
            self.kioID = self.slackClient.api_call("auth.test")["user_id"]
            while True:
                for event in self.slackClient.rtm_read():
                    # parse it for relevance...
                    # if relevant, this will pass on to a Kio
                    self.routeNewMessage(event)
                    # TODO: should we sleep if the event isn't a message?
                    time.sleep(self.readDelay)
        else:
            print("ERROR: Couldn't connect to Slack.")

    def queryConversations(self):
        response = self.slackClient.api_call("conversations.list", types=["public_channel",
                                                                         "private_channel",
                                                                         "im",
                                                                         "mpim"])
        if response['ok']:
            self.conversations = response['channels']
        else:
            print("Error getting conversations:")
            print(response)

    def getConversation(self, id):
        for conversation in self.conversations:
            if conversation['id'] == id:
                if conversation['is_im']:
                    context = IM
                    user_ids = [conversation['user']]
                elif conversation['is_channel']:
                    context = PublicChannel
                    user_ids = self.slackClient.api_call("conversations.members", channel=id)
                elif conversation['is_group']:
                    context = PrivateChannel # also encompasses multi-person IMs
                    user_ids = self.slackClient.api_call("conversations.members", channel=id)
                else:
                    raise ValueError()
                    
                break
        
        
        users = [SlackUser(id) for id in user_ids]
        return context(id, users)
    
    def routeNewMessage(self, event, retry=False):
        # parses a new message
        # if relevant, it'll pass it on to self.sendToKio with pertinent details
        # or NOOP if message isn't relevant
        # https://api.slack.com/events/message
        if event["type"] == "message" and not "subtype" in event:
            # are they @ing kio in a regular channel?
            user_id = event["user"]
            message_text = event["text"]
            conversation_id = event["channel"]
            
            user = SlackUser(user_id)
            conversation = self.getConversation(conversation_id)
            message = Message(message_text, user, conversation)
            print("Got {0} in a {1}".format(message.text, type(conversation).__name__))
            if type(conversation) == IM:
                print("Got {0} in a {1}".format(message.text, type(conversation).__name__))
                self.sendToKio(message)
            elif type(conversation) == PrivateChannel:
                # TODO: get this value dynamically, it's the user id of KIO
                if "<@UJ5HZANNR>" not in message.text: # make sure we're being addressed
                    return False
                else:
                    print("Got {0} in a {1}".format(message.text, type(conversation).__name__))
                    self.sendToKio(message)
            elif type(conversation) == PublicChannel:
                if "<@UJ5HZANNR>" not in message.text: # make sure we're being addressed
                    return False
                else:
                    print("Got {0} in a {1}".format(message.text, type(conversation).__name__))
                    self.sendToKio(message)
                
            return True

    def sendToKio(self, message):
        # is there already a Kio for this convo? if no, make one
        if message.conversation.id not in self.kios:
            # new up a Kio and store it
            # pass in the slackClient so we don't make new ones unnecessarily
            # undo if this bottlenecks
            newKio = Kio(message.conversation,
                         agent = self.agent,
                         slackClient = self.slackClient)
            self.kios[message.conversation.id] = newKio
        # now send the message on
        self.kios[message.conversation.id].receiveMessage(message)

    def getUserDetails(self, userID):
        userPayload = self.slackClient.api_call("users.info", user=userID)
        print(userPayload)
        name = userPayload["user"]["name"]
        fullName = userPayload["user"]["real_name"]
        firstName = fullName.split(" ")[0]
        email = userPayload["user"]["profile"]["email"]
        output = {
            "id": userID,
            "fullName": fullName,
            "firstName": firstName,
            "email": email,
            "handle": name
        }
        return output

if __name__ == "__main__":
    kioAgent = KioAgent(host='localhost', port=9000, localPort=8952, debug=True)
    km = KioManager(agent=kioAgent)
