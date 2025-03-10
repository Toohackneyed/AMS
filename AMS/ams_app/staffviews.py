import json
from datetime import datetime, timedelta
from uuid import uuid4

from django.contrib import messages
from django.core import serializers
from django.forms import model_to_dict
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from ams_app.models import SubjectSchedule, Subjects, SessionYearModel, Students, Attendance, AttendanceReport, \
     Staffs, CustomUser, Courses


@login_required
def staff_home(request):
    # Get all subjects assigned to the logged-in staff
    staff = Staffs.objects.get(admin=request.user.id)
    subjects = Subjects.objects.filter(staff=staff)

    # Get all unique course IDs handled by the staff
    course_id_list = list(subjects.values_list('course_id', flat=True).distinct())

    # Count total students under the staff
    students_count = Students.objects.filter(course_id__in=course_id_list).count()

    # Count total attendance taken by staff
    attendance_count = Attendance.objects.filter(subject_id__in=subjects).count()

    # Count total subjects handled by staff
    subject_count = subjects.count()

    # Fetch student population per subject
    subject_list = []
    student_population_list = []

    for subject in subjects:
        student_count = Students.objects.filter(course_id=subject.course).count()
        subject_list.append(subject.subject_name)
        student_population_list.append(student_count)

    # Fetch attendance data per subject
    attendance_list = [Attendance.objects.filter(subject_id=subject.id).count() for subject in subjects]

    # Prepare dashboard boxes
    dashboard_boxes = [
        {"value": subject_count, "label": "Total Subjects", "color": "bg-danger", "icon": "ion ion-stats-bars", "url": "#"},
        {"value": students_count, "label": "Total Students in My Subjects", "color": "bg-info", "icon": "ion ion-person-stalker", "url": "#"},
        {"value": attendance_count, "label": "Total Attendance Taken", "color": "bg-success", "icon": "ion ion-checkmark", "url": reverse('staff_take_attendance')},
        {"value": sum(student_population_list), "label": "Student Population Per Subject", "color": "bg-warning", "icon": "ion ion-person", "url": "#"},
    ]

    context = {
        "dashboard_boxes": dashboard_boxes,
        "subject_list": subject_list,
        "student_population_list": student_population_list,
        "attendance_list": attendance_list,
    }

    return render(request, "staff_template/staff_home_template.html", context)

def staff_take_attendance(request):
    subjects = Subjects.objects.all()
    schedules = SubjectSchedule.objects.all()
    session_years = SessionYearModel.objects.all()  

    return render(request, "staff_template/staff_take_attendance.html", {
        "subjects": subjects,
        "schedules": schedules,
        "session_years": session_years,
    })

@csrf_exempt
def get_students(request):
    if request.method == "POST":
        subject_id = request.POST.get("subject")
        session_year_id = request.POST.get("session_year")
        schedule_id = request.POST.get("schedule")
        all_schedules = request.POST.get("all_schedules")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")

        try:
            subject = Subjects.objects.get(id=subject_id)
            students = Students.objects.filter(course_id=subject.course_id, session_year_id=session_year_id)

            # ✅ Gamitin ang tamang field sa Attendance filtering
            attendance_records = Attendance.objects.filter(
                subject_id=subject_id,  # Gamitin ang `subject_id`, hindi `subject`
                attendance_date__range=[start_date, end_date]
            )

            list_data = []
            for student in students:
                list_data.append({
                    "id": student.admin.id,
                    "name": f"{student.admin.first_name} {student.admin.last_name}"
                })

            return JsonResponse(list_data, safe=False)

        except Subjects.DoesNotExist:
            return JsonResponse({"error": "Subject not found"}, status=400)
    return JsonResponse({"error": "Invalid request method"}, status=405)

