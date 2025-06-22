# katana_integrations/gmail_service.py

import os
import base64
import email # For parsing email content
import email.utils # For robust date parsing
import re # For service info extraction
import json
import uuid # Added for unique message_ids

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
    # Early log for critical dependency error - will be handled by module-level logger
    pass

from katana.logging_config import get_logger, setup_logging # setup_logging for __main__
# import logging # No longer needed here

logger = get_logger(__name__)

if not GOOGLE_LIBS_AVAILABLE:
    logger.critical(
        "[GmailService:CRITICAL_DEPENDENCY_ERROR] Google API client libraries not found. " +
        "Please run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib",
        extra={'user_id': 'gmail_service_system', 'chat_id': 'dependency_check', 'message_id': 'google_libs_missing'}
    )

# --- Configuration ---
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
_SCRIPT_DIR = Path(__file__).resolve().parent
TOKEN_JSON_PATH = _SCRIPT_DIR / 'token.json'
CREDENTIALS_JSON_PATH = _SCRIPT_DIR / 'credentials.json'

# log_message_gmail function removed, using logger directly.

# --- Core Functions ---
def get_gmail_service():
    """
    Authenticates and returns the Gmail API service client.
    Manages token creation/refresh using token.json and credentials.json.
    """
    # General context for this function, message_id will be updated for specific steps
    base_op_id = str(uuid.uuid4())
    def get_context(step_id):
        return {'user_id': 'gmail_service_system', 'chat_id': 'gmail_auth', 'message_id': f'{base_op_id}_{step_id}'}

    if not GOOGLE_LIBS_AVAILABLE:
        logger.critical("Cannot proceed: Google API libraries are not installed.", extra=get_context('get_service_libs_missing'))
        return None

    creds = None
    if TOKEN_JSON_PATH.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_JSON_PATH), SCOPES)
            logger.info("Credentials loaded from token.json.", extra=get_context('load_token_success'))
        except Exception as e:
            logger.warning(f"Could not load credentials from {TOKEN_JSON_PATH}: {e}. Will attempt re-auth.", extra=get_context('load_token_fail'))
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Credentials expired. Attempting to refresh token...", extra=get_context('refresh_attempt'))
            try:
                creds.refresh(Request())
                logger.info("Token refreshed successfully.", extra=get_context('refresh_success'))
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}. Manual re-authentication required.", exc_info=True, extra=get_context('refresh_fail'))
                creds = None
        else:
            logger.info("No valid credentials found or refresh failed. Starting OAuth flow...", extra=get_context('oauth_start'))
            if not CREDENTIALS_JSON_PATH.exists():
                logger.critical(f"OAuth credentials file '{CREDENTIALS_JSON_PATH}' not found.", extra=get_context('oauth_creds_missing'))
                logger.critical(f"Download OAuth 2.0 client secrets JSON from Google Cloud Console, save as 'credentials.json' in '{_SCRIPT_DIR}'.", extra=get_context('oauth_creds_instruction'))
                return None
            try:
                flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_JSON_PATH), SCOPES)
                creds = flow.run_local_server(port=0)
                logger.info("OAuth flow completed. Credentials obtained.", extra=get_context('oauth_complete'))
            except FileNotFoundError:
                 logger.critical(f"OAuth credentials file '{CREDENTIALS_JSON_PATH}' not found during flow.from_client_secrets_file. Please check path and existence.", exc_info=True, extra=get_context('oauth_creds_flow_missing'))
                 return None
            except Exception as e:
                logger.error(f"Error during OAuth flow: {e}", exc_info=True, extra=get_context('oauth_flow_error'))
                return None

        if creds: # If OAuth flow was successful or refresh happened
            try:
                with open(TOKEN_JSON_PATH, 'w') as token_file:
                    token_file.write(creds.to_json())
                logger.info(f"Credentials saved to {TOKEN_JSON_PATH}.", extra=get_context('save_token_success'))
            except Exception as e:
                logger.error(f"Could not save credentials to {TOKEN_JSON_PATH}: {e}", exc_info=True, extra=get_context('save_token_fail'))

    if not creds or not creds.valid: # Final check
        logger.error("Failed to obtain valid credentials for Gmail API.", extra=get_context('final_creds_fail'))
        return None

    # If creds are available, try to get user email for user_id field
    user_email_for_logs = 'gmail_service_user' # Default
    try:
        if creds.id_token: # id_token is a JWT string
            # Decoding JWT is non-trivial and requires another library (e.g. google-auth a.k.a. google.oauth2.id_token.verify_oauth2_token)
            # For simplicity, we won't decode it here to extract email.
            # A more robust solution would verify and decode the token.
            # If creds.service_account_email exists (for service accounts), that could be used.
            # Or, after building service, make a call to users.getProfile.
            # For now, we'll use a generic user_id or one derived if easily available.
            # Example: if creds object has an email attribute directly (it usually doesn't for user creds)
            if hasattr(creds, 'email') and creds.email:
                 user_email_for_logs = creds.email
            pass
    except Exception: #pylint: disable=broad-except
        pass # Best effort to get user email, don't fail auth for this logging detail.

    final_build_context = {'user_id': user_email_for_logs, 'chat_id': 'gmail_auth', 'message_id': f'{base_op_id}_build_service'}

    try:
        service = build('gmail', 'v1', credentials=creds)
        logger.info("Gmail API service client built successfully.", extra=final_build_context)
        return service
    except HttpError as error:
        logger.error(f"An error occurred building Gmail service: {error}", extra=final_build_context)
    except Exception as e:
        logger.error(f"An unexpected error occurred building Gmail service: {e}", exc_info=True, extra=final_build_context)
    return None

