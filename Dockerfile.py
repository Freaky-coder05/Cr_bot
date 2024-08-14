# Use the official Python image as a base
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot's source code into the container
COPY . .

# Run the bot
CMD ["python", "bot.py"]
