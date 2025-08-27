from collections import deque

class ChatHistory:
    def __init__(self, max_history_len: int = 10):
        """
        Initializes the chat history storage.

        Args:
            max_history_len (int): Maximum number of message pairs (user_message, bot_response)
                                   to store per session.
        """
        self.history = {}  # session_id -> deque of (user_message, bot_response) tuples
        self.max_history_len = max_history_len

    def add_message(self, session_id: str, user_message: str, bot_response: str):
        """
        Adds a user message and its corresponding bot response to the chat history
        for a given session.

        Args:
            session_id (str): Unique identifier for the chat session.
            user_message (str): The message sent by the user.
            bot_response (str): The response sent by the bot.
        """
        if session_id not in self.history:
            self.history[session_id] = deque(maxlen=self.max_history_len)

        self.history[session_id].append({
            "user": user_message,
            "bot": bot_response
        })

    def get_history(self, session_id: str) -> list[dict]:
        """
        Retrieves the conversation history for a given session.

        Args:
            session_id (str): Unique identifier for the chat session.

        Returns:
            list[dict]: A list of message pairs (dictionaries with "user" and "bot" keys),
                        or an empty list if the session has no history.
        """
        if session_id in self.history:
            return list(self.history[session_id])
        return []

    def get_formatted_history(self, session_id: str, user_prefix="User", bot_prefix="Bot") -> str:
        """
        Retrieves the conversation history for a given session, formatted as a single string.

        Args:
            session_id (str): Unique identifier for the chat session.
            user_prefix (str): Prefix for user messages.
            bot_prefix (str): Prefix for bot messages.

        Returns:
            str: A string containing the formatted conversation history,
                 or an empty string if the session has no history.
        """
        history_list = self.get_history(session_id)
        if not history_list:
            return ""

        formatted_lines = []
        for entry in history_list:
            formatted_lines.append(f"{user_prefix}: {entry['user']}")
            formatted_lines.append(f"{bot_prefix}: {entry['bot']}")
        return "\n".join(formatted_lines)

    def clear_history(self, session_id: str):
        """
        Clears the conversation history for a given session.

        Args:
            session_id (str): Unique identifier for the chat session.
        """
        if session_id in self.history:
            del self.history[session_id]
            # print(f"History for session '{session_id}' cleared.") # Optional: for debugging
        # else:
            # print(f"No history found for session '{session_id}' to clear.") # Optional: for debugging

    def get_all_session_ids(self) -> list[str]:
        """
        Retrieves all session IDs currently stored.

        Returns:
            list[str]: A list of all session_ids.
        """
        return list(self.history.keys())

if __name__ == '__main__':
    history_manager = ChatHistory(max_history_len=3)

    session_1 = "user123"
    session_2 = "user456"

    # Add messages to session 1
    history_manager.add_message(session_1, "Hello bot!", "Hi there! How can I help?")
    history_manager.add_message(session_1, "What's the weather like?", "It's sunny today.")
    history_manager.add_message(session_1, "Thanks!", "You're welcome!")

    # This message should cause the oldest one to be removed due to max_history_len=3
    history_manager.add_message(session_1, "Any news?", "Nothing major to report.")

    print(f"History for {session_1}:")
    for entry in history_manager.get_history(session_1):
        print(f"  User: {entry['user']} -> Bot: {entry['bot']}")
    print("-" * 20)

    # Add messages to session 2
    history_manager.add_message(session_2, "Hi", "Hello!")
    print(f"History for {session_2}:")
    for entry in history_manager.get_history(session_2):
        print(f"  User: {entry['user']} -> Bot: {entry['bot']}")
    print("-" * 20)

    print(f"Formatted history for {session_1}:\n{history_manager.get_formatted_history(session_1)}\n")
    print("-" * 20)

    # Test clearing history
    history_manager.clear_history(session_1)
    print(f"History for {session_1} after clearing: {history_manager.get_history(session_1)}")
    print(f"All active sessions: {history_manager.get_all_session_ids()}")

    history_manager.clear_history(session_2)
    print(f"All active sessions after clearing session_2: {history_manager.get_all_session_ids()}")

    # Test adding to a cleared session
    history_manager.add_message(session_1, "I'm back", "Welcome back!")
    print(f"History for {session_1} after re-adding: {history_manager.get_history(session_1)}")
    print(f"All active sessions: {history_manager.get_all_session_ids()}")
