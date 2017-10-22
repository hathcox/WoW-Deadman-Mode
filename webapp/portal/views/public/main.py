import smtplib, hashlib

from datetime import datetime, timedelta
from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth import logout, authenticate, login
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from portal.services import EmailService
from portal.models.user.portal_user import PortalUser
from django.contrib.auth.models import User
from django.conf import settings
from portal.utils import TokenGenerator
from django.db import connections, transaction

def main(request):
    if request.user is None:
        return HttpResponseRedirect('/splash')
    return HttpResponseRedirect('/user/dashboard')

def splash(request):
    online_player_count = 0            #Create the user in mangos
    with connections['realmd'].cursor() as cursor:
        sql_string = "SELECT COUNT(*) FROM account WHERE active_realm_id >0"
        cursor.execute(sql_string)
        online_player_count = cursor.fetchone()[0]
    return render(request, 'public/splash.html', {'online_player_count': online_player_count})

def features(request):
    return render(request, 'public/features.html')

def logoutview(request):
    ''' Logout the current user '''
    logout(request)
    return HttpResponseRedirect('/')

def loginview(request):
    if request.method == 'GET':
        error = request.GET.get('error', None)
        errors = []
        if error is not None:
            errors = [error]
        return render(request, 'public/login.html', { 'errors': errors })
    else:
        username = request.POST.get('username', None)
        password = request.POST.get('password', None)
        errors = []

        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                # Redirect to a success page.
                return HttpResponseRedirect('/')
            else:
                errors.append('This account is disabled, please contact us @ 555-555-5555')
        else:
            errors.append('Invalid username or password')

        return render(request, 'public/login.html', { 'errors': errors })

def register(request):
    if request.method == 'GET':
        return render(request, 'public/register.html')
    else:
        username = request.POST.get('username', None)
        password = request.POST.get('password', None)
        errors = []
        success = False

        #Look for a user with this username
        existing_user = PortalUser.objects.filter(username=username).all()
        if not existing_user:
            #Create the user in mangos
            with connections['realmd'].cursor() as cursor:
                #$sha_pass_hash = sha1(strtoupper($username).":".strtoupper($password));
                sha_password = (hashlib.sha1(username.upper()+":"+password.upper()).hexdigest()).upper()
                sql_string = "insert into account (username, sha_pass_hash, email, expansion) values ('%s', '%s', '%s', %d)" % (username, sha_password, username, 1)
                cursor.execute(sql_string)

            #Create the user in django
            new_user = PortalUser.objects.create_user(username=username, password=password)
            new_user.save()
            success = True
        else:
            errors.append('Existing User with that Username!')
        return render(request, 'public/register.html', {'errors':errors, "success": success})

def recover_password(request):
    if request.method == 'GET':
        return render(request, 'public/recover_password.html')
    else:
        userEmail = request.POST.get('email', None)

        emailService = EmailService(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_USERNAME, settings.EMAIL_HOST_PASSWORD)

        #generate
        token = TokenGenerator.create_random_token(8)
        user = PortalUser.objects.filter(email=userEmail).first()

        if user is not None:
            user.resetToken = token
            user.tokenCreateDate = datetime.now()
            emailService.send(userEmail, token, user.username)
            user.save()
            return render(request, 'public/email_sent.html')

    return render(request, 'public/recover_password.html')

def new_password(request, token):
    if request.method == "GET":
        user = PortalUser.objects.filter(resetToken=token).first()
        if user is not None:
            if user.tokenCreateDate < datetime.now()-timedelta(hours=4):
                return HttpResponseRedirect('/login?error=Your%20email%20token%20has%20expired.%20Please%20restart%20the%20process.')
        else:
            return HttpResponseRedirect('/login?error=Invalid%20token.')
        return render(request, 'public/new_password.html', {'token':token})
    else:
        errors = []
        user = PortalUser.objects.filter(resetToken=token).first()

        if user is not None:
            password = request.POST.get("password", None)
            passwordConfirm = request.POST.get("passwordConfirm", None)

            if password == passwordConfirm and len(password) > 8:
                user.set_password(password)
                user.save()

                return HttpResponseRedirect('/login')

            else:
                errors.append("Passwords don\'t match")
                return render(request, 'public/new_password.html', {'errors':errors})

def email_sent(request):
    if request.method == "GET":
        return render(request, 'public/email_sent.html')
