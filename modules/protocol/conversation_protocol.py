import os
import json
import logging
from typing import List, Dict, Any
import time

class ConversationProtocol:
    def __init__(self):
        self.protocol_dir = os.path.join(os.path.dirname(__file__), "..", "..", "runtime", "protocol")

        if not os.path.exists(self.protocol_dir):
            os.makedirs(self.protocol_dir)
    
    # PROBLEM 1: Keine Fehlerbehandlung bei JSON-Parsing
    # LÖSUNG: Sichere JSON-Operationen mit try/except
    def _safe_json_load(self, file_path: str) -> List[Dict]:
        """Sicher JSON laden mit Fehlerbehandlung"""
        try:
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            return []
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logging.error(f"JSON-Fehler in {file_path}: {str(e)}")
            # Erstelle Backup der korrupten Datei
            if os.path.exists(file_path):
                backup_path = f"{file_path}.corrupt_{int(time.time())}"
                os.rename(file_path, backup_path)
                logging.info(f"Korrupte Datei nach {backup_path} verschoben")
            return []
    
    def _safe_json_save(self, file_path: str, data: Any) -> bool:
        """Sicher JSON speichern mit Fehlerbehandlung"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            logging.error(f"Fehler beim Speichern von {file_path}: {str(e)}")
            return False

    def write_to_protocol(self, speaker_id: str, transcription: str):
        """Schreibt Nachricht ins Konversationsprotokoll"""
        protocol_file = os.path.join(self.protocol_dir, "conversation.json")
        data = {"speaker_id": speaker_id, "transcription": transcription}
        
        # KORREKTUR: Sichere JSON-Operation verwenden
        protocol_data = self._safe_json_load(protocol_file)
        protocol_data.append(data)
        
        if self._safe_json_save(protocol_file, protocol_data):
            print("Konversationsprotokoll aktualisiert.")
        else:
            print("FEHLER: Konversationsprotokoll konnte nicht aktualisiert werden!")

    # PROBLEM 2: Bug in write_actual_question - überschreibt Array statt hinzuzufügen
    # ORIGINAL CODE:
    # question_data = data  # ❌ FEHLER: Überschreibt das Array!
    
    # KORREKTUR:
    def write_actual_question(self, speaker_id: str, transcription: str):
        """Schreibt aktuelle Frage (KORRIGIERT)"""
        question_file = os.path.join(self.protocol_dir, "question.json")
        data = {"speaker_id": speaker_id, "transcription": transcription}
        
        # KORREKTUR 1: Sichere JSON-Operation
        question_data = self._safe_json_load(question_file)
        
        # KORREKTUR 2: Füge zur Liste hinzu statt zu überschreiben
        question_data.append(data)  # ✅ RICHTIG: Fügt zur Liste hinzu
        
        # Alternativ: Wenn nur die letzte Frage gespeichert werden soll:
        # question_data = [data]  # Nur die aktuelle Frage
        
        if self._safe_json_save(question_file, question_data):
            print("Frage-JSON aktualisiert.")
        else:
            print("FEHLER: Frage-JSON konnte nicht aktualisiert werden!")

    def get_latest_question(self) -> Dict[str, Any]:
        """Liefert die aktuelle Frage"""
        question_file = os.path.join(self.protocol_dir, "question.json")
        
        # KORREKTUR: Sichere JSON-Operation
        question_data = self._safe_json_load(question_file)
        
        # Gib die letzte Frage zurück, falls vorhanden
        if question_data and isinstance(question_data, list):
            return question_data[-1]
        elif isinstance(question_data, dict):
            return question_data
        else:
            return {}

    def get_latest_context_window(self, max_length: int = 2048) -> List[Dict[str, Any]]:
        """Liefert das letzte Kontextfenster aus dem Konversationsprotokoll"""
        protocol_file = os.path.join(self.protocol_dir, "conversation.json")
        
        # KORREKTUR: Sichere JSON-Operation
        protocol_data = self._safe_json_load(protocol_file)
        
        if not protocol_data:
            return []

        # Bereite das Kontextfenster vor
        context_window = []
        token_count = 0
        
        # Gehe vom letzten Eintrag rückwärts, bis max_length erreicht ist
        for entry in reversed(protocol_data):
            text = f"{entry['speaker_id']}: {entry['transcription']}"
            tokens = len(text.split())
            if token_count + tokens <= max_length:
                context_window.append(entry)
                token_count += tokens
            else:
                break
        
        # Kontextfenster umkehren, um die chronologische Reihenfolge zu wahren
        context_window.reverse()
        return context_window
    
    # NEUE HILFSMETHODEN:
    def get_protocol(self) -> List[Dict[str, Any]]:
        """Gibt das komplette Protokoll zurück (für OpenAI Agents Service)"""
        protocol_file = os.path.join(self.protocol_dir, "conversation.json")
        return self._safe_json_load(protocol_file)
    
    def clear_protocol(self):
        """Löscht das Konversationsprotokoll"""
        protocol_file = os.path.join(self.protocol_dir, "conversation.json")
        question_file = os.path.join(self.protocol_dir, "question.json")
        
        for file_path in [protocol_file, question_file]:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logging.info(f"{file_path} gelöscht")
                except Exception as e:
                    logging.error(f"Fehler beim Löschen von {file_path}: {str(e)}")


# print(os.path.join(os.path.dirname(__file__), "..", "..", "runtime", "protocol"))