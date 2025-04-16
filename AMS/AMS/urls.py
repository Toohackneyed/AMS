"""AMS URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views

from ams_app import views, adminviews, staffviews, studentviews
from AMS import settings

urlpatterns = [
    path('dashboard', views.dashboard),
    path('admin/', admin.site.urls),
    path('', views.LoginPage, name="show_login"),
    path('get_user_details/', views.GetUserDetails),
    path('logout_user/', views.Logout_user, name="logout_user"),
    path('LoggedIn', views.LoggedIn, name="LoggedIn"),
    path('admin_home/', adminviews.admin_home, name="admin_home"),
    path('add_staff/', adminviews.add_staff, name="add_staff"),
    path('add_staff_save', adminviews.add_staff_save, name="add_staff_save"),
    path('add_course/', adminviews.add_course, name="add_course"),
    path('add_course_save', adminviews.add_course_save, name="add_course_save"),
    path('add_section/', adminviews.add_section, name="add_section"),
    path('add_section_save', adminviews.add_section_save, name="add_section_save"),
    path('add_student/', adminviews.add_student, name="add_student"),
    path('add_student_save', adminviews.add_student_save, name="add_student_save"),
    path('add_subject/', adminviews.add_subject, name="add_subject"),
    path('add_subject_save', adminviews.add_subject_save, name="add_subject_save"),
    path('manage_staff/', adminviews.manage_staff, name="manage_staff"),
    path('manage_student/', adminviews.manage_student, name="manage_student"),
    path('manage_course/', adminviews.manage_course, name="manage_course"),
    path('manage_section/', adminviews.manage_section, name="manage_section"),
    path('manage_subject/', adminviews.manage_subject, name="manage_subject"),
    path('manage_session/', adminviews.manage_session,name="manage_session"),
    path('add_session_save', adminviews.add_session_save,name="add_session_save"),
    path('edit_staff/<str:staff_id>/', adminviews.edit_staff, name="edit_staff"),
    path('edit_staff_save', adminviews.edit_staff_save, name="edit_staff_save"),
    path('edit_student/<str:student_id>/', adminviews.edit_student, name="edit_student"),
    path('edit_student_save', adminviews.edit_student_save, name="edit_student_save"),
    path('edit_subject/<str:subject_id>/', adminviews.edit_subject, name="edit_subject"),
    path('edit_subject_save', adminviews.edit_subject_save, name="edit_subject_save"),
    path('edit_course/<int:course_id>/', adminviews.edit_course, name='edit_course'),
    path('edit_course_save', adminviews.edit_course_save, name="edit_course_save"),
    path('edit_section/<int:section_id>/', adminviews.edit_section, name='edit_section'),
    path('edit_section_save', adminviews.edit_section_save, name="edit_section_save"),
    path('admin_view_attendance', adminviews.admin_view_attendance, name="admin_view_attendance"),
    path('get_attendance', adminviews.get_attendance, name="get_attendance"),
    path('admin_profile', adminviews.admin_profile, name="admin_profile"),
    path('admin_profile_save', adminviews.admin_profile_save, name="admin_profile_save"),
    path('delete_course/<int:course_id>/', adminviews.delete_course, name='delete_course'),
    path('delete_section/<int:section_id>/', adminviews.delete_section, name='delete_section'),
    path('delete_session/<int:session_id>/', adminviews.delete_session, name='delete_session'),
    path('edit_session/<int:session_id>/', adminviews.edit_session, name='edit_session'),
    path('delete_staff/<int:staff_id>/', adminviews.delete_staff, name='delete_staff'),
    path('delete_subject/<int:subject_id>/', adminviews.delete_subject, name='delete_subject'),
    path('delete_student/<int:student_id>/', adminviews.delete_student, name='delete_student'),
    path("face_recognition_attendance/", adminviews.face_recognition_attendance, name="face_recognition_attendance"),
    path("auto_mark_attendance_live/", adminviews.auto_mark_attendance_live, name="auto_mark_attendance_live"),
    path("get_subjects_by_course/", adminviews.get_subjects_by_course, name="get_subjects_by_course"),
    path("get_sections_by_session_year/", adminviews.get_sections_by_session_year, name="get_sections_by_session_year"),
    path("download_attendance/", adminviews.download_attendance, name="download_attendance"),
    path("get_ongoing_subject/", adminviews.get_ongoing_subject, name="get_ongoing_subject"),
    path("scan_rfid/", adminviews.scan_rfid, name="scan_rfid"),
    path("api/rfid-scan/", adminviews.save_rfid_tag, name="save_rfid_tag"),


    path('reset-password/', auth_views.PasswordResetView.as_view(), name='reset_password'),
    path('check_face_encoding_status/', adminviews.check_face_encoding_status, name='check_face_encoding_status'),
        # Password Reset URLs
    path('reset-password/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('reset-password/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset-password-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset-password-complete/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

                  #     Staff URL Path
    path('staff_home/', staffviews.staff_home, name="staff_home"),
    path("staff/view-attendance/", staffviews.staff_view_attendance, name="staff_view_attendance"),
    path("staff/get-attendance/", staffviews.staff_get_attendance, name="staff_get_attendance"),
    path("staff/download-attendance/", staffviews.staff_download_attendance, name="staff_download_attendance"),
    path('update-attendance/', staffviews.staff_update_attendance_view, name='staff_update_attendance'),
    path('save-updated-attendance/', staffviews.save_updated_attendance, name='save_updated_attendance'),
    path('staff_profile', staffviews.staff_profile, name="staff_profile"),
    path('staff_profile_save', staffviews.staff_profile_save, name="staff_profile_save"),
    path('students-by-subject/', staffviews.students_by_subject, name='students_by_subject'),
                 #      Students URL Path
    path('student_home/', studentviews.student_home, name="student_home"),
    path('student/view_attendance/', studentviews.student_view_attendance, name='student_view_attendance'),
    path('student/get_attendance/', studentviews.student_get_attendance, name='student_get_attendance'),
    path('student/download_attendance/', studentviews.student_download_attendance, name='student_download_attendance'),
    path('student_profile', studentviews.student_profile, name="student_profile"),
    path('student_profile_save', studentviews.student_profile_save, name="student_profile_save"),
    path('student/my_subjects/', studentviews.student_my_subjects, name='student_my_subjects'),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
