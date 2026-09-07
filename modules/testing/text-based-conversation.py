import requests

def chat_with_llm(api_url):
    print("Starte Chat mit LLM. Gib 'exit' ein, um den Chat zu beenden.")

    while True:
        # Eingabe vom Benutzer
        user_input = input("Du: ")
        if user_input.lower() == 'exit':
            print("Beende den Chat.")
            break

        # Anfrage an den API-Endpunkt senden
        try:
            response = requests.post(
                url=f"{api_url}/text_based_conversation",
                json={"user_input": user_input}
            )

            if response.status_code == 200:
                # Antwort des LLMs anzeigen
                llm_response = response.json().get('response', 'Keine Antwort erhalten.')
                print(f"LLM: {llm_response}")
            else:
                print(f"Fehler bei der Anfrage: {response.status_code}")
                print(response.text)  # Zeige die genaue Fehlermeldung
        except requests.exceptions.RequestException as e:
            print(f"Fehler bei der Verbindung: {e}")

if __name__ == "__main__":
    api_url = "http://localhost:8111"  # Passe die URL an, falls der Server auf einem anderen Port/Host läuft
    chat_with_llm(api_url)