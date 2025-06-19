# katana_integrations/gmail_service.py

import os
import base64
import email # For parsing email content
import email.utils # For robust date parsing
import re # For service info extraction
import json

from pathlib import Path
from datetime import datetime, timezone

# Google API Client Libraries - User needs to install these:
# pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_LIBS_AVAILABLE = True
except ImportError:
    GOOGLE_LIBS_AVAILABLE = False
    print("[GmailService:CRITICAL_DEPENDENCY_ERROR] Google API client libraries not found. " + \
          "Please run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")

# --- Configuration ---
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
_SCRIPT_DIR = Path(__file__).resolve().parent
TOKEN_JSON_PATH = _SCRIPT_DIR / 'token.json'
CREDENTIALS_JSON_PATH = _SCRIPT_DIR / 'credentials.json'

# --- Logging Helper ---
def log_message_gmail(level, message):
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    print(f"[{timestamp}] [GmailService:{level.upper()}] {message}")

# --- Core Functions ---
def get_gmail_service():
    """
    Authenticates and returns the Gmail API service client.
    Manages token creation/refresh using token.json and credentials.json.
    """
    if not GOOGLE_LIBS_AVAILABLE:
        log_message_gmail("critical", "Cannot proceed: Google API libraries are not installed.")
        return None
    creds = None
    if TOKEN_JSON_PATH.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_JSON_PATH), SCOPES)
            log_message_gmail("info", "Credentials loaded from token.json.")
        except Exception as e:
            log_message_gmail("warning", f"Could not load credentials from {TOKEN_JSON_PATH}: {e}. Will attempt re-auth.")
            creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            log_message_gmail("info", "Credentials expired. Attempting to refresh token...")
            try:
                creds.refresh(Request())
                log_message_gmail("info", "Token refreshed successfully.")
            except Exception as e:
                log_message_gmail("error", f"Failed to refresh token: {e}. Manual re-authentication required.")
                creds = None
        else:
            log_message_gmail("info", "No valid credentials found or refresh failed. Starting OAuth flow...")
            if not CREDENTIALS_JSON_PATH.exists():
                log_message_gmail("critical", f"OAuth credentials file '{CREDENTIALS_JSON_PATH}' not found.")
                log_message_gmail("critical", f"Download OAuth 2.0 client secrets JSON from Google Cloud Console, save as 'credentials.json' in '{_SCRIPT_DIR}'.")
                return None
            try:
                flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_JSON_PATH), SCOPES)
                creds = flow.run_local_server(port=0)
                log_message_gmail("info", "OAuth flow completed. Credentials obtained.")
            except FileNotFoundError:
                 log_message_gmail("critical", f"OAuth credentials file '{CREDENTIALS_JSON_PATH}' not found during flow.from_client_secrets_file. Please check path and existence.")
                 return None
            except Exception as e:
                log_message_gmail("error", f"Error during OAuth flow: {e}")
                return None
        if creds:
            try:
                with open(TOKEN_JSON_PATH, 'w') as token_file:
                    token_file.write(creds.to_json())
                log_message_gmail("info", f"Credentials saved to {TOKEN_JSON_PATH}.")
            except Exception as e:
                log_message_gmail("error", f"Could not save credentials to {TOKEN_JSON_PATH}: {e}")
    if not creds or not creds.valid:
        log_message_gmail("error", "Failed to obtain valid credentials for Gmail API.")
        return None
    try:
        service = build('gmail', 'v1', credentials=creds)
        log_message_gmail("info", "Gmail API service client built successfully.")
        return service
    except HttpError as error:
        log_message_gmail("error", f"An error occurred building Gmail service: {error}")
    except Exception as e:
        log_message_gmail("error", f"An unexpected error occurred building Gmail service: {e}")
    return None

def list_emails(service, query_params: str = '', max_results: int = 10, user_id='me'):
    """Lists emails matching the query."""
    if not service: return []
    try:
        log_message_gmail("info", f"Listing emails with query: '{query_params}', max_results: {max_results}")
        results = service.users().messages().list(userId=user_id, q=query_params, maxResults=max_results).execute()
        messages = results.get('messages', [])
        log_message_gmail("info", f"Found {len(messages)} email(s) matching query.")
        return messages
    except HttpError as error:
        log_message_gmail("error", f"HttpError listing emails: {error}")
    except Exception as e:
        log_message_gmail("error", f"Error listing emails: {e}")
    return []

