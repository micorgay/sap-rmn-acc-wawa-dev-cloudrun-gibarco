import logging
import os
import requests
from flask import Flask, send_from_directory
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from google.cloud import storage
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask
app = Flask(__name__)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.static_folder, 'favicon.ico')

@app.route('/run', methods=['GET'])
def run_task():
    """
    Endpoint to trigger the task of fetching a report and uploading it to GCS.
    """
    logger.info("Received request to /run endpoint.")
    try:
        perform_task()
        return "Task completed!", 200
    except Exception as e:
        logger.exception("Task failed.")
        return f"Task failed: {e}", 500

def upload_to_gcs(bucket_name, destination_blob_name, data):
    """
    Uploads data to a GCS bucket.
    
    Args:
        bucket_name (str): Name of the GCS bucket.
        destination_blob_name (str): Destination path in the bucket.
        data (bytes): Data to upload.
    """
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_string(data)
        logger.info(f"Data uploaded to {destination_blob_name} in bucket {bucket_name}.")
    except Exception as e:
        logger.exception("Failed to upload data to GCS.")
        raise e

def perform_task():
    """
    Performs the task of logging into the website, fetching the report, and uploading it to GCS.
    """
    # Configure Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")  # Bypass OS security model
    chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration

    # Initialize Chrome WebDriver
    logger.info("Initializing Chrome WebDriver...")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        # Step 1: Open the login page
        logger.info("Step 1: Opening the login page...")
        driver.get('https://wawa.applause.gilbarco.com/login.php')
        logger.info("Login page opened.")

        # Step 2: Wait for username and password fields
        logger.info("Step 2: Waiting for username and password fields...")
        wait = WebDriverWait(driver, 10)
        username_field = wait.until(EC.presence_of_element_located((By.NAME, "username")))
        password_field = wait.until(EC.presence_of_element_located((By.NAME, "password")))
        logger.info("Username and password fields are present.")

        # Step 3: Enter credentials
        logger.info("Step 3: Entering credentials...")
        username = os.environ.get('GILBARCO_USERNAME')
        password = os.environ.get('GILBARCO_PASSWORD')
        if not username or not password:
            raise Exception("Username or password not set in environment variables.")
        username_field.send_keys(username)
        password_field.send_keys(password)
        logger.info("Credentials entered.")

        # Step 4: Submit the form
        logger.info("Step 4: Submitting the login form...")
        password_field.send_keys(Keys.RETURN)
        logger.info("Login form submitted.")

        # Step 5: Wait for redirection after login
        logger.info("Step 5: Waiting for redirection after login...")
        wait.until(EC.url_contains("controlcenter"))
        logger.info(f"Login successful, current URL: {driver.current_url}")

        # Step 6: Retrieve cookies from Selenium session
        logger.info("Step 6: Retrieving cookies from the Selenium session...")
        selenium_cookies = driver.get_cookies()

        # Set up a session for requests
        logger.info("Step 7: Setting up a requests session...")
        session = requests.Session()

        # Add cookies to the requests session
        for cookie in selenium_cookies:
            session.cookies.set(cookie['name'], cookie['value'])
        logger.info("Cookies added to requests session.")

        # Step 8: Construct the report URL with dynamic dates
        yesterday = datetime.now() - timedelta(days=1)
        start_date = yesterday.strftime('%Y-%m-%d')
        end_date = yesterday.strftime('%Y-%m-%d')
        logger.info(f"Start date: {start_date}")
        logger.info(f"End date: {end_date}")
        report_url = (
            f'https://wawa.applause.gilbarco.com/controlcenter/reports/fetch_report.php'
            f'?report=promotions&daterange=custom&start_date={start_date}&end_date={end_date}'
        )
        logger.info(f"Step 8: Constructed report URL: {report_url}")

        # Step 9: Fetch the report data directly
        logger.info("Step 9: Fetching the report data...")
        try:
            response = session.get(report_url, timeout=30)
            logger.info(f"Response Status Code: {response.status_code}")
            logger.info(f"Response Headers: {response.headers}")
            if response.status_code == 200:
                logger.info("Report fetched successfully.")
                logger.info(f"Start load time: {datetime.now()}")

                # Prepare data for GCS upload with folder path
                bucket_name = 'sap-rmn-acc-wawa-dev-inbound-data'
                destination_file_name = (
                    f'vap/promotion-data-gbc-{start_date.replace("-", "")}-{end_date.replace("-", "")}.csv'
                )

                # Upload the file content directly to GCS
                upload_to_gcs(bucket_name, destination_file_name, response.content)
                logger.info("Report uploaded to GCS Bucket")
                logger.info(f"End load time: {datetime.now()}")
            else:
                logger.error(f"Failed to download report: {response.status_code} - {response.text}")
                raise Exception(f"Failed to download report: {response.status_code} - {response.text}")
        except requests.exceptions.Timeout:
            logger.error("The request timed out while fetching the report.")
            raise
        except requests.exceptions.RequestException as req_err:
            logger.error(f"Request error occurred: {req_err}")
            raise

    except Exception as e:
        logger.exception("An error occurred during the task execution.")
        raise e
    finally:
        logger.info("Closing the browser...")
        # Close the browser
        driver.quit()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting Flask app on port {port}...")
    app.run(host='0.0.0.0', port=port)
