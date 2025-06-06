import json
import logging
from io import BytesIO
from celery import shared_task
from PIL import Image
from .models import Students, Staffs
from utils.face_utils import extract_face_embedding

# Tasks for processing face encodings for students and staff members
logger = logging.getLogger(__name__)

@shared_task
def process_face_encoding(user_id, image_data, user_type="student"):
    logger.info(f"🔄 Processing face encoding for {user_type.title()} ID: {user_id}")
    try:
        if user_type == "student":
            user = Students.objects.get(id=user_id)
        elif user_type == "staff":
            user = Staffs.objects.get(id=user_id)
        else:
            raise ValueError(f"Unknown user_type: {user_type}")
        image = Image.open(BytesIO(image_data)).convert("RGB")
        width, height = image.size
        side = min(width, height)
        left = (width - side) // 2
        top = (height - side) // 2
        image = image.crop((left, top, left + side, top + side))
        image = image.resize((400, 400))
        encoding = extract_face_embedding(image)
        if encoding:
            user.face_encoding = json.dumps(encoding, ensure_ascii=False)
            user.save()
            logger.info(f"✅ Face encoding saved for {user_type.title()} ID: {user_id}")
            return f"✅ Face encoding successful for {user_type.title()} ID {user_id}"
        else:
            logger.warning(f"⚠️ No face detected for {user_type.title()} ID: {user_id}")
            return f"⚠️ No face detected for {user_type.title()} ID {user_id}"
    except (Students.DoesNotExist, Staffs.DoesNotExist):
        logger.error(f"❌ {user_type.title()} with ID {user_id} not found!")
        return f"❌ {user_type.title()} with ID {user_id} not found!"
    except Exception as e:
        logger.error(f"🚨 Error in face encoding for {user_type.title()} ID {user_id}: {e}")
        return f"🚨 Error: {str(e)}"