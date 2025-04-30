# 1. Use the official Python image as the base
FROM python:3.11

# 2. Set the working directory in the container
WORKDIR /app

# 3. Copy all project files to /app in the container
COPY . .

# 4. Install dependencies from requirements.txt
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 5. Expose the port your app runs on
EXPOSE 8000

# 6. Command to run the app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
