FROM python:3.11-alpine

WORKDIR /backend
ENV PYTHONUNBUFFERED=1

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -v -r requirements.txt

# Install gunicorn for production/staging deployments
# RUN pip install gunicorn

# Copy the Django project code
COPY . .

EXPOSE 8000

# Command to run the Django development server - for production, use gunicorn instead
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]