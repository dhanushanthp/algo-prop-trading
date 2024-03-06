import requests
from clients.rest import Rest

class DXTrade:
    def __init__(self) -> None:
        self.rest_service  = Rest()
        self.access_token = None

    def login(self):
        payload = {
                    "username": "1210008442",
                    "domain": "default",
                    "password": "r9*2!@TR"
                }
        
        status_code, response = self.rest_service.post_request(url="login", payload=payload)
        if status_code == 200:
            self.access_token = response["sessionToken"]


if __name__ == "__main__":
    obj = DXTrade()
    obj.login()
    print(obj.access_token)


"""
PYTHONPATH="/Users/dhanu/Library/CloudStorage/OneDrive-Personal/Financial Freedom/Phoenix:$PYTHONPATH"
export PYTHONPATH

"""