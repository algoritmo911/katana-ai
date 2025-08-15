# This file makes the processors directory a Python package.
# It can also be used to expose a simpler API for the processors.

from .voice import process_voice_message
from .video import process_video_note
