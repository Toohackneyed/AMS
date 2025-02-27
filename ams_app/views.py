from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from ams_app.EmailBackEnd import EmailBackEnd
from django.urls import reverse

# Create your views here.
def dashboard(request):
    return render(request,"dashboard.html")

def LoginPage(request):
    return render(request,"Login.html")

def LoggedIn(request):
    if request.method!="POST":
        return HttpResponse("<h2>Method Not Allowed</h2>")
    else:
        user =EmailBackEnd.authenticate(request,username=request.POST.get('email'),password=request.POST.get('password'))
        if user!=None:
            login(request,user)
            if user.user_type=="1":
                return HttpResponseRedirect('/admin_home')
            elif user.user_type=="2":
                return HttpResponseRedirect(reverse("staff_home"))
            else:
                return HttpResponseRedirect(reverse("student_home"))
        else:
            messages.error(request,'Invalid Login Details')
            return HttpResponseRedirect('/')
    
def GetUserDetails(request):
    if request.user!=None:
        return HttpResponse("User : "+request.user.email+" usertype : "+str(request.user.user_type))
    else:
        return HttpResponse("Please Login First")

def Logout_user(request):
    logout(request)
    return HttpResponseRedirect("/")