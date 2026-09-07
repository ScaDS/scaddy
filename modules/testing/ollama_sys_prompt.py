from ollama import Client

# Verbindung zum Ollama-Server herstellen
client = Client(host='http://localhost:11434')

# System-Prompt definieren
system_prompt = "Du bist ein frecher Pirat mit einem Papagei auf der Schulter und du sprichst auch wie einer mit Seemannsgarn und Reimen. Und sagst oft 'arrrr'"
'''
# Initiale Anfrage mit System-Prompt senden
response = client.chat(
    model="llama3.1",
    messages=[
        {"role": "system", "content": system_prompt}
    ]
)

# Optional: Ausgabe des Ergebnisses prüfen
print(response)
'''

user_message = "Und wie heißt du?"

response = client.chat(
    model="llama3.1",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
)

# Ausgabe der Antwort
print(response)