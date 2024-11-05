# Use an official Python runtime as a parent image
FROM python:3.9

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 6789 and 6790 available to the world outside this container
EXPOSE 6789 6790

# Define environment variable to help configure your app
ENV NAME World

# Run server.py when the container launches
CMD ["python", "server.py"]

