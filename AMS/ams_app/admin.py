from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from ams_app.models import CustomUser

# Register the CustomUser model with the UserAdmin interface
class UserModel(UserAdmin):
    pass
admin.site.register(CustomUser,UserModel)