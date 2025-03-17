
from datetime import date
import cv2
import pandas as pd
import face_recognition
import numpy as np
from django.http import JsonResponse
from .models import Students, Attendance, AttendanceReport
from django.utils import timezone
from datetime import datetime
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.db import IntegrityError
from django.core.files.storage import FileSystemStorage
from ams_app.forms import AddStudentForm , EditStudentForm
import logging
from django.core.files.base import ContentFile
import json
from django.utils.timezone import now, localtime, make_aware
import base64
import io
from django.db import transaction   
import threading
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.cache import cache
import serial
from datetime import datetime, timedelta
from django.utils.timezone import now
import serial
import time
import serial.tools.list_ports
import re

#rfid reader


from ams_app.models import CustomUser, SessionTimeModel, Staffs, Courses, Subjects,Sections, Students, SessionYearModel, SubjectSchedule, Attendance, AttendanceReport, Enrollment

@login_required
def admin_home(request):
    # Get total counts
    student_count = Students.objects.count()
    staff_count = Staffs.objects.count()
    subject_count = Subjects.objects.count()
    course_count = Courses.objects.count()

    # Data for courses
    course_name_list = []
    subject_count_list = []
    student_count_list_in_course = []

    for course in Courses.objects.all():
        subjects = Subjects.objects.filter(course=course).count()
        students = Students.objects.filter(course_id=course).count()
        course_name_list.append(course.course_name)
        subject_count_list.append(subjects)
        student_count_list_in_course.append(students)

    # Data for subjects
    subject_list = []
    student_count_list_in_subject = []

    for subject in Subjects.objects.all():
        student_count = Students.objects.count()
        subject_list.append(subject.subject_name)
        student_count_list_in_subject.append(student_count)

    # Debugging: I-check kung tama ang bilang ng students per subject
    print("Subject count list:", student_count_list_in_subject)

    # Prepare dashboard boxes
    dashboard_boxes = [
        {"value": student_count, "label": "Total Students", "color": "bg-info", "icon": "ion ion-pie-graph", "url": "manage_student"},
        {"value": staff_count, "label": "Total Staffs", "color": "bg-success", "icon": "ion ion-pie-graph", "url": "manage_staff"},
        {"value": course_count, "label": "Total Courses", "color": "bg-warning", "icon": "ion ion-pie-graph", "url": "manage_course"},
        {"value": subject_count, "label": "Total Subjects", "color": "bg-danger", "icon": "ion ion-pie-graph", "url": "manage_subject"},
    ]

    context = {
        "dashboard_boxes": dashboard_boxes,
        "student_count": student_count or 0,
        "staff_count": staff_count or 0,
        "subject_count": subject_count,
        "course_count": course_count,
        "course_name_list": course_name_list,
        "subject_count_list": subject_count_list,
        "student_count_list_in_course": student_count_list_in_course,
        "student_count_list_in_subject": student_count_list_in_subject,
        "subject_list": subject_list,
    }
    print("🟢 DEBUG: Total Students Before Processing =", student_count)

    return render(request, "admin_template/home_content.html", context)

def add_staff(request):
    return render(request,"admin_template/add_staff_template.html")

def add_staff_save(request):
    if request.method != "POST":
        return HttpResponse("Method Not Allowed")
    else:
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")

        # Check if email or username already exists
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email already in use. Please use another.")
            return HttpResponseRedirect(reverse("add_staff"))

        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already taken. Please choose another.")
            return HttpResponseRedirect(reverse("add_staff"))

        try:
            user = CustomUser.objects.create_user(
                username=username,
                password=password,
                email=email,
                last_name=last_name,
                first_name=first_name,
                user_type=2
            )
            user.save()
            messages.success(request, "Successfully Added Staff")
            return HttpResponseRedirect(reverse("add_staff"))
        except Exception as e:
            messages.error(request, f"Failed to Add Staff: {str(e)}")
            return HttpResponseRedirect(reverse("add_staff"))
        
def add_course(request):
    return render(request,"admin_template/add_course_template.html")

def add_course_save(request):
    if request.method!="POST":
        return HttpResponse("Method Not Allowed")
    else:
        course=request.POST.get("course")
        try:
            course_model=Courses(course_name=course)
            course_model.save()
            messages.success(request,"Successfully Added Course")
            return HttpResponseRedirect(reverse("add_course"))
        except :
            messages.error(request,"Failed To Add Course")
            return HttpResponseRedirect(reverse("add_course"))
        
