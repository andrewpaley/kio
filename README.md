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

There are a host of comments scattered throughout the code if further information is required.
