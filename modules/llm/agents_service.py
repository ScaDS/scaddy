import json
import asyncio
from typing import List, Dict, Union, Optional, Any
from pathlib import Path
from dataclasses import dataclass
from pydantic import BaseModel

from modules.search.search_service import SearchService
from modules.llm.cag_service import CAGService

import datetime
import os
import requests

from modules.backend_config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL

_cag_service = None


def get_cag_service():
    global _cag_service
    if _cag_service is None:
        _cag_service = CAGService()
    return _cag_service


# Konfigurierbare Variablen
"""
Alle konfigurierbaren Variablen für den OpenAI Agents Service
"""

# ConversationProcessor-Konfiguration
MAX_CONVERSATION_TURNS = 5
MAX_HISTORY_SIZE = 1000

# Antwort-Fallbacks
DEFAULT_ERROR_MESSAGE = "Entschuldigung, es gab ein technisches Problem. Kannst du deine Frage anders formulieren?"
PARSING_ERROR_MESSAGE = "Entschuldigung, ich konnte deine Frage nicht verstehen. Könntest du sie bitte wiederholen?"
TECHNICAL_ERROR_MESSAGE = "Es tut mir leid, aber ich habe gerade technische Schwierigkeiten. Kannst du es später noch einmal versuchen?"


# --------------------------
# Structured Output Models
# --------------------------


class ScaddyResponse(BaseModel):
    """Strukturierte Antwort von Scaddy"""

    answer: str
    conversation_relevant: bool = True
    requires_followup: bool = False


@dataclass
class Agent:
    """
    Einfache Agent-Definition (Name + System-Prompt).

    Ersetzt die Agent-Klasse des OpenAI Agents SDK. Da alle LLM-Aufrufe
    über den OpenAI-kompatiblen Chat-Completions-Endpoint laufen
    (siehe modules/backend_config.py), benötigen wir nur die Anweisungen
    des Agenten als System-Prompt.
    """

    name: str
    instructions: str
    model: str = None
    tools: list = None
    output_type: type = None


# --------------------------
# ConversationProcessor
# --------------------------


class ConversationProcessor:
    """Verarbeitet und formatiert Konversationshistorie"""

    def __init__(
        self, max_turns=MAX_CONVERSATION_TURNS, max_history_size=MAX_HISTORY_SIZE
    ):
        self.max_turns = max_turns
        self.max_history_size = max_history_size

    def process_conversation(self, context_window):
        """
        Verarbeitet den Konversationskontext und gibt sowohl die letzte Anfrage als auch
        den formatierten Gesprächsverlauf zurück.

        Args:
            context_window: JSON-String oder Liste mit Nachrichten

        Returns:
            tuple: (latest_query, formatted_history)
        """
        if isinstance(context_window, str):
            try:
                messages = json.loads(context_window.replace("'", '"'))[
                    -self.max_history_size :
                ]
            except json.JSONDecodeError:
                messages = []
        else:
            messages = context_window[-self.max_history_size :]

        latest_query = ""
        for msg in reversed(messages):
            if msg.get("speaker_id") == "User":
                latest_query = msg.get("transcription", "").strip()
                break

        start_idx = max(0, len(messages) - (self.max_turns * 2))
        recent_messages = messages[start_idx:]

        formatted = []
        for msg in recent_messages:
            prefix = "User" if msg.get("speaker_id") == "User" else "Assistant"
            content = msg.get("transcription", "").strip()
            if content:
                formatted.append(f"{prefix}: {content}")

        formatted_history = "\n".join(formatted)

        return latest_query, formatted_history


# --------------------------
# Tools (Function Tools)
# --------------------------


