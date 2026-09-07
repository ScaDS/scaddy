import requests
import json

# API-Endpunkt von Perplexica
url = "http://localhost:3001/api/search"

# Anfrage-Daten
data = {
    "chatModel": {
        "provider": "ollama",
        "model": "llama3.1:latest"
    },
    "embeddingModel": {
        "provider": "ollama",
        "model": "nomic-embed-text:latest"
    },
    "focusMode": "webSearch",
    "query": "Was ist das ScaDS.AI?"
}

# Senden der Anfrage
headers = {"Content-Type": "application/json"}
response = requests.post(url, json=data, headers=headers)

# Antwort prüfen und ausgeben
if response.status_code == 200:
    result = response.json()
    # gesamter Output mit Quellen:
    # print(json.dumps(result, indent=4))

    # Nur die message anzeigen
    message = result.get("message", "Keine Antwort erhalten.")
    print(f"Antwort: {message}")
else:
    print(f"Fehler: {response.status_code}")
    print(response.text)
