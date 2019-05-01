import os
import time
import re

from slackclient import SlackClient

from kio import Kio

class KioManager(object):
    '''The chat stream manager -- gets instantiated on program start. Polls the slack api at
    regular interval (self.readDelay) for new messages, and susses out if they're @Kio or to
    Kio in a DM. If so, manages the message passing to the appropriate (new or existing,
    if ongoing conversation) Kio instance.'''
    def __init__(self):
        # some useful constants
        self.readDelay = 1 # 1 second delay between reading from RTM
        self.mentionRegex = "^<@(|[WU].+?)>(.*)"
        # a placeholder for future Kios
        self.kios = {}
        # new up a slack client...
        self.slackClient = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))
        # populate known conversations (in self.knownDMs and self.knownChannels)
        self.refreshKnownConversations()
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
                    time.sleep(self.readDelay)
        else:
            print("ERROR: Couldn't connect to Slack.")

    def refreshKnownConversations(self):
        # repopulate the known conversations in the slack app
        # I think there is a better way to do this...works for now
        self.knownDMs = self.slackClient.api_call("im.list")
        self.knownChannels = self.slackClient.api_call("conversations.list")

    def routeNewMessage(self, event, retry=False):
        # parses a new message
        # if relevant, it'll pass it on to self.sendToKio with pertinent details
        # or NOOP if message isn't relevant
        if event["type"] == "message" and not "subtype" in event:
            # are they @ing kio in a regular channel?
            user_id, message = self.parseDirectMention(event["text"])
            if user_id == self.kioID:
                # TODO: later figure out how to get the name of speaker if the context is a channel
                self.sendToKio(message, event["channel"], False, None)
            # or maybe they're DMing to Kio (this is weird. could use a refactor.)
            if "channel" in event:
                matchedDM = next((dm for dm in self.knownDMs["ims"] if dm["id"] == event["channel"]), None)
                if matchedDM:
                    # okay, it's a DM that kio has access to...so it's probably a DM to kio (?)
                    # to be sure, make sure that kio is in the members and that there's only one other...
                    members = self.slackClient.api_call("conversations.members", channel=matchedDM["id"])["members"]
                    members.remove(self.kioID)
                    if len(members) == 1:
                        self.sendToKio(event["text"], event["channel"], True, members[0])
                elif not matchedDM and retry == False:
                    # just double check it's not a new DM since your last refresh...
                    self.refreshKnownConversations()
                    # then recurse to see if you have it now...if not this will push back a None, None, None
                    self.routeNewMessage(event, True)

    def parseDirectMention(self, msgText):
        matches = re.search(self.mentionRegex, msgText)
        # the first group contains the username, the second group contains the remaining message
        return (matches.group(1), matches.group(2).strip()) if matches else (None, None)

    def sendToKio(self, message, channel, isDM=False, userID=None):
        # is there already a Kio for this convo? if no, make one
        if channel not in self.kios:
            # it's new...are there user details to suss out?
            op = self.getUserDetails(userID) if userID else None
            # new up a Kio and store it
            # pass in the slackClient so we don't make new ones unnecessarily
            # undo if this bottlenecks
            newKio = Kio(channel, op, isDM, self.slackClient)
            self.kios[channel] = newKio
        # now send the message on
        self.kios[channel].receiveMessage(message)

    def getUserDetails(self, userID):
        userPayload = self.slackClient.api_call("users.info", user=userID)
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
    km = KioManager()
