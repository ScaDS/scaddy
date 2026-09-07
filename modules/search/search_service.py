import requests
import json

PERPLEXICA_ENDPOINT = "http://localhost:3001"

class SearchService:
    def search(self, query, history=[]):
        """Searches the web for a given query using self hosted perplexica instance"""
        
        url = f"{PERPLEXICA_ENDPOINT}/api/search"

        payload = {
            "chatModel": {
                "provider": "ollama",
                "model": "qwen2.5:latest"
                # "model": "llama3.2:3b"
            },
            "embeddingModel": {
                "provider": "ollama",
                "model": "bge-m3:latest"
                # "provider": "local",
                # "model": "xenova-bge-small-en-v1.5"
            },
            "optimizationMode": "speed",
            "focusMode": "webSearch",
            "query": query,
            "history": history
        }

        headers = {
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            response_json = response.json()

            # complete output with sources
            # output = json.dumps(response_json, indent=4)

            # return only message
            output = response_json.get("message", "Keine Antwort erhalten.")

            print(f"Perplexica Response: {output}")
            return output
        else:
            print(f"Preplexica Fehler: {response.status_code}")
            print(response.text)