from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

# Middleware to check user login status
class LoginCheckMiddleWare(MiddlewareMixin):
    def process_view(self,request,view_func,view_args,view_kwargs):
        modulename=view_func.__module__
        print(modulename)
        user=request.user
        if user.is_authenticated:
            if user.user_type == "1":
                if modulename == "ams_app.adminviews":
                    pass
                elif modulename == "ams_app.views" or modulename == "django.views.static":
                    pass
                elif modulename == "django.contrib.auth.views" or modulename =="django.contrib.admin.sites":
                    pass
                else:
                    return HttpResponseRedirect(reverse("admin_home"))
            elif user.user_type == "2":
                if modulename == "ams_app.staffviews" or modulename == "ams_app.EditResultVIewClass":
                    pass
                elif modulename == "ams_app.views" or modulename == "django.views.static":
                    pass
                else:
                    return HttpResponseRedirect(reverse("staff_home"))
            elif user.user_type == "3":
                if modulename == "ams_app.studentviews" or modulename == "django.views.static":
                    pass
                elif modulename == "ams_app.views":
                    pass
                else:
                    return HttpResponseRedirect(reverse("student_home"))
            else:
                return HttpResponseRedirect(reverse("show_login"))

        else:
            if request.path == reverse("show_login") or request.path == reverse("LoggedIn") or modulename == "django.contrib.auth.views" or modulename =="django.contrib.admin.sites" or modulename=="ams_app.views":
                pass
            else:
                return HttpResponseRedirect(reverse("show_login"))