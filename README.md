# Kio - A Slackbot Kiosk

## Environment setup
In `.bashrc` or your equivalent, add the API token:
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
```
python main.py
```