def get_email_details(service, message_id: str, user_id='me', format='full'):
    """Gets detailed information for a single email."""
    if not service: return None
    try:
        log_message_gmail("debug", f"Fetching details for email ID: {message_id} with format: {format}")
        message = service.users().messages().get(userId=user_id, id=message_id, format=format).execute()
        return message
    except HttpError as error:
        log_message_gmail("error", f"HttpError getting email details for ID {message_id}: {error}")
    except Exception as e:
        log_message_gmail("error", f"Error getting email details for ID {message_id}: {e}")
    return None

def parse_email_body_from_payload(payload): # Original simpler version
    """Parses the email body from the payload, handling multipart messages."""
    if 'parts' in payload:
        parts = payload['parts']
        body_parts = []
        for part in parts:
            mime_type = part.get('mimeType', '').lower()
            if mime_type == 'text/plain':
                data = part.get('body', {}).get('data')
                if data:
                    body_parts.append(base64.urlsafe_b64decode(data).decode('utf-8', errors='replace'))
            elif mime_type == 'text/html':
                pass
            elif 'parts' in part:
                nested_body = parse_email_body_from_payload(part)
                if nested_body:
                    body_parts.append(nested_body)
        return "\\n---\\n".join(body_parts) if body_parts else None
    elif payload.get('mimeType', '').lower() == 'text/plain' and payload.get('body', {}).get('data'):
        return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='replace')
    return None

def parse_common_info_from_email_message(email_data: dict):
    """
    Parses common information (Subject, From, To, Date, Snippet, Body) from a Gmail message resource.
    email_data: The result of service.users().messages().get().execute()
    """
    if not email_data: return None

    info = {
        'id': email_data.get('id'),
        'threadId': email_data.get('threadId'),
        'snippet': email_data.get('snippet'),
        'subject': None,
        'from_address': None,
        'to_addresses': [],
        'cc_addresses': [],
        'bcc_addresses': [],
        'date_received_utc_iso': None,
        'raw_date_string': None,
        'body_text': None,
        'labels': email_data.get('labelIds', [])
    }

    headers = email_data.get('payload', {}).get('headers', [])
    for header in headers:
        name = header.get('name', '').lower()
        value = header.get('value', '')
        if name == 'subject':
            info['subject'] = value
        elif name == 'from':
            info['from_address'] = value
        elif name == 'to':
            info['to_addresses'] = [addr.strip() for addr in value.split(',')] if value else []
        elif name == 'cc':
            info['cc_addresses'] = [addr.strip() for addr in value.split(',')] if value else []
        elif name == 'bcc':
            info['bcc_addresses'] = [addr.strip() for addr in value.split(',')] if value else []
        elif name == 'date':
            info['raw_date_string'] = value
            try:
                dt_obj = email.utils.parsedate_to_datetime(value)
                if dt_obj:
                    info['date_received_utc_iso'] = dt_obj.astimezone(timezone.utc).isoformat()
                else:
                    log_message_gmail("warning", f"email.utils.parsedate_to_datetime returned None for date: '{value}'")
            except Exception as e_date:
                log_message_gmail("warning", f"Could not parse date string '{value}' to datetime object: {e_date}")

    payload = email_data.get('payload')
    if payload:
        info['body_text'] = parse_email_body_from_payload(payload)

    return info