def add_section(request):
    return render(request,"admin_template/add_section_template.html")

def add_section_save(request):
    if request.method!="POST":
        return HttpResponse("Method Not Allowed")
    else:
        section=request.POST.get("section")
        try:
            section_model=Sections(section_name=section)
            section_model.save()
            messages.success(request,"Successfully Added Section")
            return HttpResponseRedirect(reverse("add_section"))
        except :
            messages.error(request,"Failed To Add Section")
            return HttpResponseRedirect(reverse("add_section"))

def get_subjects_by_course(request):
    course_ids = request.GET.get("courses")
    if not course_ids:
        return JsonResponse({"subjects": []})  # Walang course na pinili
    
    course_ids = course_ids.split(",")  # Convert CSV string to list
    subjects = Subjects.objects.filter(course__id__in=course_ids).values("id", "subject_name")

    return JsonResponse({"subjects": list(subjects)})

def add_student(request):
    form = AddStudentForm()
    return render(request, "admin_template/add_student_template.html", {"form": form})

def add_student_save(request):
    if request.method != "POST":
        return HttpResponse("Method Not Allowed")
    else:
        form = AddStudentForm(request.POST, request.FILES)
        if form.is_valid():
            first_name = form.cleaned_data["first_name"]
            last_name = form.cleaned_data["last_name"]
            username = form.cleaned_data["username"]
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            rfid = form.cleaned_data["rfid"]
            id_number = form.cleaned_data["id_number"]
            section_id = request.POST.get("section")
            session_year_id = int(form.cleaned_data["session_year_id"])
            course_id = form.cleaned_data["course"]
            gender = form.cleaned_data["gender"]
            profile_pic = request.FILES.get("profile_pic")

            try:
                # Create user
                user = CustomUser.objects.create_user(
                    username=username,
                    password=password,
                    email=email,
                    last_name=last_name,
                    first_name=first_name,
                    user_type=3
                )

                # Assign student details
                user.students.rfid = rfid
                user.students.id_number = id_number
                user.students.course_id = Courses.objects.get(id=course_id)
                user.students.session_year_id = SessionYearModel.objects.get(id=session_year_id)
                user.students.gender = gender
                user.students.section = Sections.objects.get(id=section_id)

                # ✅ Extract face encoding from profile picture
                if profile_pic:
                    user.students.profile_pic = profile_pic
                    image_data = np.frombuffer(profile_pic.read(), np.uint8)
                    img = cv2.imdecode(image_data, cv2.IMREAD_COLOR)

                    # Convert to RGB
                    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

                    # Detect face and extract encoding
                    face_locations = face_recognition.face_locations(rgb_img, model='cnn')
                    face_encodings = face_recognition.face_encodings(rgb_img, face_locations)

                    if face_encodings:
                        user.students.face_encoding = json.dumps(face_encodings[0].tolist())  # ✅ Save encoding as JSON

                # ✅ Save student data first
                user.students.save()

                # ✅ Handle Subject Enrollment
                selected_subjects = request.POST.getlist("subjects")
                if not selected_subjects:
                    messages.error(request, "Please select at least one subject.")
                    return HttpResponseRedirect(reverse("add_student"))

                Enrollment.objects.filter(student=user.students).delete()

                for subject_id in selected_subjects:
                    subject = Subjects.objects.get(id=subject_id)
                    Enrollment.objects.create(student=user.students, subject=subject)

                messages.success(request, "Successfully Added Student")
                return HttpResponseRedirect(reverse("add_student"))

            except Exception as e:
                messages.error(request, f"Failed to Add Student: {str(e)}")
                return HttpResponseRedirect(reverse("add_student"))
        else:
            return render(request, "admin_template/add_student_template.html", {"form": form})

def add_subject(request):
    courses=Courses.objects.all()
    staffs=Staffs.objects.all()
    schedule = SubjectSchedule.objects.all()

    return render(request,"admin_template/add_subject_template.html",{"staffs":staffs,"courses":courses, "schedule":schedule})

