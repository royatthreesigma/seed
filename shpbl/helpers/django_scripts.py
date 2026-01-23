"""Python scripts to execute inside containers for Django operations"""

CREATE_URLS_SCRIPT = '''
from pathlib import Path
import sys

app_name = sys.argv[1]

urls_content = f"""\\"""URL configuration for {app_name} app.\\"""
from django.urls import path
from . import views

app_name = '{app_name}'

urlpatterns = [
    # Add your URL patterns here
]
"""

Path(f'{app_name}/urls.py').write_text(urls_content)
'''

INCLUDE_URLS_SCRIPT = """
import re
from pathlib import Path
import sys

app_name = sys.argv[1]
base_url = sys.argv[2]

config_urls = Path('config/urls.py')
content = config_urls.read_text()

# Check if already included
if f'{app_name}.urls' in content:
    sys.exit(0)

# Add include to imports if not present
if 'from django.urls import' in content:
    if 'include' not in content:
        content = content.replace(
            'from django.urls import path',
            'from django.urls import path, include'
        )
elif 'from django.urls import' not in content:
    content = 'from django.urls import path, include\\n' + content

# Add to urlpatterns
pattern = r'(urlpatterns\\s*=\\s*\\[)'
new_pattern = f"    path('{base_url}', include('{app_name}.urls')),\\n"
content = re.sub(pattern, r'\\1\\n' + new_pattern, content)

config_urls.write_text(content)
"""

ADD_INSTALLED_APP_SCRIPT = """
import re
from pathlib import Path
import sys

app_name = sys.argv[1]

settings_file = Path('config/settings.py')
content = settings_file.read_text()

# Check if already in INSTALLED_APPS
if f"'{app_name}'" in content or f'"{app_name}"' in content:
    sys.exit(0)

# Add to INSTALLED_APPS
pattern = r'(INSTALLED_APPS\\s*=\\s*\\[)'
new_app = f"    '{app_name}',\\n"
content = re.sub(pattern, r'\\1\\n' + new_app, content)

settings_file.write_text(content)
"""
