import json
from datetime import datetime, timedelta
from uuid import uuid4
import openpyxl
from openpyxl.styles import Font

from django.contrib import messages
from django.core import serializers
from django.forms import model_to_dict
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from ams_app.models import SubjectSchedule, Subjects, SessionYearModel, Students, Attendance, AttendanceReport, \
     Staffs, CustomUser, Courses, Sections, Enrollment
from django.contrib.auth.decorators import login_required
import pandas as pd
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden

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
        {"value": attendance_count, "label": "Total Attendance Taken", "color": "bg-success", "icon": "ion ion-checkmark", "url": reverse('staff_view_attendance')},
        {"value": sum(student_population_list), "label": "Student Population Per Subject", "color": "bg-warning", "icon": "ion ion-person", "url": "#"},
    ]

    context = {
        "dashboard_boxes": dashboard_boxes,
        "subject_list": subject_list,
        "student_population_list": student_population_list,
        "attendance_list": attendance_list,
    }

    return render(request, "staff_template/staff_home_template.html", context)

@csrf_exempt
def get_sections_by_session_year(request):
    """ Fetch sections based on selected session year """
    if request.method == 'POST':
        session_year_id = request.POST.get('session_year')
        sections = Sections.objects.filter(session_year_id=session_year_id)
        section_data = [{"id": section.id, "name": section.section_name} for section in sections]
        return JsonResponse(section_data, safe=False)
    return JsonResponse({'error': 'Invalid request'}, status=400)

# ✅ Decorator for Staff-only access
def staff_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.user_type != '2':  # 2 = staff
            return HttpResponseForbidden("Staff access only.")
        return view_func(request, *args, **kwargs)
    return wrapper


# ✅ Staff View for Attendance Page
@login_required
@staff_required
def staff_view_attendance(request):
    staff = Staffs.objects.get(admin=request.user)
    subjects = Subjects.objects.filter(staff=staff)
    schedules = SubjectSchedule.objects.filter(subject__in=subjects)
    session_years = SessionYearModel.objects.all()
    sections = Sections.objects.all()

    context = {
        'subjects': subjects,
        'schedules': schedules,
        'session_years': session_years,
        'sections': sections
    }
    return render(request, "staff_template/staff_view_attendance.html", context)


