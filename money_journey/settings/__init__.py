"""
Django settings module for money_journey project.

This module loads the appropriate settings based on the DJANGO_SETTINGS_MODULE
environment variable. Defaults to base settings.
"""

import os

# Determine which settings to load
settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', 'money_journey.settings.base')

if settings_module == 'money_journey.settings.production':
    from .production import *
else:
    from .base import *