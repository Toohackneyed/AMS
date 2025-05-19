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
from django.utils.dateparse import parse_date

from ams_app.models import SubjectSchedule, Subjects, SessionYearModel, Students, Attendance, AttendanceReport, \
     Staffs, CustomUser, Courses, Sections, Enrollment
from django.contrib.auth.decorators import login_required
import pandas as pd
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden

@login_required
def staff_home(request):
    staff = Staffs.objects.get(admin=request.user.id)
    subjects = Subjects.objects.filter(staff=staff)
    course_id_list = list(subjects.values_list('course_id', flat=True).distinct())
    students_count = Students.objects.filter(course_id__in=course_id_list).count()
    attendance_count = Attendance.objects.filter(subject_id__in=subjects).count()
    subject_count = subjects.count()
    subject_list = []
    student_population_list = []

    for subject in subjects:
        student_count = Students.objects.filter(course_id=subject.course).count()
        subject_list.append(subject.subject_name)
        student_population_list.append(student_count)

    attendance_list = [Attendance.objects.filter(subject_id=subject.id).count() for subject in subjects]

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

def staff_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.user_type != '2':
            return HttpResponseForbidden("Staff access only.")
        return view_func(request, *args, **kwargs)
    return wrapper

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
            start_date = parse_date(data.get("start_date"))
            end_date = parse_date(data.get("end_date"))
            get_all_schedules = data.get("get_all_schedules", False)

            subject = Subjects.objects.get(id=subject_id)
            if subject.staff != staff:
                return JsonResponse({"error": "Unauthorized access to subject."}, status=403)

            if get_all_schedules:
                schedule_objs = SubjectSchedule.objects.filter(subject_id=subject_id)
            else:
                schedule_objs = SubjectSchedule.objects.filter(id=schedule_id)

            students = Students.objects.filter(
                enrollment__subject_id=subject_id,
                session_year_id=session_year_id
            )
            if section_id:
                students = students.filter(section_id=section_id)
            students = students.distinct()

            data_list = []
            current_date = start_date

            while current_date <= end_date:
                weekday_str = current_date.strftime("%A")

                for schedule_obj in schedule_objs:
                    if schedule_obj.day_of_week != weekday_str:
                        continue

                    attendance = Attendance.objects.filter(
                        subject_id=subject_id,
                        session_year_id=session_year_id,
                        schedule_id=schedule_obj.id,
                        attendance_date=current_date
                    ).first()

                    attended_ids = set()

                    if attendance:
                        for report in attendance.attendancereport_set.all():
                            student = report.student
                            student_name = f"{student.admin.first_name} {student.admin.last_name}"
                            schedule_str = f"{schedule_obj.day_of_week} ({schedule_obj.start_time} - {schedule_obj.end_time})"
                            status = report.status

                            data_list.append([
                                student_name,
                                str(current_date),
                                schedule_str,
                                status,
                                subject.subject_name
                            ])
                            attended_ids.add(student.id)

                    schedule_str = f"{schedule_obj.day_of_week} ({schedule_obj.start_time} - {schedule_obj.end_time})"
                    for student in students:
                        if student.id not in attended_ids:
                            student_name = f"{student.admin.first_name} {student.admin.last_name}"
                            data_list.append([
                                student_name,
                                str(current_date),
                                schedule_str,
                                "Absent",
                                subject.subject_name
                            ])

                current_date += timedelta(days=1)

            df = pd.DataFrame(data_list, columns=["Student Name", "Date", "Schedule", "Status", "Subject"])

            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename="staff_attendance.xlsx"'
            df.to_excel(response, index=False)

            return response

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

