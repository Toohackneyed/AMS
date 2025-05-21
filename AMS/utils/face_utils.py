# utils/face_utils.py

import insightface
import numpy as np
from PIL import Image

# I-load ang model (global para hindi inuulit)
face_model = insightface.app.FaceAnalysis(name='buffalo_s')
face_model.prepare(ctx_id=0)  # 0 = GPU, -1 = CPU

def extract_face_embedding(image_file):
    try:
        image = Image.open(image_file).convert("RGB")
        img_array = np.array(image)
        faces = face_model.get(img_array)
        if faces:
            return faces[0].embedding.tolist()
    except Exception as e:
        print(f"❌ Error processing face: {e}")
    return []
