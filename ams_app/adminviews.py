
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
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.cache import cache
from datetime import datetime, timedelta
from django.utils.timezone import now

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
        student_count = Enrollment.objects.filter(subject=subject).count()  # ✅ Tamang query
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
        "student_count": student_count,
        "staff_count": staff_count,
        "subject_count": subject_count,
        "course_count": course_count,
        "course_name_list": course_name_list,
        "subject_count_list": subject_count_list,
        "student_count_list_in_course": student_count_list_in_course,
        "student_count_list_in_subject": student_count_list_in_subject,
        "subject_list": subject_list,
    }

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
            section_id = request.POST.get("section")  # ✅ Get section ID
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
                course_obj = Courses.objects.get(id=course_id)
                user.students.course_id = course_obj
                session_year = SessionYearModel.objects.get(id=session_year_id)
                user.students.session_year_id = session_year
                user.students.gender = gender

                # ✅ Fix Section Assignment
                section = Sections.objects.get(id=section_id)  # Get Section object from ID
                user.students.section = section  # ✅ Assign Section object

                # Save profile picture properly
                if profile_pic:
                    user.students.profile_pic = profile_pic 

                # ✅ Save student data first
                user.students.save()

                # ✅ Handle Subject Enrollment
                selected_subjects = request.POST.getlist("subjects")  
                if not selected_subjects:
                    messages.error(request, "Please select at least one subject.")
                    return HttpResponseRedirect(reverse("add_student"))

                # 🔥 Delete old enrollments para walang duplicates
                Enrollment.objects.filter(student=user.students).delete()

                # ✅ Save only selected subjects
                for subject_id in selected_subjects:
                    subject = Subjects.objects.get(id=subject_id)
                    Enrollment.objects.create(student=user.students, subject=subject)

                messages.success(request, "Successfully Added Student")
                return HttpResponseRedirect(reverse("add_student"))

            except Sections.DoesNotExist:
                messages.error(request, "Selected section does not exist.")
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

@csrf_exempt
def mark_attendance(request):
    """Process image and mark attendance based on face recognition."""
    if request.method == "POST":
        try:
            file = request.FILES.get("image")  # Expecting an image file upload
            subject_id = request.POST.get("subject_id")

            if not file or not subject_id:
                return JsonResponse({"error": "Missing image or subject ID"}, status=400)

            # Read the uploaded image
            np_arr = np.frombuffer(file.read(), np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # Extract face encoding
            face_locations = face_recognition.face_locations(rgb_img)
            face_encodings = face_recognition.face_encodings(rgb_img, face_locations)

            if not face_encodings:
                return JsonResponse({"error": "No face detected"}, status=400)

            encoding = face_encodings[0]
            students = Students.objects.exclude(face_encoding=None)

            for student in students:
                stored_encoding = np.array(json.loads(student.face_encoding))
                matches = face_recognition.compare_faces([stored_encoding], encoding)
                
                if matches[0]:
                    today = date.today()
                    attendance, created = Attendance.objects.get_or_create(
                        subject_id=subject_id,
                        attendance_date=today,
                        session_year_id=student.session_year_id
                    )

                    AttendanceReport.objects.update_or_create(
                        student=student,
                        attendance=attendance,
                        defaults={"status": True}
                    )

                    return JsonResponse({"message": f"✅ Attendance marked for {student.admin.username}!"})

            return JsonResponse({"error": "No matching student found"}, status=404)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)

def get_ongoing_subject(request):
    current_time = now().time()  # Diretso na, hindi na kailangang `localtime(now())`
    today = now().strftime("%A")  # Kunin ang araw ngayon (Monday, Tuesday, etc.)

    # Hanapin ang kasalukuyang subject na naka-schedule ngayon
    ongoing_subjects = SubjectSchedule.objects.filter(
        day_of_week=today,
        start_time__lte=current_time,
        end_time__gte=current_time
    )

    if ongoing_subjects.exists():
        data = [
            {"subject_name": sub.subject.subject_name, "start_time": str(sub.start_time), "end_time": str(sub.end_time)}
            for sub in ongoing_subjects
        ]
        return JsonResponse({"ongoing_classes": data})
    
    return JsonResponse({"error": "No ongoing class at the moment."}, status=404)

def recognize_student(image):
    """Subukang i-recognize ang student gamit ang facial recognition."""
    image_data = image.read()
    uploaded_image = face_recognition.load_image_file(ContentFile(image_data))
    uploaded_encodings = face_recognition.face_encodings(uploaded_image)
    
    if not uploaded_encodings:
        return None  # Walang mukha na nakita

    uploaded_encoding = uploaded_encodings[0]

    students = Students.objects.all()
    for student in students:
        if student.face_encoding:  # Siguraduhin na may stored encoding
            known_encoding = student.face_encoding
            match = face_recognition.compare_faces([known_encoding], uploaded_encoding)
            if match[0]:  # Kung may match
                return student

    return None  # Walang match

@csrf_exempt
def auto_mark_attendance_live(request):
    if request.method == "POST":
        subject_id = request.POST.get("subject_id")
        if not subject_id or subject_id == "undefined":
            return JsonResponse({"error": "Invalid subject ID"}, status=400)

        try:
            subject_id = int(subject_id)  # Convert to integer
            subject = SubjectSchedule.objects.get(id=subject_id)
        except (ValueError, SubjectSchedule.DoesNotExist):
            return JsonResponse({"error": "Subject not found"}, status=404)

        image = request.FILES.get("image")
        if not image:
            return JsonResponse({"error": "Missing image"}, status=400)

        current_time = now().astimezone().time()
        student = recognize_student(image)
        if not student:
            return JsonResponse({"error": "No recognized student"}, status=404)

        # Tukuyin kung PRESENT, LATE, o ABSENT
        status = "absent"
        if subject.start_time <= current_time <= subject.end_time:
            if current_time <= subject.start_time.replace(minute=subject.start_time.minute + 15):
                status = "present"
            else:
                status = "late"

        # I-save ang attendance
        Attendance.objects.update_or_create(
            student=student,
            subject=subject,
            defaults={"status": status}
        )

        return JsonResponse({
            "student_name": student.get_full_name(),
            "status": status
        })

    return JsonResponse({"error": "Invalid request method"}, status=405)
