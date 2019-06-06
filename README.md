# Kio - A Slackbot Kiosk

This is the slack bot interface to the Kiosk. The service can be run independently of Companion (but, of course, won't respond with relevant answers absent a Companion running in the backdrop to provide such responses.)

You can add this to any Slack App via a token provided by Slack. You can get that token for your Slack App by following the instructions under "Getting Started" [here](https://api.slack.com/bot-users).

## Environment setup
Assuming you got the token from Slack as per the above, add the token to your environment variables. In `.bashrc` or your equivalent, add the API token:
```
export SLACK_BOT_TOKEN = ...
```
You can also [bake this environment variable into your conda environment](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#saving-environment-variables) so that it doesn't pollute your base environment.

Then, install the dependencies:
```
conda create -n kio
conda install -c conda-forge slackclient
pip install pykqml
```

## Running Kio
Once you're all set up, just run
```
python main.py
```

While the service runs, it'll regularly poll Slack for new messages, looking for either DMs to the Kio user or references to @kio in the Slack App -- upon receipt of those sorts of messages, it'll feed the input down to Companion, and then return the result.

There are a host of comments scattered throughout the code if further information is required, though the key files to note are:

#### main.py (the KioManager class)
Adapted from docstring: The KioManager Class is the chat stream manager -- it gets instantiated on program start. It polls the slack api at a regular interval (set by self.readDelay) for new messages, and susses out if they're @Kio or to Kio in a DM. If so, it manages the message passing to the appropriate (new or existing, if ongoing conversation) Kio instance (there being one Kio instance for each channel or DM thread).

#### kio.py (the Kio class)
The KioManager will instantiate one of these Kio classes for each discrete conversation (DM or channel). It manages context, message history, long-running feedback (so the user understands work is still being done), message i/o (to/from the Agent), as well as replying out to the Slack API once a reply has been handed back. In future iterations, this class could provide "quick reply" features and improved multi-conversation handling.

#### agent.py (the KioAgent class)
This inherits from Pythonian and defines the necessary scaffolding on top of Pythonian such that the message i/o with Kio works.

#### pythonian.py (the Pythonian class)
Largely untouched from the code we received, however the `receive_achieve` method was updated to include `tell-user`
