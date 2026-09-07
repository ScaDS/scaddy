from ollama import Client

# Configure your local Ollama instance here
client = Client(host='http://localhost:11434')


message=[{'role': 'system', 'content': 'You are a helpful conversational assistant that speaks friendly and fluently and answers preferably in GERMAN. If you are asked to answer in another language, you can answer in english too. Only respond to the last question in the protocol without repeating it but consider the conversation-protocol for general reference and for context of the whole discussion.'}, {'role': 'user', 'content': "Speaker 1:  Das ist ein Test.  Hallo, wie geht's?"}, {'role': 'user', 'content': 'Speaker 1:  Das ist der zweite Test. Wie geht es dir?'}, {'role': 'user', 'content': 'Speaker 1:  Hallo, wie geht es dir?'}, {'role': 'user', 'content': 'Speaker 1:  Ein weiterer Test, wie geht es dir?'}, {'role': 'user', 'content': 'Speaker 1:  Wie viele Menschen leben auf der Erde. Kannst du das bitte englisch beantworten, denn ich habe nicht-deutschprachige Gäste hier?'}]

stream = client.chat(
    model='llama3.1',
    # messages=[{'role': 'user', 'content': 'Why is the sky blue?'}],
    messages=message,
    stream=True,
)

for chunk in stream:
  print(chunk['message']['content'], end='', flush=True)

'''
import ollama
response = ollama.chat(model='llama3', messages=[
  {
    'role': 'user',
    'content': 'Why is the sky blue?',
  },
])
print(response['message']['content'])
'''