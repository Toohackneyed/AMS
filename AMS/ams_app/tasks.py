import face_recognition
import numpy as np
import json
import logging
from io import BytesIO
import cv2
from celery import shared_task
from .models import Students
from PIL import Image

logger = logging.getLogger(__name__)

@shared_task
def process_face_encoding(student_id, image_data):
    logger.info(f"🔄 Processing face encoding for Student ID: {student_id}")

    try:
        student = Students.objects.get(id=student_id)

        # Load image into PIL for processing
        image = Image.open(BytesIO(image_data)).convert("RGB")

        # Optional: crop to square (centered)
        width, height = image.size
        side = min(width, height)
        left = (width - side) // 2
        top = (height - side) // 2
        image = image.crop((left, top, left + side, top + side))

        # Resize for consistency (not too small)
        image = image.resize((400, 400))

        # Convert to NumPy array for face_recognition
        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        img_array = np.frombuffer(buffered.getvalue(), np.uint8)
        bgr_image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        rgb_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)

        # Detect face and encode
        face_locations = face_recognition.face_locations(rgb_image, model="cnn")
        face_encodings = face_recognition.face_encodings(rgb_image, face_locations)

        if face_encodings:
            encoded_face = face_encodings[0]
            student.face_encoding = json.dumps(
                [round(float(x), 15) for x in encoded_face],
                ensure_ascii=False
            )
            student.save()
            logger.info(f"✅ Face encoding saved for Student ID: {student_id}")
            return f"✅ Face encoding successful for Student ID {student_id}"
        else:
            logger.warning(f"⚠️ No face detected for Student ID: {student_id}")
            return f"⚠️ No face detected for Student ID {student_id}"

    except Students.DoesNotExist:
        logger.error(f"❌ Student with ID {student_id} not found!")
        return f"❌ Student with ID {student_id} not found!"

    except Exception as e:
        logger.error(f"🚨 Error in face encoding for Student ID {student_id}: {e}")
        return f"🚨 Error: {str(e)}"
