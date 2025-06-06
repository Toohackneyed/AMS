from rest_framework import serializers
from ams_app.models import Students, Subjects

class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Students
        fields = ['id', 'rfid', 'admin']

class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subjects
        fields = ['id', 'subject_name', 'start_time', 'end_time', 'day_of_week']

class AttendanceInputSerializer(serializers.Serializer):
    subject_id = serializers.IntegerField()
    image = serializers.ImageField()