def add_subject_save(request):
    if request.method == "POST":
        subject_code = request.POST.get("subject_code")
        subject_name = request.POST.get("subject_name")
        course_id = request.POST.get("course")  
        staff_id = request.POST.get("staff")  
        days = request.POST.getlist("day_of_week[]")  
        start_times = request.POST.getlist("start_time[]")  
        end_times = request.POST.getlist("end_time[]")  

        try:
            course = Courses.objects.get(id=course_id)
            staff = Staffs.objects.get(id=staff_id)

            subject = Subjects.objects.create(
                subject_code=subject_code,
                subject_name=subject_name,
                course=course,
                staff=staff,
            )

            for i in range(len(days)):
                if start_times[i] >= end_times[i]:
                    raise ValidationError("Start time must be before end time.")

                SubjectSchedule.objects.create(
                    subject=subject,
                    day_of_week=days[i],
                    start_time=start_times[i],
                    end_time=end_times[i],
                )

            messages.success(request, "Subject added successfully!")
            return redirect("add_subject")

        except Courses.DoesNotExist:
            messages.error(request, "The selected course does not exist.")
        except Staffs.DoesNotExist:
            messages.error(request, "The selected staff does not exist.")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

        return redirect("add_subject")

    
def manage_staff(request):
    staffs = Staffs.objects.all()  # Fetch staff records
    return render(request, "admin_template/manage_staff_template.html", {"staffs": staffs})  # Pass staff records to the template
def manage_student(request):
    selected_subjects = request.GET.getlist("subjects")  # Kunin ang mga piniling subjects
    students = Students.objects.select_related("admin", "course_id", "session_year_id") \
                               .prefetch_related("enrollment_set__subject").all()

    if selected_subjects:
        students = students.filter(enrollment_set__subject__id__in=selected_subjects).distinct()

    # Debugging: Print enrolled subjects after filtering
    for student in students:
        print(f"Student: {student.admin.first_name} {student.admin.last_name}")
        for enrollment in student.enrollment_set.all():
            print(f"  Subject: {enrollment.subject.subject_name}")

    return render(request, "admin_template/manage_student_template.html", {"students": students})

def manage_course(request):
    courses = Courses.objects.all()
    return render(request, "admin_template/manage_course_template.html", {"courses": courses})

def manage_section(request):
    sections = Sections.objects.all()
    return render(request, "admin_template/manage_section_template.html", {"sections": sections})

def manage_subject(request):
    subjects = Subjects.objects.all()  # Fetch staff records
    return render(request, "admin_template/manage_subject_template.html", {"subjects": subjects})  # Pass staff records to the template

def edit_staff(request,staff_id):
    staff=Staffs.objects.get(admin=staff_id)
    return render(request,"admin_template/edit_staff_template.html",{"staff":staff,"id":staff_id})

def edit_staff_save(request):
    if request.method!="POST":
        return HttpResponse("<h2>Method Not Allowed</h2>")
    else:
        staff_id=request.POST.get("staff_id")
        first_name=request.POST.get("first_name")
        last_name=request.POST.get("last_name")
        email=request.POST.get("email")
        username=request.POST.get("username")
        rfid=request.POST.get("rfid")

        try:
            user=CustomUser.objects.get(id=staff_id)
            user.first_name=first_name
            user.last_name=last_name
            user.email=email
            user.username=username
            user.save()

            staff_model=Staffs.objects.get(admin=staff_id)
            staff_model.rfid=rfid
            staff_model.save()
            messages.success(request,"Successfully Edited Staff")
            return HttpResponseRedirect(reverse("edit_staff",kwargs={"staff_id":staff_id}))
        except:
            messages.error(request,"Failed to Edit Staff")
            return HttpResponseRedirect(reverse("edit_staff",kwargs={"staff_id":staff_id}))

def edit_student(request, student_id):
    student = Students.objects.get(admin=student_id)

    selected_courses_ids = list(student.selected_courses.values_list("id", flat=True))
    enrolled_subjects = list(Enrollment.objects.filter(student=student).values("subject__id", "subject__subject_name"))

    form = EditStudentForm(initial={
        "email": student.admin.email,
        "first_name": student.admin.first_name,
        "last_name": student.admin.last_name,
        "username": student.admin.username,
        "id_number": student.id_number,
        "rfid": student.rfid,
        "gender": student.gender,
        "course": student.course_id.id if student.course_id else None,
        "section": student.section,  # ✅ Plain text field lang
    })
    form.fields['course'].choices = [(c.id, c.course_name) for c in Courses.objects.all()]

    context = {
        "form": form,
        "student": student,
        "all_courses": Courses.objects.all(),
        "sections": Sections.objects.all(), 
        "selected_courses_ids": selected_courses_ids,
        "enrolled_subjects": enrolled_subjects,  
    }
    return render(request, "admin_template/edit_student_template.html", context)

