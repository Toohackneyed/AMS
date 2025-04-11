import face_recognition
import numpy as np
import json
import logging
from io import BytesIO
from celery import shared_task
from .models import Students

logger = logging.getLogger(__name__)

@shared_task
def process_face_encoding(student_id, image_data):
    logger.info(f"🔄 Processing face encoding for Student ID: {student_id}")
    
    try:
        student = Students.objects.get(id=student_id)
        image = face_recognition.load_image_file(BytesIO(image_data))
        face_encodings = face_recognition.face_encodings(image, model="cnn")

        if face_encodings:
            encoded_face = face_encodings[0]
            encoded_face_str = json.dumps(encoded_face.tolist(), ensure_ascii=False)
            student.face_encoding = encoded_face_str
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