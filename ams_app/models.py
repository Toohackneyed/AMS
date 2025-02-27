from django.db import models
import json
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
import face_recognition
from django.core.files.base import ContentFile
from PIL import Image
import numpy as np
import io
from django.db.models.signals import post_delete

class SessionYearModel(models.Model):
    id = models.AutoField(primary_key=True)
    session_start_date = models.DateField() 
    session_end_date = models.DateField()   
    objects = models.Manager()

class SessionTimeModel(models.Model):
    id = models.AutoField(primary_key=True)
    session_year = models.ForeignKey(SessionYearModel, on_delete=models.CASCADE)
    session_start_time = models.TimeField()
    session_end_time = models.TimeField()
    objects = models.Manager()

class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        (1, "Admin"),
        (2, "Staff"),
        (3, "Student"),
    )
    user_type = models.CharField(default=1, choices=USER_TYPE_CHOICES, max_length=10)

    groups = models.ManyToManyField(
        "auth.Group",
        related_name="customuser_groups",  # Prevents conflicts
        blank=True
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        related_name="customuser_permissions",  # Prevents conflicts
        blank=True
    )

class Admin(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = models.Manager()

class Staffs(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = models.Manager()

    def delete(self, *args, **kwargs):
        """Delete the associated CustomUser before deleting Staff"""
        if self.admin:
            self.admin.delete()
        super().delete(*args, **kwargs)  # Delete the Staff record


class Courses(models.Model):
    course_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = models.Manager()

class Subjects(models.Model):
    subject_name = models.CharField(max_length=255)
    subject_code = models.CharField(max_length=255, unique=True)
    course = models.ForeignKey(Courses, on_delete=models.CASCADE)
    staff = models.ForeignKey(Staffs, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = models.Manager()

class SubjectSchedule(models.Model):
    subject = models.ForeignKey(Subjects, on_delete=models.CASCADE, related_name="schedules")  
    day_of_week = models.CharField(
        max_length=10,
        choices=[
            ("Monday", "Monday"),
            ("Tuesday", "Tuesday"),
            ("Wednesday", "Wednesday"),
            ("Thursday", "Thursday"),
            ("Friday", "Friday"),
            ("Saturday", "Saturday"),
            ("Sunday", "Sunday"),
        ]
    )  
    start_time = models.TimeField() 
    end_time = models.TimeField() 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = models.Manager()

class Students(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    gender = models.CharField(max_length=255)
    profile_pic = models.ImageField(upload_to="profile_pics/", null=True, blank=True)
    id_number = models.CharField(max_length=255, unique=True)
    rfid = models.CharField(max_length=100, unique=True)
    course_id = models.ForeignKey(Courses, on_delete=models.DO_NOTHING)
    session_year_id = models.ForeignKey(SessionYearModel, on_delete=models.CASCADE)
    subjects = models.ManyToManyField(Subjects, through="Enrollment", blank=True)
    face_encoding = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = models.Manager()

    def delete(self, *args, **kwargs):
        """Delete the associated CustomUser before deleting Student"""
        if self.admin:
            self.admin.delete()
        super().delete(*args, **kwargs)  # Delete the Student record

    def save(self, *args, **kwargs):
        if self.profile_pic:
            self.generate_face_encoding()
        super().save(*args, **kwargs)

    def generate_face_encoding(self):
        """Extract face encoding from the uploaded profile picture."""
        if not self.profile_pic:
            return

        try:
            image = Image.open(self.profile_pic)
            image = image.convert("RGB")
            img_array = np.array(image)
            face_locations = face_recognition.face_locations(img_array)
            face_encodings = face_recognition.face_encodings(img_array, face_locations)

            if face_encodings:
                self.face_encoding = json.dumps(face_encodings[0].tolist())  # Save as JSON
        except Exception as e:
            print(f"Error processing image: {e}")

    def get_face_encoding(self):
        return json.loads(self.face_encoding) if self.face_encoding else None

class Enrollment(models.Model):
    student = models.ForeignKey(Students, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subjects, on_delete=models.CASCADE)
    enrollment_date = models.DateTimeField(auto_now_add=True)  # Kailan siya nag-enroll
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("student", "subject")  # Para maiwasan ang duplicate enrollment
    def __str__(self):
        return f"{self.student.admin.first_name} - {self.subject.subject_name}"

class Attendance(models.Model):
    subject = models.ForeignKey(Subjects, on_delete=models.DO_NOTHING)
    schedule = models.ForeignKey(SubjectSchedule, on_delete=models.CASCADE)
    attendance_date = models.DateField()
    session_year = models.ForeignKey(SessionYearModel, on_delete=models.CASCADE)
    students = models.ManyToManyField(Students, related_name="attendances")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = models.Manager()

class AttendanceReport(models.Model):
    STATUS_CHOICES = [
        ("Present", "Present"),
        ("Late", "Late"),
        ("Absent", "Absent"),
    ]

    student = models.ForeignKey(Students, on_delete=models.CASCADE)
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Absent") 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = models.Manager()

@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.user_type == 1:
            Admin.objects.create(admin=instance)
        elif instance.user_type == 2:
            Staffs.objects.create(admin=instance)
        elif instance.user_type == 3:
            try:
                default_course = Courses.objects.get(id=1)  
                default_session = SessionYearModel.objects.get(id=1)
                Students.objects.create(
                    admin=instance,
                    course_id=default_course,
                    session_year_id=default_session,
                    rfid="",
                    profile_pic="",
                    gender=""
                )
            except Courses.DoesNotExist or SessionYearModel.DoesNotExist:
                print("Error: No default course or session year found!")

@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    if instance.user_type == 1:
        instance.admin.save()
    elif instance.user_type == 2:
        instance.staffs.save()
    elif instance.user_type == 3:
        instance.students.save()

@receiver(post_delete, sender=Students)
def delete_student_user(sender, instance, **kwargs):
    """Automatically delete CustomUser when a Student is deleted"""
    if instance.admin:
        instance.admin.delete()

@receiver(post_delete, sender=Staffs)
def delete_staff_user(sender, instance, **kwargs):
    """Automatically delete CustomUser when a Staff is deleted"""
    if instance.admin:
        instance.admin.delete()