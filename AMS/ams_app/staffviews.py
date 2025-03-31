import json
from datetime import datetime, timedelta
from uuid import uuid4
import openpyxl
from openpyxl.styles import Font

from django.contrib import messages
from django.core import serializers
from django.forms import model_to_dict
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from ams_app.models import SubjectSchedule, Subjects, SessionYearModel, Students, Attendance, AttendanceReport, \
     Staffs, CustomUser, Courses, Sections


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

@login_required
def staff_take_attendance(request):
    """ Display attendance filtering options for staff """
    subjects = Subjects.objects.all()
    schedules = SubjectSchedule.objects.all()
    session_years = SessionYearModel.objects.all()
    sections = Sections.objects.all()

    context = {
        'subjects': subjects,
        'schedules': schedules,
        'session_years': session_years,
        'sections': sections
    }
    return render(request, "staff_template/staff_take_attendance.html", context)

@csrf_exempt
def get_sections_by_session_year(request):
    """ Fetch sections based on selected session year """
    if request.method == 'POST':
        session_year_id = request.POST.get('session_year')
        sections = Sections.objects.filter(session_year_id=session_year_id)
        section_data = [{"id": section.id, "name": section.section_name} for section in sections]
        return JsonResponse(section_data, safe=False)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
def get_students(request):
    try:
        subject_id = request.POST.get('subject')
        session_year_id = request.POST.get('session_year')
        schedule_id = request.POST.get('schedule')
        section_id = request.POST.get('section')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        get_all_schedules = request.POST.get('get_all_schedules') == 'true'

        if not subject_id or not session_year_id or not start_date or not end_date:
            return JsonResponse({'error': 'Missing required parameters'}, status=400)

        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        filters = {
            'subject_id': int(subject_id),
            'session_year_id': int(session_year_id),
            'attendance_date__range': (start_date, end_date)
        }

        if not get_all_schedules and schedule_id:
            filters['schedule_id'] = int(schedule_id)

        if section_id:
            filters['students__section_id'] = int(section_id)

        attendance_records = Attendance.objects.filter(**filters)

        attendance_data = [
            {
                'student_name': report.student.admin.get_full_name(),
                'date': report.attendance.attendance_date.strftime('%Y-%m-%d'),
                'status': report.status.capitalize()
            }
            for report in AttendanceReport.objects.filter(attendance__in=attendance_records)
        ]

        return JsonResponse(attendance_data, safe=False)

    except Exception as e:
        print(f"Error in get_students: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def download_attendance(request):
    try:
        subject_id = int(request.GET.get('subject'))
        session_year_id = int(request.GET.get('session_year'))
        schedule_id = request.GET.get('schedule')
        section_id = request.GET.get('section')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        attendance_filter = {
            'subject_id': subject_id,
            'session_year_id': session_year_id,
            'attendance_date__range': (start_date, end_date)
        }

        if section_id:
            attendance_filter['students__section_id'] = int(section_id)

        if schedule_id:
            attendance_filter['schedule_id'] = int(schedule_id)

        attendance_records = Attendance.objects.filter(**attendance_filter)

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=attendance.xlsx'

        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = 'Attendance Records'

        headers = ['Student Name', 'Date', 'Status']
        for col_num, header in enumerate(headers, 1):
            cell = sheet.cell(row=1, column=col_num)
            cell.value = header
            cell.font = Font(bold=True)

        row_num = 2
        for attendance in attendance_records:
            reports = AttendanceReport.objects.filter(attendance=attendance)
            for report in reports:
                sheet.cell(row=row_num, column=1).value = report.student.admin.get_full_name()
                sheet.cell(row=row_num, column=2).value = str(attendance.attendance_date)
                sheet.cell(row=row_num, column=3).value = report.status.capitalize()
                row_num += 1

        workbook.save(response)
        return response

    except Exception as e:
        print(f"Error in download_attendance: {str(e)}")
        return HttpResponse(f"Error: {str(e)}")


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