def edit_student_save(request):
    if request.method != "POST":
        messages.error(request, "Invalid Request")
        return redirect("manage_student")

    student_id = request.POST.get("student_id")
    main_course_id = request.POST.get("course_id")
    selected_course_ids = request.POST.getlist("selected_courses")
    subject_ids = request.POST.getlist("subjects")
    section = request.POST.get("section")  # ✅ GET SECTION AS TEXT

    # Kunin ang ibang fields mula sa POST request
    email = request.POST.get("email")
    first_name = request.POST.get("first_name")
    last_name = request.POST.get("last_name")
    username = request.POST.get("username")
    id_number = request.POST.get("id_number")
    rfid = request.POST.get("rfid")
    gender = request.POST.get("gender")
    section_id = request.POST.get("section")

    try:
        with transaction.atomic():
            student = get_object_or_404(Students, admin=student_id)
            
            # Update student details
            student.admin.email = email
            student.admin.first_name = first_name
            student.admin.last_name = last_name
            student.admin.username = username
            student.id_number = id_number
            student.rfid = rfid
            student.gender = gender
            student.admin.save()  # Save admin fields
            student.save()  # Save student fields

            # Update courses
            student.course = Courses.objects.get(id=main_course_id) if main_course_id else None
            student.selected_courses.set(Courses.objects.filter(id__in=selected_course_ids))

            # ✅ Save section as plain text
            student.section = get_object_or_404(Sections, id=section_id)
            student.save()

            # Update subjects
            current_subjects = set(Enrollment.objects.filter(student=student).values_list("subject_id", flat=True))
            new_subjects = set(map(int, subject_ids))

            Enrollment.objects.bulk_create(
                [Enrollment(student=student, subject_id=subj_id) for subj_id in new_subjects - current_subjects]
            )
            Enrollment.objects.filter(student=student, subject_id__in=current_subjects - new_subjects).delete()

        messages.success(request, "Student updated successfully")
        return redirect("manage_student")

    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect("edit_student", student_id=student_id)

def edit_subject(request, subject_id):
    subject = Subjects.objects.prefetch_related("schedules").get(id=subject_id)
    courses = Courses.objects.all()
    staffs = Staffs.objects.all()

    return render(request, "admin_template/edit_subject_template.html", {
        "subject": subject,
        "courses": courses,
        "staffs": staffs
    })

def edit_subject_save(request):
    if request.method == "POST":
        subject_id = request.POST.get("subject_id")
        subject_code = request.POST.get("subject_code")
        subject_name = request.POST.get("subject_name")
        course_id = request.POST.get("course")
        staff_id = request.POST.get("staff")
        days = request.POST.getlist("day_of_week[]")
        start_times = request.POST.getlist("start_time[]")
        end_times = request.POST.getlist("end_time[]")
        schedule_ids = request.POST.getlist("schedule_ids[]")  # Existing schedules

        try:
            subject = Subjects.objects.get(id=subject_id)
            course = Courses.objects.get(id=course_id)
            staff = Staffs.objects.get(id=staff_id)

            # Update subject details
            subject.subject_code = subject_code
            subject.subject_name = subject_name
            subject.course = course
            subject.staff = staff
            subject.save()

            # Get existing schedules
            existing_schedule_ids = set(subject.schedules.values_list('id', flat=True))
            submitted_schedule_ids = set(map(int, schedule_ids)) if schedule_ids else set()

            # Delete schedules that are removed
            schedules_to_delete = existing_schedule_ids - submitted_schedule_ids
            SubjectSchedule.objects.filter(id__in=schedules_to_delete).delete()

            # Update or Create schedules
            for i in range(len(days)):
                if start_times[i] >= end_times[i]:
                    raise ValidationError("Start time must be before end time.")

                if i < len(schedule_ids) and schedule_ids[i]:
                    schedule, created = SubjectSchedule.objects.get_or_create(
                        id=schedule_ids[i],
                        defaults={
                            "subject": subject,
                            "day_of_week": days[i],
                            "start_time": start_times[i],
                            "end_time": end_times[i],
                        }
                    )
                    if not created:
                        schedule.day_of_week = days[i]
                        schedule.start_time = start_times[i]
                        schedule.end_time = end_times[i]
                        schedule.save()
                else:
                    SubjectSchedule.objects.create(
                        subject=subject,
                        day_of_week=days[i],
                        start_time=start_times[i],
                        end_time=end_times[i],
                    )

            messages.success(request, "Subject updated successfully!")
            return redirect("manage_subject")

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect("edit_subject", subject_id=subject_id)


