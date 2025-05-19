from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404, render
from ams_app.models import Attendance, AttendanceReport, CustomUser, Subjects, Students, SessionYearModel, SubjectSchedule, Courses
from django.contrib.auth.decorators import login_required
import json
import pandas as pd
from datetime import timedelta
from django.http import JsonResponse, HttpResponse
from django.utils.dateparse import parse_date

@login_required
def student_home(request):
    student_obj = Students.objects.get(admin=request.user.id)

    attendance_reports = AttendanceReport.objects.filter(
        student=student_obj,
        attendance__session_year_id=student_obj.session_year_id
    )

    attendance_total = attendance_reports.count()
    attendance_present = attendance_reports.filter(status=True).count()
    attendance_absent = attendance_reports.filter(status=False).count()

    course = student_obj.course_id
    subject_data = Subjects.objects.filter(course=course)
    subjects_count = subject_data.count()

    subject_names = []
    data_present = []
    data_absent = []

    for subject in subject_data:
        attendance_records = Attendance.objects.filter(
            subject_id=subject.id,
            session_year_id=student_obj.session_year_id
        )

        present_count = AttendanceReport.objects.filter(
            attendance__in=attendance_records,
            status=True,
            student=student_obj
        ).count()

        absent_count = AttendanceReport.objects.filter(
            attendance__in=attendance_records,
            status=False,
            student=student_obj
        ).count()

        subject_names.append(subject.subject_name)
        data_present.append(present_count)
        data_absent.append(absent_count)

    context = {
        "total_attendance": attendance_total,
        "attendance_absent": attendance_absent,
        "attendance_present": attendance_present,
        "subjects": subjects_count,
        "data_name": subject_names,  
        "data1": data_present,  
        "data2": data_absent   
    }

    return render(request, "student_template/student_home_template.html", context)
@login_required
def student_view_attendance(request):
    student = Students.objects.get(admin=request.user)
    subjects = student.subjects.all()

    schedules = SubjectSchedule.objects.filter(subject__in=subjects)

    session_years = SessionYearModel.objects.all()

    context = {
        'subjects': subjects,
        'schedules': schedules,
        'session_years': session_years
    }
    return render(request, "student_template/student_view_attendance.html", context)

@csrf_exempt
@login_required
def student_get_attendance(request):
    try:
        data = json.loads(request.body)
        student = Students.objects.get(admin=request.user)

        subject_id = data.get("subject")
        session_year_id = data.get("session_year")
        schedule_id = data.get("schedule")
        start_date = parse_date(data.get("start_date"))
        end_date = parse_date(data.get("end_date"))
        get_all_schedules = data.get("get_all_schedules", False)

        if get_all_schedules and subject_id:
            schedule_objs = SubjectSchedule.objects.filter(subject_id=subject_id)
        elif schedule_id:
            schedule_objs = SubjectSchedule.objects.filter(id=schedule_id)
        else:
            schedule_objs = []

        attendance_filters = {
            "session_year_id": session_year_id,
            "attendance_date__range": (start_date, end_date),
            "subject_id": subject_id
        }

        if schedule_objs:
            attendance_filters["schedule_id__in"] = [s.id for s in schedule_objs]

        attendance_list = Attendance.objects.filter(**attendance_filters)
        reports = AttendanceReport.objects.filter(attendance__in=attendance_list, student=student).select_related(
            "attendance__subject", "attendance__schedule"
        )

        report_map = {
            (report.attendance.attendance_date, report.attendance.schedule_id): report
            for report in reports
        }

        response_data = []
        current_date = start_date
        while current_date <= end_date:
            weekday_str = current_date.strftime("%A")

            for schedule in schedule_objs:
                if schedule.day_of_week != weekday_str:
                    continue

                report = report_map.get((current_date, schedule.id))
                status = report.status if report else "Absent"
                subject_name = report.attendance.subject.subject_name if report else Subjects.objects.get(id=subject_id).subject_name

                response_data.append({
                    "date": str(current_date),
                    "schedule": f"{schedule.day_of_week} ({schedule.start_time} - {schedule.end_time})",
                    "status": status,
                    "subject_name": subject_name
                })
            current_date += timedelta(days=1)

        return JsonResponse(response_data, safe=False)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

@csrf_exempt
@login_required
def student_download_attendance(request):
    try:
        data = json.loads(request.body)
        student = Students.objects.get(admin=request.user)

        subject_id = data.get("subject")
        session_year_id = data.get("session_year")
        schedule_id = data.get("schedule")
        start_date = parse_date(data.get("start_date"))
        end_date = parse_date(data.get("end_date"))
        get_all_schedules = data.get("get_all_schedules", False)

        if get_all_schedules and subject_id:
            schedule_objs = SubjectSchedule.objects.filter(subject_id=subject_id)
        elif schedule_id:
            schedule_objs = SubjectSchedule.objects.filter(id=schedule_id)
        else:
            schedule_objs = []

        data_list = []
        current_date = start_date

        while current_date <= end_date:
            weekday_str = current_date.strftime("%A")

            for schedule in schedule_objs:
                if schedule.day_of_week != weekday_str:
                    continue

                attendance = Attendance.objects.filter(
                    subject_id=subject_id,
                    session_year_id=session_year_id,
                    schedule_id=schedule.id,
                    attendance_date=current_date
                ).first()

                found = False
                if attendance:
                    report = AttendanceReport.objects.filter(attendance=attendance, student=student).first()
                    if report:
                        data_list.append([
                            str(current_date),
                            f"{schedule.day_of_week} ({schedule.start_time} - {schedule.end_time})",
                            report.status,
                            attendance.subject.subject_name
                        ])
                        found = True

                if not found:
                    subject_name = Subjects.objects.get(id=subject_id).subject_name
                    data_list.append([
                        str(current_date),
                        f"{schedule.day_of_week} ({schedule.start_time} - {schedule.end_time})",
                        "Absent",
                        subject_name
                    ])

            current_date += timedelta(days=1)

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
