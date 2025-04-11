from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404, render
from ams_app.models import Attendance, AttendanceReport, CustomUser, Subjects, Students, SessionYearModel, SubjectSchedule, Courses
from django.contrib.auth.decorators import login_required
import json
import pandas as pd
from django.http import JsonResponse, HttpResponse

@login_required
def student_home(request):
    student_obj = Students.objects.get(admin=request.user.id)

    # Compute attendance stats
    attendance_total = AttendanceReport.objects.filter(student=student_obj).count()
    attendance_present = AttendanceReport.objects.filter(student=student_obj, status=True).count()
    attendance_absent = AttendanceReport.objects.filter(student=student_obj, status=False).count()

    # Get student's course and subjects
    course = student_obj.course_id
    subjects = Subjects.objects.filter(course=course).count()

    # Prepare data for attendance chart
    subject_names = []
    data_present = []
    data_absent = []

    subject_data = Subjects.objects.filter(course=course)
    for subject in subject_data:
        attendance_records = Attendance.objects.filter(subject_id=subject.id)
        present_count = AttendanceReport.objects.filter(attendance__in=attendance_records, status=True, student=student_obj).count()
        absent_count = AttendanceReport.objects.filter(attendance__in=attendance_records, status=False, student=student_obj).count()

        subject_names.append(subject.subject_name)
        data_present.append(present_count)
        data_absent.append(absent_count)

    context = {
        "total_attendance": attendance_total,
        "attendance_absent": attendance_absent,
        "attendance_present": attendance_present,
        "subjects": subjects,
        "data_name": subject_names,  # List of subject names for chart
        "data1": data_present,  # List of present counts per subject
        "data2": data_absent  # List of absent counts per subject
    }

    return render(request, "student_template/student_home_template.html", context)
@login_required
def student_view_attendance(request):
    student = Students.objects.get(admin=request.user)
    subjects = student.subjects.all()  # Assuming may M2M or related field ka dito
    session_years = SessionYearModel.objects.all()

    context = {
        'subjects': subjects,
        'session_years': session_years
    }
    return render(request, "student_template/student_view_attendance.html", context)
@csrf_exempt
@login_required
def student_get_attendance(request):
    try:
        data = json.loads(request.body)
        student = Students.objects.get(admin=request.user)

        start_date = data.get("start_date")
        end_date = data.get("end_date")
        subject_id = data.get("subject")
        session_year_id = data.get("session_year")

        filters = {
            "student": student,
            "attendance__attendance_date__range": (start_date, end_date),
            "attendance__session_year_id": session_year_id
        }

        if subject_id:
            filters["attendance__subject_id"] = subject_id

        attendance_reports = AttendanceReport.objects.filter(**filters).select_related(
            'attendance__subject', 'attendance__schedule'
        )

        response_data = []
        for report in attendance_reports:
            attendance = report.attendance
            response_data.append({
                "date": str(attendance.attendance_date),
                "schedule": f"{attendance.schedule.day_of_week} ({attendance.schedule.start_time} - {attendance.schedule.end_time})",
                "status": report.status,
                "subject_name": attendance.subject.subject_name
            })

        return JsonResponse(response_data, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

@csrf_exempt
@login_required
def student_download_attendance(request):
    try:
        data = json.loads(request.body)
        student = Students.objects.get(admin=request.user)

        start_date = data.get("start_date")
        end_date = data.get("end_date")

        attendance_reports = AttendanceReport.objects.filter(
            student=student,
            attendance__attendance_date__range=(start_date, end_date)
        ).select_related('attendance__subject', 'attendance__schedule')

        data_list = []
        for report in attendance_reports:
            attendance = report.attendance
            data_list.append([
                str(attendance.attendance_date),
                f"{attendance.schedule.day_of_week} ({attendance.schedule.start_time} - {attendance.schedule.end_time})",
                report.status,
                attendance.subject.subject_name
            ])

        df = pd.DataFrame(data_list, columns=["Date", "Schedule", "Status", "Subject"])

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="my_attendance.xlsx"'
        df.to_excel(response, index=False)

        return response
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

def student_profile(request):
    user=CustomUser.objects.get(id=request.user.id)
    student=Students.objects.get(admin=user)
    return render(request,"student_template/student_profile.html",{"user":user,"student":student})

def student_profile_save(request):
    if request.method!="POST":
        return HttpResponseRedirect(reverse("student_profile"))
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

            student=Students.objects.get(admin=customuser)
            student.save()
            messages.success(request, "Successfully Updated Profile")
            return HttpResponseRedirect(reverse("student_profile"))
        except:
            messages.error(request, "Failed to Update Profile")
            return HttpResponseRedirect(reverse("student_profile"))

@login_required
def student_my_subjects(request):
    student = Students.objects.get(admin=request.user)

    subjects = student.subjects.all()

    context = {
        'subjects': subjects
    }

    return render(request, "student_template/student_my_subjects.html", context)