def edit_course(request, course_id):
    course = Courses.objects.get(id=course_id)
    return render(request, "admin_template/edit_course_template.html", {"course": course, "id": course_id})


def edit_course_save(request):
    if request.method != "POST":
        return HttpResponse("<h2>Method Not Allowed</h2>")

    course_id = request.POST.get("course_id")
    course_name = request.POST.get("course")

    try:
        course = get_object_or_404(Courses, id=course_id)
        course.course_name = course_name
        course.save()
        messages.success(request, "Successfully Edited Course")
        return HttpResponseRedirect(reverse("edit_course", kwargs={"course_id": course_id}))
    except:
        messages.error(request, "Failed to Edit Course")
        return HttpResponseRedirect(reverse("edit_course", kwargs={"course_id": course_id}))
    
def edit_section(request, section_id):
    """ Load the edit section page with existing section details """
    section = get_object_or_404(Sections, id=section_id)
    return render(request, "admin_template/edit_section_template.html", {"section": section, "id": section_id})


def edit_section_save(request):
    """ Save edited section details """
    if request.method != "POST":
        return HttpResponse("<h2>Method Not Allowed</h2>")

    section_id = request.POST.get("section_id")
    section_name = request.POST.get("section")

    if not section_name.strip():  # ✅ Prevent saving empty names
        messages.error(request, "Section name cannot be empty.")
        return HttpResponseRedirect(reverse("edit_section", kwargs={"section_id": section_id}))

    try:
        section = get_object_or_404(Sections, id=section_id)
        section.section_name = section_name
        section.save()
        messages.success(request, "Successfully Edited Section")
    except Exception as e:
        messages.error(request, f"Failed to Edit Section: {str(e)}")

    return HttpResponseRedirect(reverse("edit_section", kwargs={"section_id": section_id}))
def manage_session(request):
    # Kunin ang pinakabagong session year mula sa database (kung meron)
    latest_session = SessionYearModel.objects.order_by('-id').first()  # Kukunin ang pinaka-latest na session

    # I-pass ang session data sa template
    return render(request, "admin_template/manage_session_template.html", {"sessions": SessionYearModel.objects.all(), "latest_session": latest_session})

def add_session_save(request):
    if request.method!="POST":
        return HttpResponseRedirect(reverse("manage_session"))
    else:
        session_start_date=request.POST.get("session_start_date")
        session_end_date=request.POST.get("session_end_date")

        try:
            sessionyear=SessionYearModel(session_start_date=session_start_date,session_end_date=session_end_date)
            sessionyear.save()
            messages.success(request, "Successfully Added Session")
            return HttpResponseRedirect(reverse("manage_session"))
        except:
            messages.error(request, "Failed to Add Session")
            return HttpResponseRedirect(reverse("manage_session"))

