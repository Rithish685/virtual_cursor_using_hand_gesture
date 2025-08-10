# 1. Use an official Python runtime as a parent image
FROM python:3.9-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Copy the requirements file into the container
COPY requirements.txt .

# 4. Install system dependencies required by OpenCV and Tkinter for GUI
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libgtk2.0-0 \
    libx11-6 \
    && rm -rf /var/lib/apt/lists/*

# 5. Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the rest of your application's code into the container
COPY . .

# 7. Specify the command to run on container start
#    !!! REMEMBER to replace 'your_main_script.py' with your actual script name !!!
CMD ["python", "gesture+ui.py"]
