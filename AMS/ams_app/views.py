from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from ams_app.EmailBackEnd import EmailBackEnd
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
import os

# import json
# import os
# import threading
# import time
# import re
# import cv2
# import numpy as np
# import face_recognition
# from datetime import datetime, date
# from django.http import JsonResponse
# from django.utils import timezone
# from django.conf import settings
# from django.utils.timezone import now
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status

# from .models import SubjectSchedule, Students, Enrollment, Attendance, AttendanceReport

# Create your views here.
def dashboard(request):
    return render(request,"dashboard.html")

def LoginPage(request):
    return render(request,"Login.html")

def LoggedIn(request):
    if request.method!="POST":
        return HttpResponse("<h2>Method Not Allowed</h2>")
    else:
        user =EmailBackEnd.authenticate(request,username=request.POST.get('email'),password=request.POST.get('password'))
        if user!=None:
            login(request,user)
            if user.user_type=="1":
                return HttpResponseRedirect('/admin_home')
            elif user.user_type=="2":
                return HttpResponseRedirect(reverse("staff_home"))
            else:
                return HttpResponseRedirect(reverse("student_home"))
        else:
            messages.error(request,'Invalid Login Details')
            return HttpResponseRedirect('/')
    
def GetUserDetails(request):
    if request.user!=None:
        return HttpResponse("User : "+request.user.email+" usertype : "+str(request.user.user_type))
    else:
        return HttpResponse("Please Login First")

def Logout_user(request):
    logout(request)
    return HttpResponseRedirect("/")

# def face_kiosk(request):
#     return render(request,"face_kiosk.html")

# # Use KIOSK_API_KEY from Django settings
# KIOSK_API_KEY = getattr(settings, "KIOSK_API_KEY", "kiosk_9M6xP4lRMANfpWs9Xd1VJYKPurt70SbHdRcXuGXjBMg")
# # Common function for API Key Auth
# def is_authenticated(request):
#     client_key = request.headers.get("X-API-KEY")
#     return client_key == KIOSK_API_KEY

# class AutoMarkAttendanceView(APIView):
#     def post(self, request):
#         if not is_authenticated(request):
#             return Response({"error": "Unauthorized"}, status=401)

#         print("\n🔍 DEBUG: Request received!")

#         subject_id = request.POST.get("subject_id")
#         image = request.FILES.get("image")

#         if not subject_id or subject_id == "undefined":
#             return Response({"error": "Invalid subject ID"}, status=400)

#         if not image:
#             return Response({"error": "Missing image"}, status=400)

#         try:
#             subject_id = int(subject_id)
#             subject_schedule = SubjectSchedule.objects.get(id=subject_id)
#             actual_subject = subject_schedule.subject
#             enrollment = Enrollment.objects.filter(subject=actual_subject).first()

#             if enrollment:
#                 session_year = enrollment.student.session_year_id
#             else:
#                 return Response({"error": "No session year found"}, status=400)

#             image_data = np.frombuffer(image.read(), np.uint8)
#             img = cv2.imdecode(image_data, cv2.IMREAD_COLOR)

#             if img is None:
#                 return Response({"error": "Invalid image format"}, status=400)

#             img = cv2.resize(img, (640, 480))
#             rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
#             face_locations = face_recognition.face_locations(rgb_img, model='hog')
#             face_encodings = face_recognition.face_encodings(rgb_img, face_locations)

#             if not face_encodings:
#                 return Response({"error": "No face detected"}, status=400)

#             students = Students.objects.exclude(face_encoding=None)
#             known_encodings = []
#             for student in students:
#                 try:
#                     encoding_data = student.face_encoding
#                     encoding = json.loads(encoding_data) if isinstance(encoding_data, str) else encoding_data
#                     known_encodings.append(np.array(encoding))
#                 except Exception as e:
#                     print(f"⚠️ Skipping student {student.id} due to error: {e}")

#             for uploaded_encoding in face_encodings:
#                 matches = face_recognition.compare_faces(known_encodings, uploaded_encoding)
#                 if True in matches:
#                     for idx, match in enumerate(matches):
#                         if match:
#                             matched_student = students[idx]
#                             break

#                     matched_name = matched_student.admin.get_full_name()
#                     stored_rfid = matched_student.rfid

#                     print(f"🔑 DEBUG: Face recognized for {matched_name} with RFID {stored_rfid}")

