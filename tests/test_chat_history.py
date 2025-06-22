import unittest
from bot.memory.chat_history import ChatHistory

class TestChatHistory(unittest.TestCase):

    def setUp(self):
        self.history_manager = ChatHistory(max_history_len=3)
        self.session_id_1 = "user1"
        self.session_id_2 = "user2"

    def test_add_and_get_messages(self):
        self.history_manager.add_message(self.session_id_1, "Hello", "Hi there!")
        self.history_manager.add_message(self.session_id_1, "How are you?", "I'm fine, thanks!")

        history = self.history_manager.get_history(self.session_id_1)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0], {"user": "Hello", "bot": "Hi there!"})
        self.assertEqual(history[1], {"user": "How are you?", "bot": "I'm fine, thanks!"})

    def test_get_history_unknown_session(self):
        history = self.history_manager.get_history("unknown_user")
        self.assertEqual(history, [])

    def test_max_history_length(self):
        self.history_manager.add_message(self.session_id_1, "Msg1_user", "Msg1_bot")
        self.history_manager.add_message(self.session_id_1, "Msg2_user", "Msg2_bot")
        self.history_manager.add_message(self.session_id_1, "Msg3_user", "Msg3_bot")
        # At this point, history is full (max_len=3)

        # Adding another message should discard the oldest one ("Msg1")
        self.history_manager.add_message(self.session_id_1, "Msg4_user", "Msg4_bot")

        history = self.history_manager.get_history(self.session_id_1)
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0], {"user": "Msg2_user", "bot": "Msg2_bot"})
        self.assertEqual(history[1], {"user": "Msg3_user", "bot": "Msg3_bot"})
        self.assertEqual(history[2], {"user": "Msg4_user", "bot": "Msg4_bot"})

    def test_clear_history(self):
        self.history_manager.add_message(self.session_id_1, "Temporary message", "Temp response")
        self.history_manager.clear_history(self.session_id_1)
        history = self.history_manager.get_history(self.session_id_1)
        self.assertEqual(history, [])
        self.assertNotIn(self.session_id_1, self.history_manager.get_all_session_ids())

    def test_clear_history_unknown_session(self):
        # Clearing a non-existent session should not raise an error
        try:
            self.history_manager.clear_history("unknown_user_to_clear")
        except Exception as e:
            self.fail(f"clear_history raised an exception for unknown session: {e}")
        # Ensure other sessions are not affected
        self.history_manager.add_message(self.session_id_1, "Test", "Test response")
        self.assertTrue(len(self.history_manager.get_history(self.session_id_1)) > 0)


    def test_multiple_sessions(self):
        self.history_manager.add_message(self.session_id_1, "User1: Hi", "Bot: Hello User1")
        self.history_manager.add_message(self.session_id_2, "User2: Hey", "Bot: Hi User2")

        history1 = self.history_manager.get_history(self.session_id_1)
        self.assertEqual(len(history1), 1)
        self.assertEqual(history1[0]["user"], "User1: Hi")

        history2 = self.history_manager.get_history(self.session_id_2)
        self.assertEqual(len(history2), 1)
        self.assertEqual(history2[0]["user"], "User2: Hey")

        self.assertIn(self.session_id_1, self.history_manager.get_all_session_ids())
        self.assertIn(self.session_id_2, self.history_manager.get_all_session_ids())
        self.assertEqual(len(self.history_manager.get_all_session_ids()), 2)

    def test_formatted_history(self):
        self.history_manager.add_message(self.session_id_1, "Hello", "Hi there!")
        self.history_manager.add_message(self.session_id_1, "How are you?", "I'm fine, thanks!")

        expected_format = "User: Hello\nBot: Hi there!\nUser: How are you?\nBot: I'm fine, thanks!"
        self.assertEqual(self.history_manager.get_formatted_history(self.session_id_1), expected_format)

    def test_formatted_history_custom_prefixes(self):
        self.history_manager.add_message(self.session_id_1, "Question", "Answer")
        expected_format = "You: Question\nAssistant: Answer"
        self.assertEqual(self.history_manager.get_formatted_history(self.session_id_1, user_prefix="You", bot_prefix="Assistant"), expected_format)

    def test_formatted_history_empty(self):
        self.assertEqual(self.history_manager.get_formatted_history("non_existent_session"), "")

    def test_max_history_len_zero_or_one(self):
        # Test with max_history_len = 1
        history_manager_one = ChatHistory(max_history_len=1)
        history_manager_one.add_message(self.session_id_1, "Msg1_user", "Msg1_bot")
        history_manager_one.add_message(self.session_id_1, "Msg2_user", "Msg2_bot")
        history = history_manager_one.get_history(self.session_id_1)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0], {"user": "Msg2_user", "bot": "Msg2_bot"})

        # Test with max_history_len = 0 (should effectively store nothing user-visible, or behave like 1 based on deque impl)
        # Deque with maxlen=0 will be empty.
        history_manager_zero = ChatHistory(max_history_len=0)
        history_manager_zero.add_message(self.session_id_1, "Msg1_user", "Msg1_bot")
        history = history_manager_zero.get_history(self.session_id_1)
        self.assertEqual(len(history), 0)


if __name__ == '__main__':
    unittest.main()