def admin_view_attendance(request):
    """ Display attendance filtering options """
    subjects = Subjects.objects.all()
    schedules = SubjectSchedule.objects.all()
    session_years = SessionYearModel.objects.all()
    sections = Sections.objects.all()  # Kunin ang lahat ng sections

    context = {
        'subjects': subjects,
        'schedules': schedules,
        'session_years': session_years,
        'sections': sections  # Ipadala sa template
    }
    
    return render(request, "admin_template/admin_view_attendance.html", context)

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
def get_attendance(request):
    """ Fetch attendance records based on selected filters """
    if request.method == 'POST':
        subject_id = request.POST.get('subject')
        session_year_id = request.POST.get('session_year')
        schedule_id = request.POST.get('schedule')
        section_id = request.POST.get('section')  # Kunin ang section
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        # I-filter ang attendance gamit ang section
        attendance_records = Attendance.objects.filter(
            subject_id=subject_id,
            session_year_id=session_year_id,
            schedule_id=schedule_id,
            students__section_id=section_id,  # Isama ang filter sa section
            attendance_date__range=(start_date, end_date)
        )

        attendance_data = []
        for attendance in attendance_records:
            reports = AttendanceReport.objects.filter(attendance=attendance)
            for report in reports:
                attendance_data.append({
                    "student_name": report.student.admin.get_full_name(),
                    "date": attendance.attendance_date.strftime("%Y-%m-%d"),
                    "status": report.status
                })

        return JsonResponse(attendance_data, safe=False)

    return JsonResponse({'error': 'Invalid request'}, status=400)

def download_attendance(request):
    """ Export attendance records as Excel file """
    
    subject_id = request.GET.get("subject")
    session_year_id = request.GET.get("session_year")
    schedule_id = request.GET.get("schedule")
    section_id = request.GET.get("section")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    # Kunin ang attendance records
    attendance_records = Attendance.objects.filter(
        subject_id=subject_id,
        session_year_id=session_year_id,
        schedule_id=schedule_id,
        students__section_id=section_id,
        attendance_date__range=(start_date, end_date)
    )

    # I-prepare ang data
    data = []
    for attendance in attendance_records:
        reports = AttendanceReport.objects.filter(attendance=attendance)
        for report in reports:
            data.append([
                report.student.admin.get_full_name(),
                report.student.id_number,
                attendance.attendance_date.strftime("%Y-%m-%d"),
                report.status
            ])

    # Gawing DataFrame
    df = pd.DataFrame(data, columns=["Student Name", "ID Number", "Date", "Status"])

    # Gumawa ng Excel file
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = "attachment; filename=attendance.xlsx"
    
    with pd.ExcelWriter(response, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Attendance", index=False)

    return response

def admin_profile(request):
    user=CustomUser.objects.get(id=request.user.id)
    return render(request,"admin_template/admin_profile.html",{"user":user})

def admin_profile_save(request):
    if request.method!="POST":
        return HttpResponseRedirect(reverse("admin_profile"))
    else:
        first_name=request.POST.get("first_name")
        last_name=request.POST.get("last_name")
        password=request.POST.get("password")
        try:
            customuser=CustomUser.objects.get(id=request.user.id)
            customuser.first_name=first_name
            customuser.last_name=last_name
            # if password!=None and password!="":
            #     customuser.set_password(password)
            customuser.save()
            messages.success(request, "Successfully Updated Profile")
            return HttpResponseRedirect(reverse("admin_profile"))
        except:
            messages.error(request, "Failed to Update Profile")
            return HttpResponseRedirect(reverse("admin_profile"))

def delete_course(request, course_id):
    course = get_object_or_404(Courses, id=course_id)
    course.delete()
    messages.success(request, "Course successfully deleted.")
    return redirect('manage_course') 

def delete_section(request, section_id):
    section = get_object_or_404(Sections, id=section_id)
    section.delete()
    messages.success(request, "Section successfully deleted.")
    return redirect('manage_section') 

def delete_session(request, session_id):
    session = get_object_or_404(SessionYearModel, id=session_id)
    session.delete()
    messages.success(request, "Session year successfully deleted.")
    return redirect('manage_session')

# Edit session year
def edit_session(request, session_id):
    session = get_object_or_404(SessionYearModel, id=session_id)
    
    if request.method == 'POST':
        # Kunin ang mga values mula sa form
        session_start_date = request.POST.get('session_start_date')
        session_end_date = request.POST.get('session_end_date')

        # Update ang session year
        session.session_start_date = session_start_date
        session.session_end_date = session_end_date
        session.save()

        messages.success(request, "Session year successfully updated.")
        return redirect('manage_session')  # Palitan ito ng URL name ng iyong page

    return render(request, 'admin_template/edit_session.html', {'session': session})

def delete_staff(request, staff_id):
    staff = get_object_or_404(Staffs, admin__id=staff_id)
    staff.delete()
    messages.success(request, "Staff successfully deleted.")
    return redirect('manage_staff')

def delete_subject(request, subject_id):
    subject = get_object_or_404(Subjects, id=subject_id)
    subject.delete()
    messages.success(request, "Subject successfully deleted.")
    return redirect('manage_subject')

def delete_student(request, student_id):
    student = get_object_or_404(CustomUser, id=student_id)
    student.delete()
    return redirect('manage_student') # Adjust the redirect to the correct name for your student management view

def face_recognition_attendance(request):
    """Render the Face Recognition Attendance page."""
    return render(request, "admin_template/face_recognition_attendance.html")

#Face Recognition----------------------------------------------------------------------------------------------------------------------------------------

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

        if enrollment:
            session_year = enrollment.student.session_year_id
        else:
            return JsonResponse({"error": "No session year found"}, status=400)

        image_data = np.frombuffer(image.read(), np.uint8)
        img = cv2.imdecode(image_data, cv2.IMREAD_COLOR)

        if img is None:
            return JsonResponse({"error": "Invalid image format"}, status=400)

        img = cv2.resize(img, (320, 240))
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_img, model='hog')
        face_encodings = face_recognition.face_encodings(rgb_img, face_locations)

        if not face_encodings:
            return JsonResponse({"error": "No face detected"}, status=400)

        students = Students.objects.exclude(face_encoding=None)
        known_encodings = [np.array(json.loads(student.face_encoding)) for student in students]
        known_names = [student.admin.get_full_name() for student in students]

        for uploaded_encoding in face_encodings:
            matches = face_recognition.compare_faces(known_encodings, uploaded_encoding)
            if True in matches:
                matched_index = matches.index(True)
                matched_student = students[matched_index]
                matched_name = matched_student.admin.get_full_name()
                stored_rfid = matched_student.rfid

                print(f"🔑 DEBUG: Face recognized for {matched_name} with RFID {stored_rfid}")

                # RFID Verification
                try:
                    with open("rfid_tags.txt", "r") as file:
                        tags = file.read().splitlines()

                    if stored_rfid in tags:
                        attendance, _ = Attendance.objects.get_or_create(
                            subject=actual_subject,
                            schedule=subject_schedule,
                            session_year=session_year,
                            attendance_date=date.today()
                        )

                        AttendanceReport.objects.get_or_create(
                            student=matched_student,
                            attendance=attendance,
                            status="present"
                        )

                        print(f"✅ SUCCESS: Attendance marked for {matched_name} ({stored_rfid})")
                        return JsonResponse({
                            "message": f"Attendance recorded for {matched_name}.",
                            "rfid": stored_rfid
                        })
                    else:
                        print(f"❌ ERROR: RFID mismatch for {matched_name}")
                        return JsonResponse({"error": "RFID mismatch"}, status=400)

                except Exception as e:
                    print(f"⚠️ ERROR: RFID verification failed -> {e}")
                    return JsonResponse({"error": "RFID verification failed"}, status=500)

        return JsonResponse({"error": "No matching student found"}, status=404)

    except Exception as e:
        print(f"⚡ ERROR: Exception processing image -> {e}")
        return JsonResponse({"error": "Error processing image"}, status=500)