@login_required
@staff_required
def staff_update_attendance_view(request):
    staff = Staffs.objects.get(admin=request.user)
    subjects = Subjects.objects.filter(staff=staff)
    schedules = SubjectSchedule.objects.filter(subject__in=subjects)
    session_years = SessionYearModel.objects.all()
    current_session = SessionYearModel.objects.first()

    context = {
        'subjects': subjects,
        'schedules': schedules,
        'session_years': session_years,
        'current_session_id': current_session.id
    }

    return render(request, 'staff_template/staff_update_attendance.html', context)


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
            start_date = parse_date(data.get("start_date"))
            end_date = parse_date(data.get("end_date"))
            get_all_schedules = data.get("get_all_schedules", False)

            subject = Subjects.objects.get(id=subject_id)
            if subject.staff != staff:
                return JsonResponse({"error": "Unauthorized access to subject."}, status=403)

            if get_all_schedules:
                schedule_objs = SubjectSchedule.objects.filter(subject_id=subject_id)
            else:
                schedule_objs = SubjectSchedule.objects.filter(id=schedule_id)

            students = Students.objects.filter(
                enrollment__subject_id=subject_id,
                session_year_id=session_year_id
            )
            if section_id:
                students = students.filter(section_id=section_id)
            students = students.distinct()

            response_data = []
            current_date = start_date

            while current_date <= end_date:
                weekday_str = current_date.strftime("%A")

                for schedule_obj in schedule_objs:
                    if schedule_obj.day_of_week != weekday_str:
                        continue  # Skip non-matching day

                    attendance = Attendance.objects.filter(
                        subject_id=subject_id,
                        session_year_id=session_year_id,
                        schedule_id=schedule_obj.id,
                        attendance_date=current_date
                    ).first()

                    attended_ids = set()
                    reports_map = {}

                    if attendance:
                        reports = attendance.attendancereport_set.all()
                        for report in reports:
                            reports_map[report.student.id] = report
                            attended_ids.add(report.student.id)

                    for student in students:
                        student_name = f"{student.admin.first_name} {student.admin.last_name}"

                        if student.id in reports_map:
                            report = reports_map[student.id]
                            response_data.append({
                                "student_name": student_name,
                                "student_id": student.id,
                                "status": report.status,
                                "attendance_id": report.attendance.id,
                                "subject_name": subject.subject_name,
                                "schedule": f"{schedule_obj.day_of_week} ({schedule_obj.start_time} - {schedule_obj.end_time})",
                                "date": str(current_date)
                            })
                        else:
                            response_data.append({
                                "student_name": student_name,
                                "student_id": student.id,
                                "status": "Absent",
                                "attendance_id": attendance.id if attendance else None,
                                "subject_name": subject.subject_name,
                                "schedule": f"{schedule_obj.day_of_week} ({schedule_obj.start_time} - {schedule_obj.end_time})",
                                "date": str(current_date)
                            })

                current_date += timedelta(days=1)

            return JsonResponse(response_data, safe=False)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

@login_required
@staff_required
@csrf_exempt
@login_required
@staff_required
@csrf_exempt
def save_updated_attendance(request):
    try:
        if request.method == "POST":
            data = json.loads(request.body)
            attendance_id = data.get("attendance_id")
            student_id = data.get("student_id")
            new_status = data.get("status")
            subject_id = data.get("subject_id")
            session_year_id = data.get("session_year_id")
            schedule_id = data.get("schedule_id")
            date = data.get("date")

            student = Students.objects.get(id=student_id)

            if attendance_id:
                attendance = Attendance.objects.get(id=attendance_id)
            else:
                attendance_date = parse_date(date)
                subject = Subjects.objects.get(id=subject_id)
                session_year = SessionYearModel.objects.get(id=session_year_id)
                schedule = SubjectSchedule.objects.get(id=schedule_id)

                attendance, created = Attendance.objects.get_or_create(
                    subject=subject,
                    session_year=session_year,
                    schedule=schedule,
                    attendance_date=attendance_date
                )

            report = AttendanceReport.objects.filter(attendance=attendance, student=student).first()
            if report:
                report.status = new_status
                report.save()
            else:
                AttendanceReport.objects.create(
                    student=student,
                    attendance=attendance,
                    status=new_status
                )

            return JsonResponse({"success": True})

        return JsonResponse({"error": "Invalid request."}, status=400)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@login_required
def staff_profile(request):
    user = request.user
    staff = get_object_or_404(Staffs, admin=user)
    return render(request, "staff_template/staff_profile.html", {"user": user, "staff": staff})

@login_required
def staff_profile_save(request):
    if request.method != "POST":
        return HttpResponseRedirect(reverse("staff_profile"))

    first_name = request.POST.get("first_name")
    last_name = request.POST.get("last_name")
    password = request.POST.get("password")

    try:
        customuser = request.user 
        staff = get_object_or_404(Staffs, admin=customuser)
        customuser.first_name = first_name
        customuser.last_name = last_name

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
        subjects = []
    except Subjects.DoesNotExist:
        enrolled_students = []

    context = {
        'subjects': subjects,
        'selected_subject_id': selected_subject_id,
        'enrolled_students': enrolled_students,
    }
    return render(request, 'staff_template/students_by_subject.html', context)