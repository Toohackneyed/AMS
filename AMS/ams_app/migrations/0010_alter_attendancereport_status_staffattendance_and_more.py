# Generated by Django 5.1.6 on 2025-06-03 18:23

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ams_app', '0009_staffs_face_encoding_staffs_profile_pic'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attendancereport',
            name='status',
            field=models.CharField(choices=[('Present', 'Present'), ('Present (No ID)', 'Present (No ID)'), ('Late', 'Late'), ('Late (No ID)', 'Late (No ID)'), ('Absent', 'Absent'), ('Absent (No ID)', 'Absent (No ID)')], default='Absent', max_length=20),
        ),
        migrations.CreateModel(
            name='StaffAttendance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attendance_date', models.DateField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('schedule', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ams_app.subjectschedule')),
                ('staff', models.ManyToManyField(related_name='staff_attendances', to='ams_app.staffs')),
                ('subject', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='ams_app.subjects')),
            ],
        ),
        migrations.CreateModel(
            name='StaffAttendanceReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('marked_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('status', models.CharField(choices=[('Present', 'Present'), ('Late', 'Late'), ('Absent', 'Absent')], default='Absent', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('attendance', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ams_app.staffattendance')),
                ('staff', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ams_app.staffs')),
            ],
        ),
    ]