def get_ongoing_subject(request):   
    """Fetch currently ongoing class. Search for a new class only when the ongoing class ends."""
    current_time = now().time()
    today = now().strftime("%A")  # Ex: "Monday", "Tuesday"

    print(f"\n🔍 DEBUG: Today is {today}, Current Time: {current_time}")

    # 🔍 Fetch all subjects for today
    subjects_today = SubjectSchedule.objects.filter(day_of_week=today).order_by("start_time")
    print(f"✅ DEBUG: Found {subjects_today.count()} subjects for today.")

    # 🔍 Keep the current ongoing subject active
    ongoing_subject = subjects_today.filter(start_time__lte=current_time, end_time__gte=current_time).first()

    if ongoing_subject:
        print(f"✅ DEBUG: Ongoing Subject Found -> {ongoing_subject.subject.subject_name}")
        return JsonResponse({
            "subject_id": ongoing_subject.id,
            "subject_name": ongoing_subject.subject.subject_name,
            "start_time": str(ongoing_subject.start_time),
            "end_time": str(ongoing_subject.end_time),
            "message": "Ongoing class is active"
        })

    # ✅ If no class is ongoing, check if the last class has already ended
    last_class = subjects_today.last()
    if last_class and current_time > last_class.end_time:
        print("✅ DEBUG: All classes for today have ended.")
        return JsonResponse({"message": "All scheduled classes for today have ended."}, status=200)

    # ✅ Search for the next class only after the current one ends
    next_class = subjects_today.filter(start_time__gt=current_time).first()
    if next_class:
        print(f"✅ DEBUG: Next Class Found -> {next_class.subject.subject_name} at {next_class.start_time}")
        return JsonResponse({
            "next_subject_id": next_class.id,
            "next_subject_name": next_class.subject.subject_name,
            "next_start_time": str(next_class.start_time),
            "next_end_time": str(next_class.end_time),
            "message": "Waiting for the next class to start"
        }, status=200)

    print("🚨 ERROR: No ongoing or upcoming class found!")
    return JsonResponse({"error": "No ongoing class at the moment."}, status=404)

