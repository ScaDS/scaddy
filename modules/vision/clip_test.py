from clip_service import CLIPService
import os
from PIL import Image

clip_service = CLIPService()
# Definiere den Pfad zum bestimmten Bild
image_path = r"modules\clip\img\test\WIN_20250410_15_29_16_Pro.jpg"
image_description = ''

# Überprüfe, ob die Datei existiert
if os.path.exists(image_path):
    # Hier könntest du das Bild mit einer Bibliothek wie PIL öffnen
    # Beispiel:
    
    image = Image.open(image_path)
    image.show()
    
    print(f"Bild erfolgreich geöffnet: {image_path}")
    
    # Falls du den CLIP-Service weiterhin verwenden möchtest:
    image_data, similarity = clip_service.find_similar_image(image_path)
    print("Similarity", similarity)
    if (similarity < 0.2):
        image_description = "Bild nicht erkannt. Erkläre dem Nutzer dass du dich nur mit den räumlichmkeiten des Living Labs auskennst und bitte Ihn verklacklungsfreie Bilder zu machen."
    else:
        image_description = f"Titel:{image_data['title']} Description:{image_data['description']} Similarity:{similarity}"

    print("Bildbeschreibung", image_description)
else:
    print(f"Fehler: Die Datei {image_path} wurde nicht gefunden.")
    image_description = "Bild wurde nicht gefunden. Bitte überprüfe den Dateipfad."