# --- Service Info Extraction from Email ---
def extract_service_info_from_email(parsed_email_info: dict):
    """
    Attempts to extract service registration/activity information from parsed email info.
    Returns a dictionary with extracted service info or None.
    """
    if not parsed_email_info or not isinstance(parsed_email_info, dict):
        return None

    subject = parsed_email_info.get('subject', '').lower()
    body = parsed_email_info.get('body_text', '').lower() if parsed_email_info.get('body_text') else ""
    from_address = parsed_email_info.get('from_address', '').lower()

    registration_keywords = [
        "welcome to", "confirm your email", "verify your account", "account created",
        "getting started", "your new account", "sign up complete", "registration successful",
        "activate your account", "trial started", "subscription confirmed"
    ]

    url_pattern = re.compile(r'https?://[\w\d./?=#&%-]+')

    service_name = None
    action_url = None
    mentioned_username = None
    email_type = "unknown"

    text_to_search = subject + " " + body[:1000]

    for keyword in registration_keywords:
        if keyword in text_to_search:
            email_type = "registration_confirmation"
            match_welcome = re.search(r"welcome to ([\w\s.-]+)(!|,|\.|\n)", subject + " " + body[:200], re.IGNORECASE)
            if match_welcome:
                service_name = match_welcome.group(1).strip().replace("your new", "").replace("your", "").strip()
                service_name = service_name.split(" account")[0].split(" services")[0].strip()
            break

    if not service_name and from_address:
        domain_match = re.search(r"@([\w\d.-]+)", from_address)
        if domain_match:
            full_domain = domain_match.group(1)
            parts = full_domain.split('.')
            if len(parts) >= 2:
                potential_name = parts[-2] if len(parts) > 1 else parts[0]
                if potential_name not in ["google", "googlemail", "gmail", "outlook", "hotmail", "microsoft", "amazon", "aws"]:
                     service_name = potential_name.capitalize()

    urls = url_pattern.findall(body)
    if urls:
        for url in urls:
            if any(kw_url in url.lower() for kw_url in ["confirm", "verify", "activate", "validate", "complete_registration"]):
                action_url = url
                break
        if not action_url and email_type == "registration_confirmation" and urls:
            action_url = urls[0]

    username_match = re.search(r"(?:username|user ID|login ID)[:\s]+([\w\d.@_-]+)", body, re.IGNORECASE)
    if username_match:
        mentioned_username = username_match.group(1)

    if service_name or action_url or (email_type != "unknown" and mentioned_username):
        return {
            "detected_service_name": service_name,
            "detected_email_type": email_type,
            "action_url": action_url,
            "mentioned_username": mentioned_username,
            "source_email_id": parsed_email_info.get('id'),
            "source_email_subject": parsed_email_info.get('subject')
        }
    return None

# --- Main Execution (Example Usage) ---
if __name__ == '__main__':
    import traceback
    log_message_gmail("info", "Starting Gmail Service example (with enhanced parsing)...")
    gmail_service = get_gmail_service()

    if gmail_service:
        messages = list_emails(gmail_service, query_params='in:inbox category:primary', max_results=5)

        if not messages:
            log_message_gmail("info", "No emails found.")
        else:
            log_message_gmail("info", f"Processing {len(messages)} email(s):")
            for msg_summary in messages:
                email_id = msg_summary['id']
                log_message_gmail("info", f"--- Email ID: {email_id} ---")

                email_details_full = get_email_details(gmail_service, email_id, format='full')
                if email_details_full:
                    parsed_common_info = parse_common_info_from_email_message(email_details_full)
                    if parsed_common_info:
                        print(f"  Subject: {parsed_common_info.get('subject')}")
                        print(f"  From: {parsed_common_info.get('from_address')}")
                        print(f"  To: {parsed_common_info.get('to_addresses')}")
                        print(f"  CC: {parsed_common_info.get('cc_addresses')}")
                        print(f"  BCC: {parsed_common_info.get('bcc_addresses')}")
                        print(f"  Date (Raw): {parsed_common_info.get('raw_date_string')}")
                        print(f"  Date (ISO UTC): {parsed_common_info.get('date_received_utc_iso')}")

                        service_info = extract_service_info_from_email(parsed_common_info)
                        if service_info:
                            print(f"  >>>> Detected Service Info <<<<")
                            print(f"    Service Name: {service_info.get('detected_service_name')}")
                            print(f"    Email Type: {service_info.get('detected_email_type')}")
                            print(f"    Action URL: {service_info.get('action_url')}")
                            print(f"    Username: {service_info.get('mentioned_username')}")
                        else:
                            print(f"  No specific service registration/activity detected in this email.")
                    else:
                        log_message_gmail("warning", f"Could not parse common info for email {email_id}")
                else:
                    log_message_gmail("warning", f"Could not retrieve full details for email {email_id}")
                print("------------------------------------")
    else:
        log_message_gmail("critical", "Could not initialize Gmail service.")
