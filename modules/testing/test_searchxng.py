import os
import requests
from bs4 import BeautifulSoup
from lxml_html_clean import Cleaner  # Zum Reinigen des HTML-Inhalts
import ollama

# SearchXNG API-Endpunkt
search_url = os.getenv("SEARCHXNG_URL", "http://localhost:4000/search")

def get_news_urls(query):
    """ Holt URLs von SearchXNG basierend auf der Query """
    params = {
        "q": query,
        "format": "json"
    }
    search_results = requests.get(search_url, params=params)
    search_results_json = search_results.json()
    urls = [result['url'] for result in search_results_json['results'][:1]]
    return urls

def get_cleaned_text(urls):
    """ Holt und säubert den Text der Artikel """
    texts = []
    for url in urls:
        print(f"Fetching {url}")
        response = requests.get(url)
        html = response.text
        text = html_to_text(html)
        texts.append(f"Source: {url}\n{text}\n\n")
    return texts

def html_to_text(html):
    """ Extrahiert und reinigt den lesbaren Text aus HTML """
    cleaner = Cleaner()
    soup = BeautifulSoup(html, "html.parser")
    cleaned_html = cleaner.clean_html(str(soup))  # HTML säubern
    readable_text = BeautifulSoup(cleaned_html, "html.parser").get_text()
    return readable_text

def answer_query(query, texts):
    """ Fragt das LLM-Modell an, um eine Antwort basierend auf den Artikeln zu generieren """
    result = ollama.generate({
        "model": "llama3.2:1b",
        "prompt": f"{query}. Summarize the information and provide an answer. Use only the information in the following articles to answer the question: {' '.join(texts)}",
        "stream": True,
        "options": {
            "num_ctx": 16000,
        }
    })
    
    for chunk in result:
        if chunk.get("done") != True:
            print(chunk.get("response"))

# Ausführung des Codes
query = "Was ist das ScaDS.AI?"
urls = get_news_urls(query)
alltexts = get_cleaned_text(urls)
answer_query(query, alltexts)
