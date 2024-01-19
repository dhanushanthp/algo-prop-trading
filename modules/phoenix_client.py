import requests

def get_master_positions():
    try:
        url = "http://10.1.0.6:8080/get_positions"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            return data

    except Exception as e:
        print("Exception:", str(e))

if __name__ == "__main__":
    print(get_master_positions())
