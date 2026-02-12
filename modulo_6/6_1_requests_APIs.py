import requests

# GET simples
response = requests.get("https://api.github.com/events")
data = response.json()

# POST com autenticação
url = ""
auth = ("user", "pass")
payload = {"key": "value"}
r =requests.post(url, data=payload, auth=auth)

# Traamento de erros
try:
    r.raise_for_status()
except requests.exceptions.HTTPError as err:
    print(f"Erro HTTP: {err}")
