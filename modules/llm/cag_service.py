import requests
import os

from modules.backend_config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL


class CAGService:
    """
    Cache-Augmented Generation (CAG).

    Vereinfachter Ansatz statt klassischem RAG: Die gesamte Wissensbasis
    wird als Kontext in das Prompt eingebettet (bzw. optional als Datei
    hochgeladen, falls der Endpoint /v1/files unterstützt).

    Der Endpoint, das Modell und der API-Key werden über .env konfiguriert
    (siehe modules/backend_config.py).
    """

    def __init__(
        self,
        model_name=None,
        knowledge_file="./data/knowledge_library/knowledge.txt",
        api_url=None,
        api_token=None,
    ):
        self.model_name = model_name or LLM_MODEL
        self.api_url = api_url or f"{LLM_BASE_URL}/chat/completions"
        self.api_token = api_token or LLM_API_KEY
        self.knowledge_file = knowledge_file
        self.knowledge_content = None
        self.file_id = None

    def _load_knowledge_content(self):
        if self.knowledge_content is None:
            if os.path.exists(self.knowledge_file):
                with open(self.knowledge_file, "r", encoding="utf-8") as f:
                    self.knowledge_content = f.read()
            else:
                raise FileNotFoundError(f"Wissensbasis nicht gefunden: {self.knowledge_file}")
        return self.knowledge_content

    def _upload_knowledge_file(self, path: str):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Wissensbasis nicht gefunden: {path}")

        try:
            files_url = f"{LLM_BASE_URL}/files"
            headers = {"Authorization": f"Bearer {self.api_token}"}
            with open(path, "rb") as f:
                files = {"file": (os.path.basename(path), f, "text/plain")}
                resp = requests.post(files_url, headers=headers, files=files, timeout=60)
                resp.raise_for_status()
                file_id = resp.json().get("id")
                if file_id:
                    print(f"[CAGService] Knowledge file uploaded with file_id: {file_id}")
                    return file_id
        except Exception as e:
            print(f"[CAGService] File upload failed, using text context: {e}")

        return None

    async def generate_response(self, user_question: str) -> str:
        if self.file_id is None:
            try:
                self.file_id = self._upload_knowledge_file(self.knowledge_file)
            except Exception as e:
                print(f"[CAGService] Could not upload file: {e}")

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        if self.file_id:
            system_prompt = (
                "Du bist Scaddys Wissensdatenbank. "
                "Nutze die angehängte Wissensbasis (Datei) als Kontext, um die folgende Frage so präzise und faktenbasiert wie möglich zu beantworten. "
                "Ignoriere keine Fakten aus der Datei. "
                "Gib nur Wissen wieder, das auch dort steht, außer die Frage bezieht sich explizit auf Allgemeinwissen."
            )
            data = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_question},
                ],
                "files": [
                    {"type": "file", "id": self.file_id}
                ],
            }
        else:
            knowledge_content = self._load_knowledge_content()
            system_prompt = f"""Du bist Scaddys Wissensdatenbank.
Nutze folgenden Wissenskontext als Grundlage für deine Antwort:

=== WISSENSDATENBANK ===
{knowledge_content}
=== ENDE WISSENSDATENBANK ===

Beantworte die Frage präzise und faktenbasiert basierend auf diesem Wissen.
Ignoriere keine Fakten aus der Wissensdatenbank.
Gib nur Wissen wieder, das dort steht, außer die Frage bezieht sich explizit auf Allgemeinwissen."""
            data = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_question},
                ],
            }

        try:
            response = requests.post(self.api_url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            resp_json = response.json()
            if "choices" in resp_json and len(resp_json["choices"]) > 0:
                answer = resp_json["choices"][0]["message"]["content"].strip()
                print(f"[CAGService] Antwort: {answer[:200]}...")
                return answer
            else:
                return "Fehler: Keine Antwort erhalten."
        except Exception as e:
            print("[CAGService] Fehler bei Inferenz:", e)
            return "Fehler bei der kontextbasierten Beantwortung."
