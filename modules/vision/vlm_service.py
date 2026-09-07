# modules/vision/vlm_service.py

# vlm_service to enrich vision capabilities:
# this is adding context to images taken in the vision mode
# the vlm adds image description as well as possibly OCR or else
# the aim is to not only rely on the visRAG knowledge but give scaddy also super-powers regarding conversation including images and image-contents

import requests
import os
import base64

from modules.backend_config import VLM_BASE_URL, VLM_API_KEY, VLM_MODEL


class VLMService:
    def __init__(
        self,
        model: str = None,
        api_url: str = None,
        api_token: str = None,
    ):
        self.model = model or VLM_MODEL
        self.api_url = api_url or f"{VLM_BASE_URL}/chat/completions"
        self.api_token = api_token or VLM_API_KEY

    def convert_image_to_base64(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    async def infer(
        self,
        image_path: str,
        prompt: str = "Was ist auf dem Bild zu sehen? Beschreibe die Bildinhalte und Elemente. Sind Texte, Dokumente oder ähnliches zu sehen, verwende deine OCR-Fähigkeiten, um die Informationen zu extrahieren.",
    ) -> str:
        try:
            img_base64 = self.convert_image_to_base64(image_path)
            headers = {
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json'
            }
            data = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + img_base64}}
                        ]
                    }
                ]
            }
            response = requests.post(self.api_url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            resp_json = response.json()
            if "choices" in resp_json and len(resp_json["choices"]) > 0:
                return resp_json["choices"][0]["message"]["content"].strip()
            else:
                return "❌ Fehler: Keine Antwort erhalten."
        except Exception as e:
            print("[VLMService] Fehler bei Inferenz:", e)
            return "Fehler bei der Bildanalyse"
