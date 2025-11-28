#!/usr/bin/env python
import os
import sys

# Set environment variable before importing Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'osym_ai.settings')
os.environ['DJANGO_ENV'] = 'office_development'

import django
django.setup()

from django.core.management import execute_from_command_line

if __name__ == '__main__':
    execute_from_command_line(['manage.py', 'runserver'])
