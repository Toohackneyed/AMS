
from datetime import date
import cv2
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
import json
import base64
import io
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.cache import cache
from datetime import datetime, timedelta
from django.utils.timezone import now

from ams_app.models import CustomUser, SessionTimeModel, Staffs, Courses, Subjects, Students, SessionYearModel, SubjectSchedule, Attendance, AttendanceReport, Enrollment

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
        student_count = Students.objects.filter(course_id=subject.course).count()
        subject_list.append(subject.subject_name)
        student_count_list_in_subject.append(student_count)

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

def get_subjects_by_course(request):
    course_ids = request.GET.get("courses")
    
    if not course_ids:
        return JsonResponse({"subjects": []})
    
    course_ids = course_ids.split(",")  # Convert CSV to list
    subjects = Subjects.objects.filter(course_id__in=course_ids).values("id", "subject_name")

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

                # Save profile picture properly
                if profile_pic:
                    user.students.profile_pic = profile_pic  # ✅ Correct way to save

                user.save()

                # Save subjects using Enrollment model
                selected_subjects = request.POST.getlist("subjects")  # Use getlist() for multiple values
                if not selected_subjects:
                    messages.error(request, "Please select at least one subject.")
                    return HttpResponseRedirect(reverse("add_student"))


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
    students = Students.objects.select_related("admin", "course_id", "session_year_id") \
                               .prefetch_related("enrollment_set__subject").all()

    # Debugging: Print enrolled subjects
    for student in students:
        print(f"Student: {student.admin.first_name} {student.admin.last_name}")
        for enrollment in student.enrollment_set.all():
            print(f"  Subject: {enrollment.subject.subject_name}")

    return render(request, "admin_template/manage_student_template.html", {"students": students})


def manage_course(request):
    courses = Courses.objects.all()
    return render(request, "admin_template/manage_course_template.html", {"courses": courses})

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

def edit_student(request,student_id):
    request.session['student_id']=student_id
    student=Students.objects.get(admin=student_id)
    form=EditStudentForm()
    form.fields['email'].initial=student.admin.email
    form.fields['first_name'].initial=student.admin.first_name
    form.fields['last_name'].initial=student.admin.last_name
    form.fields['username'].initial=student.admin.username
    form.fields['rfid'].initial=student.rfid
    form.fields['id_number'].initial=student.id_number
    form.fields['course'].initial=student.course_id.id
    form.fields['gender'].initial=student.gender
    form.fields['session_year_id'].initial=student.session_year_id.id

    return render(request,"admin_template/edit_student_template.html",{"form":form,"id":student_id,"username":student.admin.username, "id_number": student.id_number})

def edit_student_save(request):
    if request.method!="POST":
        return HttpResponse("<h2>Method Not Allowed</h2>")
    else:
        student_id=request.session.get("student_id")
        if student_id==None:
            return HttpResponseRedirect(reverse("manage_student"))

        form=EditStudentForm(request.POST,request.FILES)
        if form.is_valid():
            email = form.cleaned_data["email"]
            first_name = form.cleaned_data["first_name"]
            last_name = form.cleaned_data["last_name"]
            username = form.cleaned_data["username"]
            rfid = form.cleaned_data["rfid"]
            id_number = form.cleaned_data["id_number"]
            course_id = form.cleaned_data["course"]
            gender = form.cleaned_data["gender"]
            session_year_id=form.cleaned_data["session_year_id"]

            if request.FILES.get('profile_pic',False):
                profile_pic=request.FILES['profile_pic']
                fs=FileSystemStorage()
                filename=fs.save(profile_pic.name,profile_pic)
                profile_pic_url=fs.url(filename)
            else:
                profile_pic_url=None


            try:
                user=CustomUser.objects.get(id=student_id)
                user.first_name=first_name
                user.last_name=last_name
                user.username=username
                user.email=email
                user.save()

                student=Students.objects.get(admin=student_id)
                student.rfid=rfid
                session_year = SessionYearModel.objects.get(id=session_year_id)
                student.session_year_id = session_year
                student.id_number=id_number
                student.gender=gender
                course=Courses.objects.get(id=course_id)
                student.course_id=course
                if profile_pic_url!=None:
                    student.profile_pic=profile_pic_url
                student.save()
                del request.session['student_id']
                messages.success(request,"Successfully Edited Student")
                return HttpResponseRedirect(reverse("edit_student",kwargs={"student_id":student_id}))
            except:
                messages.error(request,"Failed to Edit Student")
                return HttpResponseRedirect(reverse("edit_student",kwargs={"student_id":student_id}))
        else:
            form=EditStudentForm(request.POST)
            student=Students.objects.get(admin=student_id)
            return render(request,"hod_template/edit_student_template.html",{"form":form,"id":student_id,"username":student.admin.username, "id_number": id_number})

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

            # Update or Create Subject Schedules
            for i in range(len(days)):
                if start_times[i] >= end_times[i]:
                    raise ValidationError("Start time must be before end time.")

                if i < len(schedule_ids):  
                    schedule = SubjectSchedule.objects.get(id=schedule_ids[i])
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

    context = {
        'subjects': subjects,
        'schedules': schedules,
        'session_years': session_years
    }
    
    return render(request, "admin_template/admin_view_attendance.html", context)


@csrf_exempt
def get_attendance(request):
    """ Fetch attendance records based on selected filters """
    if request.method == 'POST':
        subject_id = request.POST.get('subject')
        session_year_id = request.POST.get('session_year')
        schedule_id = request.POST.get('schedule')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        # Convert string dates to Python date format
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        # Get attendance records
        attendance_records = Attendance.objects.filter(
            subject_id=subject_id,
            session_year_id=session_year_id,
            schedule_id=schedule_id,
            attendance_date__range=(start_date, end_date)
        )

        # Prepare JSON response
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
    student = get_object_or_404(Students, admin__id=student_id)  # Use admin.id to get the student
    student.delete()
    messages.success(request, "Student successfully deleted.")
    return redirect('manage_student')  # Adjust the redirect to the correct name for your student management view

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


@csrf_exempt
def mark_attendance_live(request):
    if request.method == "POST":
        try:
            file = request.FILES.get("image")
            subject_id = request.POST.get("subject_id")

            if not file or not subject_id:
                return JsonResponse({"error": "Missing image or subject ID"}, status=400)

            # Get subject schedule
            subject_schedule = SubjectSchedule.objects.filter(subject_id=subject_id).first()
            if not subject_schedule:
                return JsonResponse({"error": "No schedule found for this subject"}, status=404)

            # Compute grace periods
            start_time = subject_schedule.start_time
            grace_period_end = (datetime.combine(now().date(), start_time) + timedelta(minutes=5)).time()  # Present
            late_period_end = (datetime.combine(now().date(), start_time) + timedelta(minutes=15)).time()  # Late
            current_time = now().time()

            # Determine attendance status
            if current_time <= grace_period_end:
                status = "Present"
            elif current_time <= late_period_end:
                status = "Late"
            else:
                return JsonResponse({"error": "You are too late! Attendance not recorded."}, status=400)

            # Process face recognition
            np_arr = np.frombuffer(file.read(), np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
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
                    today = now().date()
                    attendance, created = Attendance.objects.get_or_create(
                        subject_id=subject_id,
                        attendance_date=today,
                        session_year_id=student.session_year_id
                    )

                    AttendanceReport.objects.update_or_create(
                        student=student,
                        attendance=attendance,
                        defaults={"status": status}
                    )

                    return JsonResponse({"message": f"✅ {student.admin.username} marked as {status}!"})

            return JsonResponse({"error": "No matching student found"}, status=404)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)