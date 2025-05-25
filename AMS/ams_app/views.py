from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from datetime import datetime, date
from ams_app.models import Students, Subjects, Enrollment, Attendance, AttendanceReport, SubjectSchedule
from ams_app.serializers import StudentSerializer, SubjectSerializer  # Add this import
from utils.face_utils import extract_face_embedding  # Assumes your utility is here
import numpy as np
import os
import json
from datetime import datetime
from django.utils.timezone import now
from django.conf import settings
from django.shortcuts import render  # Add this import
from django.urls import reverse  # Import reverse for URL reversing
from ams_app.EmailBackEnd import EmailBackEnd  # Add this import for authentication
from django.contrib.auth import login, logout  # Import login and logout functions
from django.contrib import messages  # Import messages framework
# from ams_app.utils import clear_used_rfid_tags

# Stub for recognize_face - replace with actual implementation
def recognize_face(image):
    """
    Dummy face recognition function.
    Replace this with actual face recognition logic.
    Should return a Students instance if recognized, else None.
    """
    # Example: always return None (face not recognized)
    return None

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
        rfid_file_path = os.path.join(os.getcwd(), "rfid_tags.txt")

        if not os.path.exists(rfid_file_path):
            return Response({"rfids": []})

        with open(rfid_file_path, "r") as file:
            tags = file.read().splitlines()

        return Response({"rfids": tags})
    except Exception as e:
        print(f"⚠️ Error reading RFID tags: {e}")
        return Response({"rfids": [], "error": "Could not read RFID tags"}, status=500)

@csrf_exempt
def auto_mark_attendance_live(request):
    print("\n🔍 DEBUG: Request received!")

    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    subject_id = request.POST.get("subject_id")
    image = request.FILES.get("image")

    if not subject_id or subject_id == "undefined":
        return JsonResponse({"error": "Invalid subject ID"}, status=400)

    if not image:
        return JsonResponse({"error": "Missing image"}, status=400)

    try:
        subject_id = int(subject_id)
        subject_schedule = SubjectSchedule.objects.get(id=subject_id)
        actual_subject = subject_schedule.subject

        enrollment = Enrollment.objects.filter(subject=actual_subject).first()
        if not enrollment:
            return JsonResponse({"error": "No session year found"}, status=400)
        session_year = enrollment.student.session_year_id

        input_embedding = extract_face_embedding(image)
        if not input_embedding:
            return JsonResponse({"error": "No face detected"}, status=400)

        input_embedding = np.array(input_embedding)

        students = Students.objects.exclude(face_encoding=None)
        matched_student = None

        for student in students:
            try:
                db_encoding = np.array(json.loads(student.face_encoding))
                similarity = np.dot(input_embedding, db_encoding) / (
                    np.linalg.norm(input_embedding) * np.linalg.norm(db_encoding)
                )
                if similarity > 0.6:
                    matched_student = student
                    break
            except Exception as e:
                print(f"⚠️ Error processing student {student.id}: {e}")
                continue

        if not matched_student:
            return JsonResponse({"error": "Face not recognized"}, status=404)

        matched_name = matched_student.admin.get_full_name()
        stored_rfid = matched_student.rfid
        print(f"🔑 Recognized {matched_name} with RFID {stored_rfid}")

        if not Enrollment.objects.filter(student=matched_student, subject=actual_subject).exists():
            return JsonResponse({"error": "Student not enrolled in subject"}, status=400)

        try:
            with open("rfid_tags.txt", "r") as file:
                tags = file.read().splitlines()
        except Exception:
            return JsonResponse({"error": "RFID tag file error"}, status=500)

        if stored_rfid not in tags:
            return JsonResponse({"error": "RFID not detected or already used"}, status=400)

        with open("used_rfid_tags.txt", "a") as used_file:
            used_file.write(f"{stored_rfid}\n")

        now_time = timezone.now().time()
        start_time = subject_schedule.start_time
        time_diff = datetime.combine(date.today(), now_time) - datetime.combine(date.today(), start_time)
        minutes_late = time_diff.total_seconds() / 60

        if minutes_late <= 15:
            status = "Present"
        elif 15 < minutes_late <= 30:
            status = "Late"
        else:
            status = "Absent"

        attendance, _ = Attendance.objects.get_or_create(
            subject=actual_subject,
            schedule=subject_schedule,
            session_year=session_year,
            attendance_date=date.today()
        )

        report, created = AttendanceReport.objects.get_or_create(
            student=matched_student,
            attendance=attendance
        )

        if not report.created_at:
            report.created_at = timezone.now()
            report.save()

        attendance_time = report.created_at.strftime("%I:%M:%S %p")

        # Update status only if newly created
        if created:
            report.status = status
            report.save()
            attendance.students.add(matched_student)

        last_name = matched_student.admin.last_name
        first_initial = matched_student.admin.first_name[0] if matched_student.admin.first_name else ""
        formatted_name = f"{last_name}, {first_initial}"

        print(f"✅ Marked {status} for {formatted_name} at {attendance_time}")

        return JsonResponse({
            "message": f"{status} recorded for {formatted_name}.",
            "rfid": stored_rfid,
            "status": status,
            "formatted_name": formatted_name,
            "attendance_time": attendance_time
        })

    except Exception as e:
        print(f"⚡ ERROR: {e}")
        return JsonResponse({"error": "Error processing image"}, status=500)

@api_view(['GET'])
def get_ongoing_subject(request):
    try:
        current_time = now().time()
        today = now().strftime("%A")

        subjects_today = SubjectSchedule.objects.filter(day_of_week=today).order_by("start_time")
        ongoing_subject = subjects_today.filter(
            start_time__lte=current_time,
            end_time__gte=current_time
        ).first()

        if ongoing_subject:
            return Response({
                "subject_id": ongoing_subject.id,
                "subject_name": ongoing_subject.subject.subject_name,
                "start_time": str(ongoing_subject.start_time),
                "end_time": str(ongoing_subject.end_time),
                "message": "Ongoing class is active"
            })

        # End of all scheduled classes
        last_class = subjects_today.last()
        if last_class and current_time > last_class.end_time:
            # clear_used_rfid_tags()
            return Response({"message": "All scheduled classes for today have ended."}, status=200)

        # Look for upcoming class
        next_class = subjects_today.filter(start_time__gt=current_time).first()
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
        print(f"⚠️ Error in get_ongoing_subject: {e}")
        return Response({"error": "Server error"}, status=500)
    
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