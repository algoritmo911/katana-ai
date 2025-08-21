import hashlib
import logging

# Initialize logger
logger = logging.getLogger(__name__)

def generate_chronohash(temporal_source: str, event_id: str) -> str:
    """
    Generates a unique, deterministic SHA-256 hash for an event.

    The hash is based on the source of the event (e.g., 'telegram_chat', 'git_commit')
    and a unique identifier for the event itself (e.g., a timestamp + user_id, or a UUID).

    Args:
        temporal_source: A string identifying the origin of the event.
        event_id: A unique identifier for the event within its source.

    Returns:
        A SHA-256 hex digest string.
    """
    if not temporal_source or not event_id:
        logger.error("temporal_source and event_id cannot be empty for ChronoHash generation.")
        raise ValueError("temporal_source and event_id are required.")

    # Create a stable, concatenated string
    input_string = f"{temporal_source.strip()}:{event_id.strip()}"

    # Encode the string to bytes
    encoded_string = input_string.encode('utf-8')

    # Create a SHA-256 hash
    sha256_hash = hashlib.sha256(encoded_string).hexdigest()

    logger.debug(f"Generated ChronoHash '{sha256_hash}' for source '{temporal_source}' and event_id '{event_id}'")

    return sha256_hash