@csrf_exempt
def save_attendance_data(request):
    if request.method == "POST":
        print("✅ Received POST request for saving attendance.")

        student_data = json.loads(request.POST.get("student_ids"))
        subject_id = request.POST.get("subject_id")
        session_year_id = request.POST.get("session_year_id")
        schedule_id = request.POST.get("schedule_id")
        attendance_date = request.POST.get("start_date")  # Start date ang gagamitin

        print(f"📌 Data Received: subject_id={subject_id}, session_year_id={session_year_id}, schedule_id={schedule_id}, attendance_date={attendance_date}")
        print("📌 Student Data:", student_data)

        try:
            subject = Subjects.objects.get(id=subject_id)
            session_year = SessionYearModel.objects.get(id=session_year_id)
            schedule = SubjectSchedule.objects.get(id=schedule_id)

            # ✅ CHECK: May existing attendance record na ba sa araw na ito?
            attendance, created = Attendance.objects.get_or_create(
                subject_id=subject,
                schedule=schedule,
                session_year_id=session_year,
                attendance_date=attendance_date
            )

            for student in student_data:
                student_instance = Students.objects.get(admin_id=student["id"])
                
                # ✅ SAVE sa AttendanceReport (Student Attendance)
                AttendanceReport.objects.update_or_create(
                    student=student_instance,
                    attendance=attendance,
                    defaults={"status": student["status"]}  # Update status kung meron na
                )

                print(f"📌 Attendance saved for: {student_instance.admin.first_name} {student_instance.admin.last_name} (Status: {student['status']})")

            print("✅ Attendance saved successfully!")
            return JsonResponse("OK", safe=False)

        except Subjects.DoesNotExist:
            print("❌ ERROR: Subject not found!")
            return JsonResponse({"error": "Subject not found"}, status=400)
        except Students.DoesNotExist:
            print("❌ ERROR: Student not found!")
            return JsonResponse({"error": "Student not found"}, status=400)
        except SessionYearModel.DoesNotExist:
            print("❌ ERROR: Session year not found!")
            return JsonResponse({"error": "Session year not found"}, status=400)
        except SubjectSchedule.DoesNotExist:
            print("❌ ERROR: Schedule not found!")
            return JsonResponse({"error": "Schedule not found"}, status=400)
        except Exception as e:
            print(f"❌ ERROR: {e}")
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)

@csrf_exempt
def filter_attendance(request):
    if request.method == "POST":
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")

        try:
            attendance_records = Attendance.objects.filter(attendance_date__range=[start_date, end_date])

            list_data = []
            for record in attendance_records:
                list_data.append({
                    "student": f"{record.student.admin.first_name} {record.student.admin.last_name}",
                    "date": record.attendance_date,
                    "status": "Present" if record.status == 1 else "Absent"
                })

            return JsonResponse(list_data, safe=False)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)

def staff_update_attendance(request):
    staff = Staffs.objects.get(admin=request.user)

    # Get subjects handled by this staff
    subjects = Subjects.objects.filter(staff=staff)

    # Get schedules related to these subjects
    schedules = SubjectSchedule.objects.filter(subject__in=subjects)

    # Get session years
    session_years = SessionYearModel.objects.all()

    context = {
        'subjects': subjects,
        'schedules': schedules,
        'session_years': session_years
    }

    return render(request, "staff_template/staff_update_attendance.html", context)


@csrf_exempt
def get_students(request):
    if request.method == 'POST':
        subject_id = request.POST.get('subject')
        session_year_id = request.POST.get('session_year')
        schedule_id = request.POST.get('schedule')
        all_schedules = request.POST.get('all_schedules') == '1'
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        # Fetch students based on subject and session year
        students = Students.objects.filter(course_id__subjects__id=subject_id, session_year_id=session_year_id).distinct()

        # Format the response
        student_data = [{"id": student.id, "name": student.admin.get_full_name()} for student in students]

        return JsonResponse(student_data, safe=False)

    return JsonResponse({'error': 'Invalid request'}, status=400)


@csrf_exempt
def save_attendance_data(request):
    if request.method == 'POST':
        data = json.loads(request.POST.get('student_ids'))
        subject_id = request.POST.get('subject_id')
        session_year_id = request.POST.get('session_year_id')
        schedule_id = request.POST.get('schedule_id')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        # Ensure date is in the correct format
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()

        # Save attendance
        attendance = Attendance(
            subject_id=Subjects.objects.get(id=subject_id),
            session_year_id=SessionYearModel.objects.get(id=session_year_id),
            schedule=SubjectSchedule.objects.get(id=schedule_id),
            attendance_date=start_date
        )
        attendance.save()

        # Save attendance reports
        for student in data:
            student_instance = Students.objects.get(id=student["id"])
            attendance_report = AttendanceReport(student=student_instance, attendance=attendance, status=student["status"])
            attendance_report.save()

        return JsonResponse("OK", safe=False)

    return JsonResponse({'error': 'Invalid request'}, status=400)

def staff_profile(request):
    user=CustomUser.objects.get(id=request.user.id)
    staff=Staffs.objects.get(admin=user)
    return render(request,"staff_template/staff_profile.html",{"user":user,"staff":staff})

def staff_profile_save(request):
    if request.method!="POST":
        return HttpResponseRedirect(reverse("staff_profile"))
    else:
        first_name=request.POST.get("first_name")
        last_name=request.POST.get("last_name")
        password=request.POST.get("password")
        try:
            customuser=CustomUser.objects.get(id=request.user.id)
            customuser.first_name=first_name
            customuser.last_name=last_name
            if password!=None and password!="":
                customuser.set_password(password)
            customuser.save()

            staff=Staffs.objects.get(admin=customuser.id)
            staff.save()
            messages.success(request, "Successfully Updated Profile")
            return HttpResponseRedirect(reverse("staff_profile"))
        except:
            messages.error(request, "Failed to Update Profile")
            return HttpResponseRedirect(reverse("staff_profile"))