def list_emails(service, query_params: str = '', max_results: int = 10, user_id='me'):
    """Lists emails matching the query."""
    if not service: return []
    op_id = str(uuid.uuid4())
    # Assuming 'user_id' parameter to this function is the Google User ID ('me' or actual ID)
    # For logging, we might use a more specific internal user if available, or this passed 'user_id'
    log_context = {'user_id': user_id, 'chat_id': 'gmail_ops', 'message_id': op_id}

    try:
        logger.info(f"Listing emails with query: '{query_params}', max_results: {max_results}, for user: {user_id}", extra=log_context)
        results = service.users().messages().list(userId=user_id, q=query_params, maxResults=max_results).execute()
        messages = results.get('messages', [])
        logger.info(f"Found {len(messages)} email(s) matching query for user: {user_id}.", extra=log_context)
        return messages
    except HttpError as error:
        logger.error(f"HttpError listing emails for user {user_id}: {error}", extra=log_context)
    except Exception as e:
        logger.error(f"Error listing emails for user {user_id}: {e}", exc_info=True, extra=log_context)
    return []

def get_email_details(service, message_id: str, user_id='me', format='full'):
    """Gets detailed information for a single email."""
    if not service: return None
    # Use the actual Gmail message_id as the message_id for this log event if desired, or generate a new op_id.
    # Using a new op_id for consistency of operation tracking.
    op_id = str(uuid.uuid4())
    log_context = {'user_id': user_id, 'chat_id': 'gmail_ops',
                   'message_id': op_id, 'gmail_message_id': message_id} # Add actual gmail id for context

    try:
        logger.debug(f"Fetching details for email ID: {message_id} (user: {user_id}, format: {format})", extra=log_context)
        message = service.users().messages().get(userId=user_id, id=message_id, format=format).execute()
        return message
    except HttpError as error:
        logger.error(f"HttpError getting email details for ID {message_id} (user: {user_id}): {error}", extra=log_context)
    except Exception as e:
        logger.error(f"Error getting email details for ID {message_id} (user: {user_id}): {e}", exc_info=True, extra=log_context)
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
                    # Context for this specific warning inside parsing
                    parse_date_ctx = {'user_id': 'gmail_parser', 'chat_id': 'email_parsing',
                                      'message_id': f'parse_date_none_{info.get("id", "unknown_email")}'}
                    logger.warning(f"email.utils.parsedate_to_datetime returned None for date: '{value}'", extra=parse_date_ctx)
            except Exception as e_date:
                parse_date_err_ctx = {'user_id': 'gmail_parser', 'chat_id': 'email_parsing',
                                      'message_id': f'parse_date_error_{info.get("id", "unknown_email")}'}
                logger.warning(f"Could not parse date string '{value}' to datetime object: {e_date}", exc_info=True, extra=parse_date_err_ctx)

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
    setup_logging(log_level=logging.INFO) # Setup logging for this example run

    main_op_id = f"gmail_main_example_{datetime.utcnow().timestamp()}"
    main_context = {'user_id': 'gmail_service_main', 'chat_id': 'example_run', 'message_id': main_op_id}

    logger.info("Starting Gmail Service example (with enhanced parsing)...", extra=main_context)
    gmail_service = get_gmail_service() # This function has its own detailed logging

    if gmail_service:
        # list_emails and get_email_details have their own logging.
        # This block is for orchestrating and providing summary logs for the example run.
        messages = list_emails(gmail_service, query_params='in:inbox category:primary', max_results=5)

        if not messages:
            logger.info("No emails found by list_emails.", extra=main_context)
        else:
            logger.info(f"Processing {len(messages)} email(s) for example...", extra=main_context)
            for msg_summary in messages:
                email_id = msg_summary['id']
                # Context for processing a specific email in the example
                email_process_context = {**main_context, 'message_id': f"{main_op_id}_process_{email_id}"}
                logger.info(f"--- Example processing for Email ID: {email_id} ---", extra=email_process_context)

                email_details_full = get_email_details(gmail_service, email_id, format='full')
                if email_details_full:
                    parsed_common_info = parse_common_info_from_email_message(email_details_full)
                    if parsed_common_info:
                        print(f"  Subject: {parsed_common_info.get('subject')}")
                        # ... (other print statements for console output remain unchanged) ...
                        print(f"  Date (ISO UTC): {parsed_common_info.get('date_received_utc_iso')}")

                        service_info = extract_service_info_from_email(parsed_common_info)
                        if service_info:
                            print(f"  >>>> Detected Service Info <<<<")
                            # ... (print statements for service_info) ...
                            print(f"    Username: {service_info.get('mentioned_username')}")
                        else:
                            print(f"  No specific service registration/activity detected in this email.")
                    else:
                        logger.warning(f"Could not parse common info for email {email_id}", extra=email_process_context)
                else:
                    logger.warning(f"Could not retrieve full details for email {email_id}", extra=email_process_context)
                print("------------------------------------")
    else:
        logger.critical("Could not initialize Gmail service for example run.", extra=main_context)
