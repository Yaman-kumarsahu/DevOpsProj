# Step 1: Use the official Python image from Docker Hub
FROM python:3.13

# Step 2: Set the working directory inside the container
WORKDIR /DevOpsProj

# Step 3: Copy the requirements.txt file into the container
COPY requirements.txt .

# Step 4: Install the dependencies inside the container
RUN pip install --no-cache-dir -r requirements.txt

# Step 5: Copy the entire application into the container
COPY . .

# Step 6: Set environment variables for Flask
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Step 7: Expose port 5000, the port Flask runs on by default
EXPOSE 5000

# Step 8: Define the command to run your app
CMD ["flask", "run"]
