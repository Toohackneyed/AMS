from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings
from django.utils.timezone import now

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser

import os
import json
import numpy as np
from datetime import datetime, date

from ams_app.EmailBackEnd import EmailBackEnd
from ams_app.models import Students, Subjects, Enrollment, Attendance, AttendanceReport, SubjectSchedule
from ams_app.serializers import StudentSerializer, SubjectSerializer, AttendanceInputSerializer
from utils.face_utils import extract_face_embedding
from utils.api_auth import require_api_key


# ======================== BASIC ROUTES ========================

def dashboard(request):
    return render(request, "dashboard.html")

def LoginPage(request):
    return render(request, "Login.html")

def LoggedIn(request):
    if request.method != "POST":
        return HttpResponse("<h2>Method Not Allowed</h2>")
    
    user = EmailBackEnd.authenticate(request, username=request.POST.get('email'), password=request.POST.get('password'))
    if user:
        login(request, user)
        if user.user_type == "1":
            return HttpResponseRedirect('/admin_home')
        elif user.user_type == "2":
            return HttpResponseRedirect(reverse("staff_home"))
        else:
            return HttpResponseRedirect(reverse("student_home"))
    else:
        messages.error(request, 'Invalid Login Details')
        return HttpResponseRedirect('/')

def GetUserDetails(request):
    if request.user:
        return HttpResponse(f"User: {request.user.email}, usertype: {request.user.user_type}")
    return HttpResponse("Please Login First")

def Logout_user(request):
    logout(request)
    return HttpResponseRedirect("/")

def monitoring_ui(request):
    return render(request, 'monitor.html')


# ======================== API ROUTES ========================

@api_view(['GET'])
def student_list(request):
    students = Students.objects.all()
    serializer = StudentSerializer(students, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def subject_list(request):
    subjects = Subjects.objects.all()
    serializer = SubjectSerializer(subjects, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def get_latest_rfids(request):
    try:
        rfid_file = os.path.join(os.getcwd(), "rfid_tags.txt")
        if not os.path.exists(rfid_file):
            return Response({"rfids": []})

        with open(rfid_file, "r") as file:
            rfids = file.read().splitlines()

        return Response({"rfids": rfids})
    except Exception as e:
        print(f"[RFID ERROR] {e}")
        return Response({"rfids": [], "error": "Could not read RFID tags"}, status=500)


# ======================== ATTENDANCE LOGIC ========================

def process_attendance(subject_id, image):
    try:
        schedule = SubjectSchedule.objects.get(id=int(subject_id))
        subject = schedule.subject
    except SubjectSchedule.DoesNotExist:
        raise Exception("Invalid subject ID")

    enrollment = Enrollment.objects.filter(subject=subject).first()
    if not enrollment:
        raise Exception("No enrollment found for subject")
    
    session_year = enrollment.student.session_year_id

    embedding = extract_face_embedding(image)
    if not embedding:
        raise Exception("No face detected")
    input_encoding = np.array(embedding)

    matched_student = None
    for student in Students.objects.exclude(face_encoding=None):
        try:
            db_encoding = np.array(json.loads(student.face_encoding))
            similarity = np.dot(input_encoding, db_encoding) / (
                np.linalg.norm(input_encoding) * np.linalg.norm(db_encoding)
            )
            if similarity > 0.6:
                matched_student = student
                break
        except Exception:
            continue

    if not matched_student:
        raise Exception("No matching student found")

    try:
        with open("rfid_tags.txt", "r") as file:
            rfids = file.read().splitlines()
    except Exception:
        raise Exception("RFID file read error")

    if matched_student.rfid not in rfids:
        raise Exception("RFID not detected or already used")

    with open("used_rfid_tags.txt", "a") as file:
        file.write(f"{matched_student.rfid}\n")

    now_time = timezone.now().time()
    start_time = schedule.start_time
    minutes_late = (datetime.combine(date.today(), now_time) - datetime.combine(date.today(), start_time)).total_seconds() / 60

    if minutes_late <= 15:
        status = "Present"
    elif minutes_late <= 30:
        status = "Late"
    else:
        status = "Absent"

    attendance, _ = Attendance.objects.get_or_create(
        subject=subject,
        schedule=schedule,
        session_year=session_year,
        attendance_date=date.today()
    )

    report, created = AttendanceReport.objects.get_or_create(
        student=matched_student,
        attendance=attendance
    )

    if not report.created_at:
        report.created_at = timezone.now()

    report.status = status
    report.save()
    attendance.students.add(matched_student)

    formatted_name = f"{matched_student.admin.last_name}, {matched_student.admin.first_name[0]}"
    return {
        "message": f"{status} recorded for {formatted_name}.",
        "rfid": matched_student.rfid,
        "status": status,
        "formatted_name": formatted_name,
        "attendance_time": report.created_at.strftime("%I:%M %p")
    }


@csrf_exempt
@require_api_key
@api_view(['POST'])
@parser_classes([MultiPartParser])
def auto_mark_attendance_live(request):
    subject_id = request.POST.get("subject_id")
    image = request.FILES.get("image")

    if not subject_id or not image:
        return Response({"error": "Missing subject_id or image"}, status=400)

    try:
        result = process_attendance(subject_id, image)
        return Response(result)
    except Exception as e:
        return Response({"error": str(e)}, status=400)


@api_view(['GET'])
@require_api_key
def get_ongoing_subject(request):
    try:
        now_time = timezone.now().time()
        today = timezone.now().strftime("%A")

        today_subjects = SubjectSchedule.objects.filter(day_of_week=today).order_by("start_time")
        current = today_subjects.filter(start_time__lte=now_time, end_time__gte=now_time).first()

        if current:
            return Response({
                "subject_id": current.id,
                "subject_name": current.subject.subject_name,
                "start_time": str(current.start_time),
                "end_time": str(current.end_time),
                "message": "Ongoing class is active"
            })

        last = today_subjects.last()
        if last and now_time > last.end_time:
            return Response({"message": "All scheduled classes for today have ended."})

        next_class = today_subjects.filter(start_time__gt=now_time).first()
        if next_class:
            return Response({
                "next_subject_id": next_class.id,
                "next_subject_name": next_class.subject.subject_name,
                "next_start_time": str(next_class.start_time),
                "next_end_time": str(next_class.end_time),
                "message": "Waiting for the next class to start"
            })

        return Response({"error": "No ongoing class at the moment."}, status=404)

    except Exception as e:
        print(f"[Schedule Error] {e}")
        return Response({"error": "Server error"}, status=500)


class AttendanceMarkAPIView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request, *args, **kwargs):
        serializer = AttendanceInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        subject_id = serializer.validated_data['subject_id']
        image = serializer.validated_data['image']

        try:
            result = process_attendance(subject_id, image)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

RFID_LOG_FILE = 'rfid_tags.txt'

@csrf_exempt
def rfid_endpoint(request):
    if request.method == 'POST':
        rfid = request.POST.get('rfid')
        if rfid:
            # Ensure file exists
            if not os.path.exists(RFID_LOG_FILE):
                open(RFID_LOG_FILE, 'w').close()

            # Read all existing RFID tags
            with open(RFID_LOG_FILE, 'r') as f:
                existing_rfids = set(line.strip() for line in f)

            if rfid not in existing_rfids:
                with open(RFID_LOG_FILE, 'a') as f:
                    f.write(rfid + '\n')
                return JsonResponse({'status': 'success', 'rfid': rfid})
            else:
                return JsonResponse({'status': 'duplicate', 'rfid': rfid})
        return JsonResponse({'status': 'error', 'message': 'Missing RFID'}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=405)
