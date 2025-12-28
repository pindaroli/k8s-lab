import requests
from bs4 import BeautifulSoup
import argparse
import sys
import re

# Disable SSL warnings
requests.packages.urllib3.disable_warnings()

def get_csrf_token(session, url):
    """Fetches the page and extracts the CSRF token"""
    response = session.get(url, verify=False)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # OPNsense CSRF token is usually in a meta tag or hidden input
    # Common input name is "__csrf_magic" or similar, but often it's just 'csrf_token'
    # Let's try finding the input fields in the login form first
    
    # In newer OPNsense, it might be in <script> tags or headers.
    # Let's try standard grep for the token pattern if specific input is missing
    return response

def login(session, base_url, username, password):
    login_url = f"{base_url}/"
    response = session.get(login_url, verify=False)
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find CSRF token (usually hidden input named 'csrf_magic' or similar)
    csrf_input = soup.find('input', {'id': re.compile(r'csrf')}) 
    if not csrf_input:
        # Fallback search for any hidden input with long random value
        csrf_input = soup.find('input', {'type': 'hidden'})
    
    csrf_token = csrf_input['value'] if csrf_input else None
    csrf_name = csrf_input['name'] if csrf_input else 'csrf_magic'

    login_data = {
        'usernamefld': username,
        'passwordfld': password,
        'login': 'Login'
    }
    
    if csrf_token:
        login_data[csrf_name] = csrf_token

    # Perform Login
    post_response = session.post(login_url, data=login_data, verify=False)
    
    if "Dashboard" not in post_response.text and "Logout" not in post_response.text:
       # OPNsense redirects after login usually
       pass

    return session

def update_settings(session, base_url, hostnames):
    target_url = f"{base_url}/system_advanced_admin.php"
    
    # Get the page first to load current settings and CSRF
    response = session.get(target_url, verify=False)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract all form inputs to rebuild the state (important for checkboxes!)
    form_data = {}
    for input_tag in soup.find_all('input'):
        name = input_tag.get('name')
        value = input_tag.get('value', '')
        Type = input_tag.get('type', 'text')
        
        if not name: continue
        
        # Handle specific fields we want to change
        if name == 'althostnames':
            value = hostnames
            print(f"[INFO] Setting Alternate Hostnames to: {value}")
        
        # Handle Checkboxes: OPNsense sends 'yes' if checked. 
        # We need to preserve existing state EXCEPT for rebind check
        if Type == 'checkbox':
            if input_tag.get('checked'):
                form_data[name] = 'yes'
            
            # Explicitly force Rebind Check to be UNCHECKED (Enabled protection)
            if name == 'nodnsrebindcheck':
                if name in form_data: del form_data[name] # Ensure it's not sent
                print("[INFO] Ensuring DNS Rebind Check is ENABLED (Unchecked)")
                continue 
                
        elif Type == 'submit':
             if value == 'Save':
                 form_data[name] = value
        else:
            form_data[name] = value

    # Update our specific target again to be sure
    form_data['althostnames'] = hostnames

    # Submit
    post_response = session.post(target_url, data=form_data, verify=False)
    
    if "The changes have been applied successfully" in post_response.text:
        print("[SUCCESS] Settings saved successfully.")
        return True
    else:
        print("[WARNING] Could not verify success message. Check manually.")
        return False

def main():
    parser = argparse.ArgumentParser(description='Configure OPNsense WebGUI Settings')
    parser.add_argument('--url', required=True, help='OPNsense Base URL')
    parser.add_argument('--user', required=True, help='Username')
    parser.add_argument('--password', required=True, help='Password')
    parser.add_argument('--aliases', required=True, help='Space separated list of alternate hostnames')
    
    args = parser.parse_args()
    
    session = requests.Session()
    session = login(session, args.url, args.user, args.password)
    update_settings(session, args.url, args.aliases)

if __name__ == "__main__":
    main()
