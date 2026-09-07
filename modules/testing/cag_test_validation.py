import asyncio
import lmstudio as lms

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from modules.llm.cag_service import CAGService

# Toolfunktion für Toolaufruf
def ask_cag(context_window: str) -> str:
    """
    Verwende internes Wissen aus einer textbasierten Wissensdatenbank,
    um kontextuelle Fragen zu ScaDS.AI oder dem Living Lab zu beantworten.
    
    Parameter:
    - context_window: Die Benutzerfrage, die mit dem gespeicherten Wissen beantwortet werden soll.
    
    Returns:
    Eine textuelle Antwort basierend auf der Wissensbasis.
    """
    cag = CAGService()
    # Trick: asynchronen Code synchron ausführen
    return asyncio.run(cag.generate_response(context_window))


# Fehlerbehandlung (direkt inline genutzt)
def handle_tool_error(exc, request=None):
    print("[Fehler] Tool konnte nicht korrekt verwendet werden.")
    raise exc

# Hauptfunktion
async def main():
    model = lms.llm("qwen3-8b")  # Stelle sicher, dass dieses Modell in LM Studio läuft
    chat = lms.Chat()

    # Beispielprompt – erfordert Toolnutzung
    chat.add_user_message(
        "Nutze das interne ScaDS.AI-Wissen, um zu beantworten: Wie viele Menschen arbeiten am ScaDS.AI? /no_think"
    )

    final_response = ""

    def capture_message(msg):
        nonlocal final_response
        # print("[on_message]", msg) # for testing/debugging

        if isinstance(msg, lms.AssistantResponse):
            for part in msg.content:
                if hasattr(part, "text") and part.text:
                    text = part.text.strip()
                    if "</think>" in text:
                        final_response = text.split("</think>", 1)[1].strip()
                    elif "<think>" not in text:
                        final_response = text

    model.act(
        chat,
        tools=[ask_cag],
        on_message=capture_message
    )

    print("\n[Antwort vom Modell]:")
    print(final_response.strip() if final_response else "[Leere Antwort]")

# Start
if __name__ == "__main__":
    asyncio.run(main())