#                     if not Enrollment.objects.filter(student=matched_student, subject=actual_subject).exists():
#                         return Response({"error": "Student is not enrolled in this subject"}, status=400)

#                     try:
#                         with open("rfid_tags.txt", "r") as file:
#                             tags = file.read().splitlines()
#                     except Exception:
#                         return Response({"error": "RFID tag file error"}, status=500)

#                     if stored_rfid not in tags:
#                         print(f"❌ RFID tag {stored_rfid} not detected")
#                         return Response({"error": "RFID tag not detected or already used"}, status=400)

#                     used_tag_path = "used_rfid_tags.txt"
#                     try:
#                         with open(used_tag_path, "a") as used_file:
#                             used_file.write(f"{stored_rfid}\n")
#                     except Exception as e:
#                         print(f"⚠️ Failed to mark RFID as used: {e}")

#                     now_time = timezone.now().time()
#                     start_time = subject_schedule.start_time
#                     time_diff = datetime.combine(date.today(), now_time) - datetime.combine(date.today(), start_time)
#                     minutes_late = time_diff.total_seconds() / 60

#                     if minutes_late <= 15:
#                         status_ = "Present"
#                     elif 15 < minutes_late <= 30:
#                         status_ = "Late"
#                     else:
#                         status_ = "Absent"

#                     attendance, _ = Attendance.objects.get_or_create(
#                         subject=actual_subject,
#                         schedule=subject_schedule,
#                         session_year=session_year,
#                         attendance_date=date.today()
#                     )

#                     report, created = AttendanceReport.objects.get_or_create(
#                         student=matched_student,
#                         attendance=attendance
#                     )

#                     if created:
#                         report.status = status_
#                         report.created_at = timezone.now()
#                         report.save()
#                         attendance.students.add(matched_student)
#                         attendance_time = timezone.now().strftime("%I:%M:%S %p")
#                     else:
#                         status_ = report.status
#                         attendance_time = report.created_at.strftime("%I:%M:%S %p") if report.created_at else timezone.now().strftime("%I:%M:%S %p")

#                     last_name = matched_student.admin.last_name
#                     first_initial = matched_student.admin.first_name[0] if matched_student.admin.first_name else ""
#                     formatted_name = f"{last_name}, {first_initial}"

#                     print(f"✅ SUCCESS: {status_} marked for {formatted_name} ({stored_rfid}) at {attendance_time}")

#                     return Response({
#                         "message": f"{status_} recorded for {formatted_name}.",
#                         "rfid": stored_rfid,
#                         "status": status_,
#                         "formatted_name": formatted_name,
#                         "attendance_time": attendance_time
#                     })

#             return Response({"error": "No matching student found"}, status=404)

#         except Exception as e:
#             print(f"⚡ ERROR: Exception processing image -> {e}")
#             return Response({"error": "Error processing image"}, status=500)

# class GetOngoingSubjectView(APIView):
#     def get(self, request):
#         if not is_authenticated(request):
#             return Response({"error": "Unauthorized"}, status=401)

#         current_time = now().time()
#         today = now().strftime("%A")

#         subjects_today = SubjectSchedule.objects.filter(day_of_week=today).order_by("start_time")
#         ongoing_subject = subjects_today.filter(start_time__lte=current_time, end_time__gte=current_time).first()

#         if ongoing_subject:
#             return Response({
#                 "subject_id": ongoing_subject.id,
#                 "subject_name": ongoing_subject.subject.subject_name,
#                 "start_time": str(ongoing_subject.start_time),
#                 "end_time": str(ongoing_subject.end_time),
#                 "message": "Ongoing class is active"
#             })

#         last_class = subjects_today.last()
#         if last_class and current_time > last_class.end_time:
            
#             return Response({"message": "All scheduled classes for today have ended."}, status=200)

#         next_class = subjects_today.filter(start_time__gt=current_time).first()
#         if next_class:
#             return Response({
#                 "next_subject_id": next_class.id,
#                 "next_subject_name": next_class.subject.subject_name,
#                 "next_start_time": str(next_class.start_time),
#                 "next_end_time": str(next_class.end_time),
#                 "message": "Waiting for the next class to start"
#             }, status=200)

#         return Response({"error": "No ongoing class at the moment."}, status=404)