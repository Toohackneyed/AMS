from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404, render
from ams_app.models import Attendance, AttendanceReport, CustomUser, Subjects, Students, SessionYearModel, SubjectSchedule, Courses
from django.contrib.auth.decorators import login_required


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
    subjects = Subjects.objects.filter(course=student.course_id)  # Hanapin ang subjects ng student
    session_years = SessionYearModel.objects.all()  # Kunin lahat ng session years
    schedules = SubjectSchedule.objects.filter(subject__in=subjects)  # Hanapin ang schedules ng subject na enrolled ang student

    context = {
        "subjects": subjects,
        "session_years": session_years,
        "schedules": schedules 
    }
    
    return render(request, 'student_template/student_view_attendance.html', context)

@csrf_exempt  # Temporary disable CSRF (for testing purposes)
def get_attendance_data(request):
    if request.method == "POST":
        try:
            subject_id = request.POST.get("subject")
            session_year_id = request.POST.get("session_year")
            schedule_id = request.POST.get("schedule")
            attendance_scope = request.POST.get("attendance_scope")
            start_date = request.POST.get("start_date")
            end_date = request.POST.get("end_date")

            # Filter attendance based on scope (all weeks or specific week)
            if attendance_scope == "specific" and start_date and end_date:
                attendance_records = Attendance.objects.filter(
                    subject_id=subject_id,
                    session_year_id=session_year_id,
                    schedule_id=schedule_id,
                    attendance_date__range=[start_date, end_date]
                )
            else:
                attendance_records = Attendance.objects.filter(
                    subject_id=subject_id,
                    session_year_id=session_year_id,
                    schedule_id=schedule_id
                )

            data = []

            for attendance in attendance_records:
                reports = AttendanceReport.objects.filter(attendance_id=attendance.id)
                for report in reports:
                    data.append({
                        "student_name": report.student.admin.first_name + " " + report.student.admin.last_name,
                        "attendance_date": attendance.attendance_date.strftime("%Y-%m-%d"),
                        "status": "Present" if report.status else "Absent"
                    })

            return JsonResponse(data, safe=False)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid Request"}, status=400)

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
