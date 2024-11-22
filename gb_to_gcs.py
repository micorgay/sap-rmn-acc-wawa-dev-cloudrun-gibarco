import logging
import os
import requests
from flask import Flask, send_from_directory
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
# Headless Chrome Packages
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
# Modified selenium setup to include headless option
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from google.cloud import storage
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Configure Chrome options
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in headless mode
chrome_options.add_argument("--no-sandbox")  # Bypass OS security model
chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration

# Install Flask
app = Flask(__name__)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.static_folder, 'favicon.ico')

@app.route('/run', methods=['GET'])
def run_task():
    # Call your existing function that performs the login, download, and upload to GCS
    logging.debug("Starting the task...")
    # your_function()  # Uncomment this line and replace with your actual function
    return "Task completed!", 200

# Note: Remove the following block when using Gunicorn
#if __name__ == '__main__':
#    port = int(os.environ.get('PORT', 8080))
#    app.run(host='0.0.0.0', port=port)

# Function to upload data directly to GCS
def upload_to_gcs(bucket_name, destination_blob_name, data):
    """Uploads data to a GCS bucket."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_string(data)  # Upload the file content directly
    print(f"Data uploaded to {destination_blob_name} in bucket {bucket_name}.")
    
# Initialize Chrome WebDriver
print("Initializing Chrome WebDriver...")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    # Step 1: Open the login page
    print("Step 1: Opening the login page...")
    driver.get('https://wawa.applause.gilbarco.com/login.php')
    print("Login page opened.")
    # Step 2: Wait for username and password fields
    print("Step 2: Waiting for username and password fields...")
    wait = WebDriverWait(driver, 10)
    username_field = wait.until(EC.presence_of_element_located((By.NAME, "username")))
    password_field = wait.until(EC.presence_of_element_located((By.NAME, "password")))
    print("Username and password fields are present.")
    # Step 3: Enter credentials
    print("Step 3: Entering credentials...")
    username_field.send_keys('gPailavenkata')  # Replace with your actual username
    password_field.send_keys('Publicisvap123$')  # Replace with your actual password
    print("Credentials entered.")
    # Step 4: Submit the form
    print("Step 4: Submitting the login form...")
    password_field.send_keys(Keys.RETURN)
    print("Login form submitted.")
    # Step 5: Wait for redirection after login
    print("Step 5: Waiting for redirection after login...")
    wait.until(EC.url_contains("controlcenter"))
    print("Login successful, current URL:", driver.current_url)
    # Step 6: Retrieve cookies from Selenium session
    print("Step 6: Retrieving cookies from the Selenium session...")
    selenium_cookies = driver.get_cookies()
    # Set up a session for requests
    print("Step 7: Setting up a requests session...")
    session = requests.Session()
    # Add cookies to the requests session
    for cookie in selenium_cookies:
        session.cookies.set(cookie['name'], cookie['value'])
    print("Cookies added to requests session.")
    # Step 8: Construct the report URL
    start_date = "2024-11-19"  # Replace with actual variable
    end_date = "2024-11-19"    # Replace with actual variable
    print("start date: ", start_date)
    print("end date: ", end_date)
    report_url = f'https://wawa.applause.gilbarco.com/controlcenter/reports/fetch_report.php?report=promotions&daterange=custom&start_date={start_date}&end_date={end_date}'
    print(f"Step 8: Constructed report URL: {report_url}")
    # Step 9: Fetch the report data directly
    print("Step 9: Fetching the report data...")
    try:
        # response = session.get(report_url, timeout=30)  # Set a timeout of 30 seconds
        response = session.get(report_url)
        print(f"Response Status Code: {response.status_code}")  # Print status code
        print(f"Response Headers: {response.headers}")  # Print response headers
        if response.status_code == 200:
            print("Report fetched successfully.")
            print("start load time: ", datetime.now())
            # Prepare data for GCS upload with folder path
            bucket_name = 'sap-rmn-acc-wawa-dev-inbound-data'
            destination_file_name = f'vap/promotion-data-gbc-{start_date.replace("-", "")}-{end_date.replace("-", "")}.csv'
            # Upload the file content directly to GCS
            upload_to_gcs(bucket_name, destination_file_name, response.content)
            print("Report in GCS Bucket")
            print("end load time: ", datetime.now())
        else:
            print(f"Failed to download report: {response.status_code} - {response.text}")
    except requests.exceptions.Timeout:
        print("The request timed out while fetching the report.")
    except requests.exceptions.RequestException as req_err:
        print(f"Request error occurred: {req_err}")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    print("Closing the browser...")
    # Close the browser
    driver.quit()