# ✅ Reused API: Get Attendance (with staff access check)
@csrf_exempt
@login_required
@staff_required
def staff_get_attendance(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            staff = Staffs.objects.get(admin=request.user)

            subject_id = data.get("subject")
            session_year_id = data.get("session_year")
            schedule_id = data.get("schedule")
            section_id = data.get("section")
            start_date = data.get("start_date")
            end_date = data.get("end_date")

            # ✅ Ensure subject belongs to staff
            if not Subjects.objects.filter(id=subject_id, staff=staff).exists():
                return JsonResponse({"error": "Unauthorized access to subject."}, status=403)

            attendance_filter = {
                'subject_id': subject_id,
                'session_year_id': session_year_id,
                'attendance_date__range': (start_date, end_date)
            }

            if section_id:
                attendance_filter['students__section_id'] = section_id

            attendance_records = Attendance.objects.filter(**attendance_filter)\
                .select_related("subject", "session_year", "schedule")\
                .prefetch_related("attendancereport_set__student__admin")\
                .distinct()

            response_data = []
            seen_attendance = set()

            for attendance in attendance_records:
                for report in attendance.attendancereport_set.all():
                    student_name = f"{report.student.admin.first_name} {report.student.admin.last_name}"
                    schedule_str = f"{attendance.schedule.day_of_week} ({attendance.schedule.start_time} - {attendance.schedule.end_time})"
                    status = report.status

                    key = (attendance.attendance_date, attendance.schedule_id, student_name)
                    if key not in seen_attendance:
                        seen_attendance.add(key)
                        response_data.append({
                            "student_name": student_name,
                            "date": str(attendance.attendance_date),
                            "schedule": schedule_str,
                            "status": status,
                            "subject_name": attendance.subject.subject_name
                        })

            return JsonResponse(response_data, safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


# ✅ Reused API: Download Attendance (with staff access check)
@csrf_exempt
@login_required
@staff_required
def staff_download_attendance(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            staff = Staffs.objects.get(admin=request.user)

            subject_id = data.get("subject")
            session_year_id = data.get("session_year")
            schedule_id = data.get("schedule")
            section_id = data.get("section")
            start_date = data.get("start_date")
            end_date = data.get("end_date")

            if not Subjects.objects.filter(id=subject_id, staff=staff).exists():
                return JsonResponse({"error": "Unauthorized access to subject."}, status=403)

            attendance_filter = {
                'subject_id': subject_id,
                'session_year_id': session_year_id,
                'attendance_date__range': (start_date, end_date)
            }

            if section_id:
                attendance_filter['students__section_id'] = section_id

            attendance_records = Attendance.objects.filter(**attendance_filter)\
                .select_related("subject", "session_year", "schedule")\
                .prefetch_related("attendancereport_set__student__admin")\
                .distinct()

            data_list = []
            seen_attendance = set()

            for attendance in attendance_records:
                for report in attendance.attendancereport_set.all():
                    student_name = f"{report.student.admin.first_name} {report.student.admin.last_name}"
                    schedule_str = f"{attendance.schedule.day_of_week} ({attendance.schedule.start_time} - {attendance.schedule.end_time})"
                    status = report.status

                    key = (attendance.attendance_date, attendance.schedule_id, student_name)
                    if key not in seen_attendance:
                        seen_attendance.add(key)
                        data_list.append([
                            student_name,
                            str(attendance.attendance_date),
                            schedule_str,
                            status,
                            attendance.subject.subject_name
                        ])

            df = pd.DataFrame(data_list, columns=["Student Name", "Date", "Schedule", "Status", "Subject"])

            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename="staff_attendance.xlsx"'
            df.to_excel(response, index=False)

            return response

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

@login_required
def staff_update_attendance_view(request):
    staff = Staffs.objects.get(admin=request.user)
    subjects = Subjects.objects.filter(staff=staff)
    schedules = SubjectSchedule.objects.filter(subject__in=subjects)

    context = {
        'subjects': subjects,
        'schedules': schedules
    }
    return render(request, "staff_template/staff_update_attendance.html", context)

@csrf_exempt
@login_required
def fetch_attendance_for_update(request):
    if request.method == "POST":
        data = json.loads(request.body)
        subject_id = data.get("subject")
        schedule_id = data.get("schedule")
        date = data.get("date")

        staff = Staffs.objects.get(admin=request.user)

        # Secure check
        if not Subjects.objects.filter(id=subject_id, staff=staff).exists():
            return JsonResponse({"error": "Unauthorized access"}, status=403)

        attendance = Attendance.objects.filter(subject_id=subject_id, schedule_id=schedule_id, attendance_date=date).first()

        if not attendance:
            return JsonResponse({"error": "No attendance record found for that date."}, status=404)

        reports = AttendanceReport.objects.filter(attendance=attendance).select_related("student__admin")

        response_data = []
        for r in reports:
            student_name = f"{r.student.admin.first_name} {r.student.admin.last_name}"
            response_data.append({
                "report_id": r.id,
                "student_name": student_name,
                "status": r.status
            })

        return JsonResponse({"reports": response_data})

@csrf_exempt
@login_required
def save_updated_attendance(request):
    if request.method == "POST":
        data = json.loads(request.body)
        updates = data.get("updates")

        for item in updates:
            report_id = item.get("report_id")
            new_status = item.get("status")

            report = get_object_or_404(AttendanceReport, id=report_id)
            report.status = new_status
            report.save()

        return JsonResponse({"success": "Attendance updated successfully."})

@login_required
def staff_profile(request):
    user = request.user  # Get the logged-in user
    staff = get_object_or_404(Staffs, admin=user)  # Ensures staff exists
    return render(request, "staff_template/staff_profile.html", {"user": user, "staff": staff})

@login_required
def staff_profile_save(request):
    if request.method != "POST":
        return HttpResponseRedirect(reverse("staff_profile"))

    first_name = request.POST.get("first_name")
    last_name = request.POST.get("last_name")
    password = request.POST.get("password")

    try:
        customuser = request.user  # Get the logged-in user
        staff = get_object_or_404(Staffs, admin=customuser)  # Ensures staff exists

        # Update user details
        customuser.first_name = first_name
        customuser.last_name = last_name

        # Update password only if it's provided
        if password and password.strip():
            customuser.set_password(password)

        customuser.save()
        staff.save()

        messages.success(request, "Successfully Updated Profile")
        return HttpResponseRedirect(reverse("staff_profile"))

    except Exception as e:
        messages.error(request, f"Failed to Update Profile: {str(e)}")
        return HttpResponseRedirect(reverse("staff_profile"))
    
def students_by_subject(request):
    enrolled_students = []
    selected_subject_id = request.GET.get('subject_id')

    try:
        staff_instance = Staffs.objects.get(admin=request.user)
        subjects = Subjects.objects.filter(staff=staff_instance)

        if selected_subject_id:
            selected_subject = Subjects.objects.get(id=selected_subject_id, staff=staff_instance)
            enrolled_students = Enrollment.objects.filter(subject=selected_subject).select_related('student')

    except Staffs.DoesNotExist:
        subjects = []  # Staff not found = walang subject
    except Subjects.DoesNotExist:
        enrolled_students = []  # Subject ID not owned by this staff

    context = {
        'subjects': subjects,
        'selected_subject_id': selected_subject_id,
        'enrolled_students': enrolled_students,
    }
    return render(request, 'staff_template/students_by_subject.html', context)