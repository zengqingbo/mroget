# Use an official Python runtime as a parent image
FROM python:3.5

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
ADD . /app

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt --no-index -f pypi/

# Run tasks
ENTRYPOINT celery worker -A tasks -c 1 -Q main -l info
