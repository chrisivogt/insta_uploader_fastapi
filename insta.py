import argparse
import json
import logging
import os
from instagrapi import Client
from instagrapi.exceptions import LoginRequired

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

def load_credentials(filepath):
    """
    Reads username and password from a JSON file.
    Expected JSON format: {"username": "your_user", "password": "your_password"}
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Credentials file not found at: {filepath}")
    
    with open(filepath, 'r') as f:
        creds = json.load(f)
    
    if "username" not in creds or "password" not in creds:
        raise ValueError("File must contain both 'username' and 'password' keys.")
        
    return creds["username"], creds["password"], creds["proxy_url"], creds["delay_range_bottom"], creds["delay_range_top"]

def login_user(insta_username):
    """
    Attempts to login to Instagram using either the provided session information
    or the provided username and password.
    """
    # Read creds file
    filepath = "creds/" + insta_username + "_creds.json"
    username, password, PROXY_URL, DELAY_RANGE_BOTTOM, DELAY_RANGE_TOP = load_credentials(filepath)


    cl = Client()

    # adds a random delay between 1 and 3 seconds after each request
    cl.delay_range = [DELAY_RANGE_BOTTOM, DELAY_RANGE_TOP]
    before_ip = cl._send_public_request("https://api.ipify.org/")
    cl.set_proxy(PROXY_URL)
    after_ip = cl._send_public_request("https://api.ipify.org/")

    print(before_ip)
    print(after_ip)

    # Load session if it exists locally
    session_file = "sessions/" + insta_username + "_session.json"
    if os.path.exists(session_file):
        session = cl.load_settings(session_file)
    else:
        session = None

    login_via_session = False
    login_via_pw = False

    if session:
        try:
            cl.set_settings(session)
            cl.login(username, password)

            # check if session is valid
            try:
                cl.get_timeline_feed()
            except LoginRequired:
                logger.info("Session is invalid, need to login via username and password")

                old_session = cl.get_settings()

                # use the same device uuids across logins
                cl.set_settings({})
                cl.set_uuids(old_session["uuids"])

                cl.login(username, password)
            login_via_session = True
        except Exception as e:
            logger.info("Couldn't login user using session information: %s" % e)

    if not login_via_session:
        try:
            logger.info("Attempting to login via username and password. username: %s" % username)
            if cl.login(username, password):
                login_via_pw = True
        except Exception as e:
            logger.info("Couldn't login user using username and password: %s" % e)

    if not login_via_pw and not login_via_session:
        raise Exception("Couldn't login user with either password or session")

    # Optional: Save/Update session settings after successful login
    cl.dump_settings(session_file)

    return cl

if __name__ == "__main__":
    # Initialize argument parser
    parser = argparse.ArgumentParser(description="Instagram Login Script")
    parser.add_argument("creds_file", help="Path to the JSON file containing username and password")

    # Parse arguments
    args = parser.parse_args()

    try:
        # Execute login
        client = login_user(args.creds_file)
        logger.info("Login process completed successfully.")

    except Exception as e:
        logger.error(f"Fatal error: {e}")