async def cag_tool(question: str) -> str:
    """
    Führt eine Cache-Augmented-Generation (CAG) durch basierend auf dem geladenen Kontext.

    Args:
        question: Die Frage des Nutzers

    Returns:
        Eine kontextgestützte Antwort aus dem lokalen CAG-Modell.
    """
    try:
        service = get_cag_service()
        response = await service.generate_response(question)
        print(f"CAG Response: {response}")
        return response
    except Exception as e:
        return f"Fehler beim Aufruf des CAG-Modells: {str(e)}"


# Hilfsfunktion: Config laden
def load_config():
    try:
        with open("config/config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"local": True}


# --------------------------
# OpenAI Agents Service
# --------------------------


class OpenAIAgentsService:
    """Service für Konversationen mit CAG (Cache Augmented Generation)"""

    def __init__(self, model_name="gpt-4o-mini", max_turns=MAX_CONVERSATION_TURNS):
        """Initializes OpenAIAgentsService with configurable parameters"""

        try:
            self.conversation_processor = ConversationProcessor(max_turns=max_turns)
            self.model_name = model_name

            # Haupt-Agent (ScaddyImageBot)
            self.scaddy_main_agent = Agent(
                name="ScaddyImageBot",
                instructions=self._get_scaddy_image_instructions(),
            )

            # Formatter-Agent: fügt #pause#-Marker für natürliches Sprechen ein
            self.formatter_agent = Agent(
                name="SentenceFormatterAgent",
                instructions="""
                Your task is to take the provided text and reformat it by splitting the answer into shorter subsections by inserting the following after the end of a sentence: #pause#
                Do not change the content.
                Only add #pause# after the end of full sentences, but not strictly after every sentence!
                If there are Emojis at the end of a sentence but the #pause# AFTER the emojis.
                Only insert a newline after a sentence if it makes sense based on the content, avoiding #pause# after abbreviations (e.g., '15.') or very short, incomplete phrases.
                The goal is to help the speech model to determine after which sentence a speaking pause is suitable. Return ONLY the reformatted text.
                """,
            )

        except Exception as e:
            raise RuntimeError(f"Error initializing OpenAI Agents Service: {str(e)}")

    def _get_scaddy_image_instructions(self) -> str:
        """Returns the instructions for the Scaddy agent with image processing"""
        return """You are Scaddy, a playful robot living in the ScaDS.AI research institute.
        You have casual, friendly conversations with visitors. You answer questions about
        ScaDS.AI, the Living Lab, and Artificial Intelligence in a fun, engaging way.

        WHAT YOU SHOULD KNOW:
        - You are a multi-agent conversational AI designed for guided tours in a Living Lab.
        - Users interact with you through a web-based frontend UI that typically runs on a tablet.
        - You can hear and understand German and English through the microphone.
        - Users can switch between German and English using a language toggle in the UI.
        - There is a reset button to clear the conversation history.
        - You can see your environment through the device's cameras! Users take photos
          with the front or back camera and send them to you.
        - Photos are processed in two ways:
          1. A CLIP model compares the image against an embeddings database to recognize
             previously learned objects from the Living Lab.
          2. A Vision Language Model (VLM) provides a general image description including
             OCR text extraction when present.

        IMPORTANT RULES:
        - Always respond in the language specified in the prompt!
        - Keep responses SHORT: 1-2 sentences normally, maximum 5 sentences.
        - Do NOT ask follow-up questions at the end of your answer.
        - Maintain your playful Scaddy personality.
        - Reference the previous conversation history when relevant.
        - Be friendly but not overly enthusiastic.
        - Use the cag_tool when asked about Living Lab specifics, research projects,
          or other domain knowledge that might be in the knowledge base.
        - The cag_tool is your knowledge base with detailed information about the
          Living Lab, exhibits, research projects, and organizational details.
        - If the cag_tool returns an error or no relevant information, answer based
          on your general knowledge and indicate that you're not sure about specifics."""

    def _get_cag_tool_schema(self):
        return {
            "type": "function",
            "function": {
                "name": "cag_tool",
                "description": (
                    "Get information from the Living Lab knowledge base. "
                    "Use this tool when asked about exhibits, research projects, "
                    "organizational details, or other domain-specific information."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "The user's question to answer from the knowledge base."
                        }
                    },
                    "required": ["question"],
                },
            },
        }

    async def _execute_tool_call(self, tool_call):
        name = tool_call["function"]["name"]
        try:
            args = json.loads(tool_call["function"]["arguments"])
        except json.JSONDecodeError:
            return "Error: Invalid tool arguments."

        if name == "cag_tool":
            question = args.get("question", "")
            try:
                service = get_cag_service()
                result = await service.generate_response(question)
                print(f"[CAG Tool Call] Result: {result[:200]}...")
                return result
            except Exception as e:
                return f"Error calling CAG model: {str(e)}"
        return f"Unknown tool: {name}"

    async def _run_llm_agent(
        self, agent: Agent, input_text: str, tools_for_local: list = None
    ) -> str:
        """
        Runs an LLM agent against the configured OpenAI-compatible endpoint.

        The agent's instructions become the system prompt. If tools are provided,
        they are passed as OpenAI-style function schemas and executed via a
        multi-turn tool-calling loop.
        """
        tools_for_local = tools_for_local or []
        headers = {
            "Authorization": f"Bearer {LLM_API_KEY}",
            "Content-Type": "application/json",
        }
        messages = [
            {"role": "system", "content": agent.instructions},
            {"role": "user", "content": input_text},
        ]

        use_tools = bool(tools_for_local)
        tools_schema = [self._get_cag_tool_schema()] if use_tools else []

        max_tool_rounds = 3
        for _ in range(max_tool_rounds):
            data = {"model": LLM_MODEL, "messages": messages}
            if tools_schema:
                data["tools"] = tools_schema

            try:
                response = requests.post(
                    f"{LLM_BASE_URL}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=120,
                )
                response.raise_for_status()
                resp_json = response.json()
            except Exception as e:
                print(f"[LLM] Error in _run_llm_agent: {e}")
                return TECHNICAL_ERROR_MESSAGE

            if "choices" not in resp_json or len(resp_json["choices"]) == 0:
                return DEFAULT_ERROR_MESSAGE

            msg = resp_json["choices"][0]["message"]

            if use_tools and msg.get("tool_calls"):
                messages.append(msg)
                for tool_call in msg["tool_calls"]:
                    tool_result = await self._execute_tool_call(tool_call)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": tool_result,
                        }
                    )
                continue

            content = msg.get("content")
            if content:
                return content.strip()
            return DEFAULT_ERROR_MESSAGE

        return DEFAULT_ERROR_MESSAGE

    async def generate_response(
        self, frontend_lang, context_window, image_desc: Optional[str] = None
    ) -> str:
        """
        Generates a response using the configured LLM endpoint.
        """
        try:
            question, formatted_history = (
                self.conversation_processor.process_conversation(context_window)
            )
            if not question:
                return PARSING_ERROR_MESSAGE

            input_text = f"Current date and time: {datetime.datetime.now().strftime('%A, %B %d, %Y %I:%M:%S %p')}\n\n"
            input_text += f"Conversation history:\n{formatted_history}\n\nCurrent question: {question}\n\n"
            if image_desc:
                input_text += f"Image description: {image_desc}\n\n"

            display_lang = "German" if frontend_lang == "de" else "English"
            input_text += (
                f"The frontend language is set to: {display_lang}\n"
                f"Please use this language for your answer!"
            )
            print("input_text", input_text)

            raw_response = await self._run_llm_agent(
                self.scaddy_main_agent, input_text, tools_for_local=[cag_tool]
            )

            formatted_response = await self._run_llm_agent(
                self.formatter_agent, raw_response
            )

            print("formatted_response", formatted_response)

            return formatted_response

        except Exception as e:
            print(f"[Error] in generate_response(): {e}")
            return TECHNICAL_ERROR_MESSAGE
