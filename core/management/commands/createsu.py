from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
import os

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        username = os.environ.get('SU_USERNAME')
        email = os.environ.get('SU_EMAIL')
        password = os.environ.get('SU_PASSWORD')

        if username and password:
            user, created = User.objects.get_or_create(username=username)
            user.email = email
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.save()

            if created:
                print("Superuser creado")
            else:
                print("Superuser actualizado")