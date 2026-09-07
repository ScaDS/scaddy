import torch
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import json
import numpy as np
import os


class CLIPService:
    def __init__(self, model_name="openai/clip-vit-base-patch32", embeddings_file="./data/embeddings/embeddings.json", model_dir="./runtime/models/clip"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.embeddings_file = embeddings_file  # Store the embeddings file path

        self.model = CLIPModel.from_pretrained(model_name, cache_dir=model_dir).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name, cache_dir=model_dir)
        self.data = self.load_embeddings(embeddings_file)

    def _get_image_embedding(self, image_path: str) -> list:
        """
        Erzeugt das CLIP-Embedding für ein Bild.

        Kompatibel mit transformers 4.x (get_image_features() → Tensor)
        und transformers 5.x (get_image_features() → ModelOutput mit
        'last_hidden_state' und 'pooler_output').

        Raises:
            ValueError: Wenn das Output-Format nicht erkannt wird.
        """
        image = Image.open(image_path).convert("RGB")
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)

        with torch.no_grad():
            output = self.model.get_image_features(**inputs)

        # transformers 4.x: direkter Tensor
        if torch.is_tensor(output):
            return output.squeeze().tolist()

        # transformers 5.x: BaseModelOutputWithPooling
        if hasattr(output, "keys"):
            keys = list(output.keys())

            # 'image_embeds' ist der projizierte Feature-Vektor
            if "image_embeds" in keys and output.image_embeds is not None:
                return output.image_embeds.squeeze().tolist()

            # Fallback: pooler_output → visual_projection
            if "pooler_output" in keys and output.pooler_output is not None:
                pooled = output.pooler_output
                if hasattr(self.model, "visual_projection"):
                    with torch.no_grad():
                        projected = self.model.visual_projection(pooled)
                    return projected.squeeze().tolist()
                return pooled.squeeze().tolist()

        raise ValueError(
            f"Unbekanntes Output-Format von get_image_features(): "
            f"{type(output).__name__} mit Keys "
            f"{list(output.keys()) if hasattr(output, 'keys') else 'keine'}"
        )

    def find_similar_image(self, new_image_path):
        """Finds the most similar image based on stored CLIP embeddings."""

        # Create embeddings for the new image
        if not os.path.exists(new_image_path):
            print("Error: The entered image does not exist.")
            return None, -1

        try:
            new_image_embedding = self._get_image_embedding(new_image_path)
        except Exception as e:
            print(f"Error creating embedding for '{new_image_path}': {type(e).__name__}: {e}")
            return None, -1

        if not self.data:
            print("Warning: No stored embeddings found. Cannot match image.")
            return None, -1

        # Find the image with the highest cosine similarity
        max_similarity = -1
        most_similar = None

        for item in self.data:
            similarity = self.cosine_similarity(new_image_embedding, item["embedding"])
            if similarity > max_similarity:
                max_similarity = similarity
                most_similar = item

        if most_similar is None:
            print("Warning: No stored embeddings found. Cannot match image.")
            return None, -1

        print("Maximum Similarity", max_similarity)
        print("Most similar item:", most_similar.get("title", "unknown"))

        return most_similar, max_similarity

    def load_embeddings(self, file_path):
        """Loads the stored embeddings from a JSON file."""
        if not os.path.exists(file_path):
            print(f"Warning: The embeddings file '{file_path}' was not found. A new one will be created if data is added.")
            return []
        with open(file_path, "r") as f:
            data = json.load(f)
        return data

    def save_embeddings(self):
        """Saves the current embeddings to the JSON file."""
        with open(self.embeddings_file, "w") as f:
            json.dump(self.data, f, indent=4)
        print(f"Embeddings successfully saved to '{self.embeddings_file}'.")

    def cosine_similarity(self, embedding1, embedding2):
        """Calculates the cosine similarity between two embeddings."""
        embedding1 = np.array(embedding1)
        embedding2 = np.array(embedding2)
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        return dot_product / (norm1 * norm2)

    def add_to_embeddings(self, image_path, image_title, image_description, url=None, file_path_doc=None):
        """Adds new image to the CLIP-Embeddings."""

        if not os.path.exists(image_path):
            print("Error while creating embeddings for new image. Image does not exist.")
            return False

        try:
            # Erzeuge Embedding (versions-kompatibel, siehe _get_image_embedding)
            image_embedding_list = self._get_image_embedding(image_path)

            # Create the new entry
            new_entry = {
                "image_path": image_path,
                "title": image_title,
                "url": url,
                "file_path": file_path_doc,
                "description": image_description,
                "embedding": image_embedding_list,
            }

            # Add the new entry to the existing data
            self.data.append(new_entry)

            # Save the updated embeddings
            self.save_embeddings()
            print(f"New embedding for '{os.path.basename(image_path)}' added.")
            return True

        except Exception as e:
            print(f"Error adding embedding for '{image_path}': {type(e).__name__}: {e}")
            return False
