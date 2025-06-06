import insightface
import numpy as np
from PIL import Image

# This module provides functionality to extract face embeddings using the InsightFace library.
face_model = insightface.app.FaceAnalysis(name='buffalo_s')
face_model.prepare(ctx_id=0)  # 0 = GPU, -1 = CPU

def extract_face_embedding(image_input):
    try:
        if isinstance(image_input, Image.Image):
            image = image_input.convert("RGB")
        else:
            image = Image.open(image_input).convert("RGB")
        img_array = np.array(image)
        faces = face_model.get(img_array)
        if faces:
            return faces[0].embedding.tolist()
    except Exception as e:
        print(f"❌ Error processing face: {e}")
    return []
