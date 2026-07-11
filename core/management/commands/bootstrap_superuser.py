import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Creates the initial administrator from ADMIN_* environment variables.'

    def handle(self, *args, **options):
        username = os.environ.get('ADMIN_USERNAME')
        email = os.environ.get('ADMIN_EMAIL', '')
        password = os.environ.get('ADMIN_PASSWORD')

        if not username and not password:
            self.stdout.write('No ADMIN_* credentials supplied; skipping admin bootstrap.')
            return
        if not username or not password:
            raise CommandError('Set both ADMIN_USERNAME and ADMIN_PASSWORD to bootstrap an administrator.')

        User = get_user_model()
        user, created = User.objects.get_or_create(username=username, defaults={'email': email})

        if created:
            user.set_password(password)
        elif email and user.email != email:
            user.email = email

        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.role = 'ADMIN'
        user.save()

        message = 'Created' if created else 'Confirmed'
        self.stdout.write(self.style.SUCCESS(f'{message} administrator: {username}'))
