

if __name__ == "__main__":
    import requests
    API_URL = "http://0.0.0.0:8000/api/v1"
    # response = requests.get(f'{API_URL}/authors/')
    response = requests.get(f'{API_URL}/statistics/')
    print(response.status_code)
    print(response.text)