#RFID Attendance----------------------------------------------------------------------------------------------------------------------------------------

def find_ch340_port():
    """Find the COM port assigned to USB-SERIAL CH340 (RFID Reader)."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "CH340" in port.description:
            print(f"✅ Found CH340 RFID Reader on {port.device}")
            return port.device
    print("❌ CH340 RFID Reader not found! Please check the connection.")
    return None

def clean_rfid_data(data):
    """Remove unexpected characters and extract the numeric RFID tag."""
    clean_data = re.sub(r'[^\d]', '', data)  # Keep only numbers
    return clean_data

def is_tag_in_file(tag):
    """Check if the tag already exists in the file."""
    try:
        with open("rfid_tags.txt", "r") as file:
            tags = file.read().splitlines()
            return tag in tags
    except FileNotFoundError:
        return False

def read_rfid_tag(port):
    """Read RFID tags from the detected CH340 port and append unique tags to the file."""
    try:
        rfid_reader = serial.Serial(port, 9600, timeout=1)
        print(f"📡 Listening for RFID tags on {port}...")

        while True:
            if rfid_reader.in_waiting > 0:
                raw_data = rfid_reader.readline().decode('utf-8', errors='ignore').strip()
                print(f"🔍 Raw Data: '{raw_data}'")  # Print raw data for debugging

                tag = clean_rfid_data(raw_data)  # Clean the data to extract the RFID tag
                print(f"🧹 Cleaned Data: '{tag}'")  # Print cleaned data

                if tag:
                    if not is_tag_in_file(tag):
                        print(f"🏷️ New Unique Tag Detected: {tag}")

                        # Save the detected tag to the file (append mode)
                        with open("rfid_tags.txt", "a") as file:
                            file.write(f"{tag}\n")
                            file.flush()
                    else:
                        print(f"🔁 Duplicate Tag Skipped: {tag}")

    except serial.SerialException as e:
        print(f"⚠️ Serial Error: {e}")
    except KeyboardInterrupt:
        print("\n🔌 RFID Reader disconnected.")

def scan_for_reader():
    """Keep scanning for the RFID reader every 5 seconds if not found."""
    while True:
        com_port = find_ch340_port()
        if com_port:
            read_rfid_tag(com_port)
        else:
            print("🔄 Rescanning for RFID reader in 5 seconds...")
            time.sleep(5)

# 📝 Django Views
def rfid_attendance(request):
    """Render the RFID Attendance page."""
    return render(request, "admin_template/rfid_attendance_template.html")

def get_rfid_username(request):
    """Fetch the username associated with the latest detected RFID tag."""
    try:
        with open("rfid_tags.txt", "r") as file:
            lines = file.readlines()
            detected_rfid = lines[-1].strip() if lines else "N/A"  # Get the last detected tag

        if detected_rfid and detected_rfid != "N/A":
            # Find the student by RFID tag
            student = Students.objects.filter(rfid=detected_rfid).select_related("admin").first()
            if student:
                return JsonResponse({"username": student.admin.username, "rfid": student.rfid})
            else:
                return JsonResponse({"username": "Unknown", "rfid": detected_rfid})

        return JsonResponse({"username": "No Tag", "rfid": "N/A"})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

# 🚀 Start RFID Reader in the Background
def start_rfid_reader():
    thread = threading.Thread(target=scan_for_reader)
    thread.daemon = True  # Run in the background
    thread.start()

# Start the RFID reader when the server starts
start_rfid_reader()