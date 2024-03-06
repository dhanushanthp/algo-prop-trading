import requests
import json

class Rest:
    def __init__(self) -> None:
        self.base_url = "https://dxtrade.ftmo.com/dxsca-web/"

    def post_request(self, url, payload):
        request_url = self.base_url + url
        response = requests.post(request_url, json=payload, verify=False)

        if response.status_code == 404:
            return response.status_code, response.content

        if response.status_code == 503:
            return response.status_code, response.content

        try:
            order_content = json.loads(response.content)
        except json.JSONDecodeError as e:
            self.msg.send_msg(
                f"Json Error in POST Request, ```{e}\n {response}\n {response.status_code}```"
            )
            return response.status_code, response.content

        return response.status_code, order_content