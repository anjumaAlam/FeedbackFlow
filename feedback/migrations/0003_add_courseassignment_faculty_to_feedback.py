import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def migrate_faculty_data(apps, schema_editor):
    """Copy old Course.faculty → CourseAssignment (is_primary=True) and Feedback.faculty"""
    Course = apps.get_model('feedback', 'Course')
    CourseAssignment = apps.get_model('feedback', 'CourseAssignment')
    Feedback = apps.get_model('feedback', 'Feedback')

    for course in Course.objects.all():
        old_faculty_id = course.faculty_id  # Course still has faculty FK at this step
        if old_faculty_id:
            CourseAssignment.objects.get_or_create(
                course=course,
                faculty_id=old_faculty_id,
                defaults={'is_primary': True}
            )
            Feedback.objects.filter(course=course, faculty__isnull=True).update(faculty_id=old_faculty_id)


class Migration(migrations.Migration):

    dependencies = [
        ('feedback', '0002_feedback_class_section_alter_course_id_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Step 1: Add faculty to Feedback (nullable)
        migrations.AddField(
            model_name='feedback',
            name='faculty',
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={'role__in': ['Faculty', 'HOD']},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='feedback_received',
                to=settings.AUTH_USER_MODEL
            ),
        ),
        # Step 2: Create CourseAssignment table (faculty_id still on Course at this point)
        migrations.CreateModel(
            name='CourseAssignment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_primary', models.BooleanField(default=False)),
                ('assigned_at', models.DateTimeField(auto_now_add=True)),
                ('course', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='assignments',
                    to='feedback.course'
                )),
                ('faculty', models.ForeignKey(
                    limit_choices_to={'role__in': ['Faculty', 'HOD']},
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='course_assignments',
                    to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'verbose_name': 'Course Assignment',
                'verbose_name_plural': 'Course Assignments',
                'ordering': ['-is_primary', 'faculty__full_name'],
                'unique_together': {('course', 'faculty')},
            },
        ),
        # Step 3: Copy existing Course.faculty data → CourseAssignment + Feedback.faculty
        migrations.RunPython(migrate_faculty_data, migrations.RunPython.noop),
        # Step 4: Remove old faculty FK from Course
        migrations.RemoveField(
            model_name='course',
            name='faculty',
        ),
    ]
