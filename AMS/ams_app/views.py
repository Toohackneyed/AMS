from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from ams_app.EmailBackEnd import EmailBackEnd
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
import os

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

RFID_LOG_FILE = 'rfid_tags.txt'

@csrf_exempt
def rfid_endpoint(request):
    if request.method == 'POST':
        rfid = request.POST.get('rfid')
        if rfid:
            # Ensure file exists
            if not os.path.exists(RFID_LOG_FILE):
                open(RFID_LOG_FILE, 'w').close()

            # Read all existing RFID tags
            with open(RFID_LOG_FILE, 'r') as f:
                existing_rfids = set(line.strip() for line in f)

            if rfid not in existing_rfids:
                with open(RFID_LOG_FILE, 'a') as f:
                    f.write(rfid + '\n')
                return JsonResponse({'status': 'success', 'rfid': rfid})
            else:
                return JsonResponse({'status': 'duplicate', 'rfid': rfid})
        return JsonResponse({'status': 'error', 'message': 'Missing RFID'}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=405)