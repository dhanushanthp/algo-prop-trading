import os
from slack import WebClient
from slack.errors import SlackApiError
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

class Slack:
    def __init__(self) -> None:
        try:
            self.client = WebClient(
                token="")
        except Exception as e:
            print(e)
        self.SLACK_CHANNEL = 'general'

    def send_msg(self, msg):
        if True:
            try:
                self.client.chat_postMessage(channel='#general', text=msg)
            except Exception as e:
                print(e)

if __name__ == "__main__":
    ref = Slack()
    ref.send_msg('testing')
