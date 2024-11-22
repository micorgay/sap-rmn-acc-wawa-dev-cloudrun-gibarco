# Use the official Python image as the base image
FROM python:3.8-slim

# Set the working directory in the container
WORKDIR /app

# Install necessary dependencies for Chrome and ChromeDriver
RUN apt-get update && apt-get install -y \
    wget \
    gnupg2 \
    unzip \
    xvfb \
    libxi6 \
    libgconf-2-4 \
    libnss3 \
    libxss1 \
    libasound2 \
    fonts-liberation \
    libappindicator3-1 \
    libgtk-3-0 \
    xdg-utils \
    default-jdk \
    chromium \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Create the application directory
RUN mkdir /src
WORKDIR /src

# Copy the application code and requirements file
COPY gb_to_gcs.py /src/
COPY requirements.txt /src/

# Install Python dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entrypoint script
COPY entrypoint.sh /entrypoint.sh

# Make the entrypoint script executable
RUN chmod +x /entrypoint.sh

# Download Google Chrome
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get update && \
    apt-get install -y ./google-chrome-stable_current_amd64.deb && \
    rm google-chrome-stable_current_amd64.deb

# Get the latest ChromeDriver version using wget only
RUN LATEST=$(wget -q -O - https://chromedriver.storage.googleapis.com/LATEST_RELEASE) \
    && wget -q "https://chromedriver.storage.googleapis.com/$LATEST/chromedriver_linux64.zip" \
    && unzip chromedriver_linux64.zip \
    && mv chromedriver /usr/local/bin/ \
    && rm chromedriver_linux64.zip


# Give permissions to the ChromeDriver
RUN chmod +x /usr/local/bin/chromedriver

# Set environment variables for Chrome to run in headless mode
ENV DISPLAY=:99
ENV HOST 0.0.0.0

# Install necessary display server and tools for headless Chrome
RUN apt-get install -y xvfb

# Install Flask
RUN pip install flask

# Set the command to run when the container starts
CMD ["python", "gb_to_gcs.py"]

# Expose port 8080
EXPOSE 8080

# Set the entrypoint
ENTRYPOINT ["/entrypoint.sh"]