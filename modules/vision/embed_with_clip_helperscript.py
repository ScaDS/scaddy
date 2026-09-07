import torch
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import json
import os
import matplotlib.pyplot as plt

def user_input(prompt):
    """Hilfsfunktion zur Eingabe mit Möglichkeit, leer zu lassen."""
    value = input(prompt).strip()
    return value if value else None

def show_image(image_path):
    """Zeigt das Bild an"""
    image = Image.open(image_path)
    plt.figure(figsize=(10, 10))
    plt.imshow(image)
    plt.axis('off')
    plt.title(os.path.basename(image_path))
    plt.show()

def create_clip_embeddings(output_file):
    """Erstellt CLIP-Embeddings für Bilder mit zusätzlichen Metadaten."""
    # Lade das CLIP-Modell
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    
    data = []
    print("\nWillkommen zum CLIP Embedding Generator!")
    print("Hier werden alle Bilder im 'data/embeddings/images' Ordner verarbeitet.")
    print("Für jedes Bild können Metadaten eingegeben werden. Felder können leer bleiben.")
    
    # Überprüfe, ob der img-Ordner existiert
    img_folder = './data/embeddings/images'
    if not os.path.exists(img_folder) or not os.path.isdir(img_folder):
        print(f"Fehler: Der Ordner '{img_folder}' existiert nicht. Bitte erstellen Sie diesen Ordner zuerst.")
        return
    
    # Liste alle Bilddateien im img-Ordner auf
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff']
    image_files = [
        os.path.join(img_folder, f) for f in os.listdir(img_folder)
        if os.path.isfile(os.path.join(img_folder, f)) and
        any(f.lower().endswith(ext) for ext in image_extensions)
    ]
    
    if not image_files:
        print(f"Keine Bilder im '{img_folder}' Ordner gefunden.")
        return
    
    print(f"{len(image_files)} Bilder gefunden.")
    
    for i, image_path in enumerate(image_files):
        print(f"\nBild {i+1} von {len(image_files)}: {os.path.basename(image_path)}")
        
        # Zeige das Bild an
        try:
            show_image(image_path)
        except Exception as e:
            print(f"Fehler beim Anzeigen des Bildes: {e}")
        
        # Frage, ob dieses Bild übersprungen werden soll
        action = user_input("Möchten Sie fortfahren (Enter), dieses Bild überspringen (s), oder den Prozess beenden (exit)? ")
        if action and action.lower() == 'exit':
            print("Prozess wird beendet...")
            break
        if action and action.lower() == 's':
            print(f"Bild {os.path.basename(image_path)} wird übersprungen.")
            continue
        
        title = user_input("Titel: ")
        url = user_input("URL: ")
        file_path = user_input("Pfad zu Dokument(en) (optional): ")
        description = user_input("Beschreibung/Annotation: ")
        
        # Lade das Bild
        image = Image.open(image_path)
        
        # Verarbeite das Bild und erstelle Embeddings
        inputs = processor(images=image, return_tensors="pt").to(device)
        with torch.no_grad():
            image_embeddings = model.get_image_features(**inputs)
        
        # Konvertiere das Embedding in eine Liste
        image_embedding_list = image_embeddings.squeeze().tolist()
        
        # Speichere die Daten
        data.append({
            'image_path': image_path,
            'title': title,
            'url': url,
            'file_path': file_path,
            'description': description,
            'embedding': image_embedding_list
        })
        
        print(f"Eintrag für {os.path.basename(image_path)} gespeichert!")
    
    if data:
        # Prüfe, ob die Ausgabedatei bereits existiert
        if os.path.exists(output_file):
            overwrite = user_input(f"Möchten Sie die Datei '{output_file}' überschreiben? (j/n): ").lower()
            if overwrite != "j" and overwrite != "ja":
                print("Speichern abgebrochen. Die Datei wurde nicht überschrieben.")
                return
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"\nAlle Daten wurden in {output_file} gespeichert!")
    else:
        print("Keine neuen Einträge. Datei wurde nicht erstellt/verändert.")

# Beispiel-Aufruf
if __name__ == "__main__":
    output_file = 'data/embeddings/embeddings.json'
    create_clip_embeddings(output_file)