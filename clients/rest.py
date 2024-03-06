import requests
import json
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Rest:
    def __init__(self) -> None:
        self.base_url = "https://dxtrade.ftmo.com/dxsca-web/"

    def post_request(self, url, payload, headers=None):
        request_url = self.base_url + url
        
        if not headers:
            headers = {}
        
        if payload:
            response = requests.post(request_url, json=payload, verify=False, headers=headers)
        else:
            response = requests.post(request_url, verify=False, headers=headers)

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
    
    def get_request(self, url, headers):
        """
        Base request to the Client Portal
        """
        request_url = self.base_url + url
        
        if not headers:
            headers = {'Content-Type': 'application/json'}

        response = requests.get(request_url, verify=False, headers=headers)
        return json.loads(response.content)

    def delete_request(self, url, headers):
        """
        Base request to the Client Portal
        """
        request_url = self.base_url + url
        
        if not headers:
            headers = {'Content-Type': 'application/json'}

        response = requests.delete(request_url, verify=False, headers=headers)
        return json.loads(response.content)