import unittest
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Any
import statistics # Required for stddev if calculated manually for verification

# Добавляем путь к src, чтобы можно было импортировать модули из src
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from monitoring.fatigue_analyzer.schemas import MessageInput
from monitoring.fatigue_analyzer import metrics as fatigue_metrics

TEST_ROLE_USER = "user"
TEST_ROLE_ASSISTANT = "assistant"


class TestFatigueMetrics(unittest.TestCase):

    def assertAlmostOptionalEqual(self, a: Optional[float], b: Optional[float], places: int = 7, msg: Any = None):
        if a is None and b is None:
            return
        if a is None or b is None:
            standard_msg = f"One value is None and the other is not: {a} vs {b}"
            raise AssertionError(standard_msg + (f". {msg}" if msg else ""))
        self.assertAlmostEqual(a, b, places=places, msg=msg)

    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.messages_fixture: List[MessageInput] = [
            MessageInput(role=TEST_ROLE_USER, content="Привет", timestamp=self.now - timedelta(minutes=60)),
            MessageInput(role=TEST_ROLE_ASSISTANT, content="Привет! Чем могу помочь?", timestamp=self.now - timedelta(minutes=59, seconds=30)),
            MessageInput(role=TEST_ROLE_USER, content="Расскажи анекдот", timestamp=self.now - timedelta(minutes=59)), # Reaction 1: 30s
            MessageInput(role=TEST_ROLE_ASSISTANT, content="Колобок повесился.", timestamp=self.now - timedelta(minutes=58)),
            MessageInput(role=TEST_ROLE_USER, content="Смешно. А другой?", timestamp=self.now - timedelta(minutes=50)), # Reaction 2: 480s
            MessageInput(role=TEST_ROLE_ASSISTANT, content="Почему курица перешла дорогу?", timestamp=self.now - timedelta(minutes=49)),
            MessageInput(role=TEST_ROLE_USER, content="/mind_clearing", timestamp=self.now - timedelta(minutes=40)), # Reaction 3: 540s. Switch command.
            MessageInput(role=TEST_ROLE_ASSISTANT, content="Контекст очищен.", timestamp=self.now - timedelta(minutes=39)),
            MessageInput(role=TEST_ROLE_USER, content="Какая погода?", timestamp=self.now - timedelta(minutes=8)), # Reaction 4: 1860s
            MessageInput(role=TEST_ROLE_ASSISTANT, content="Солнечно, +25C.", timestamp=self.now - timedelta(minutes=7)),
            MessageInput(role=TEST_ROLE_USER, content="Спасибо", timestamp=self.now - timedelta(minutes=6)), # Reaction 5: 60s
            MessageInput(role=TEST_ROLE_ASSISTANT, content="Пожалуйста!", timestamp=self.now - timedelta(minutes=5)),
            MessageInput(role=TEST_ROLE_USER, content="Что-то пошло не так, ошибка!", timestamp=self.now - timedelta(minutes=4)), # Reaction 6: 60s
            MessageInput(role=TEST_ROLE_ASSISTANT, content="Произошла ошибка при обработке вашего запроса.", timestamp=self.now - timedelta(minutes=3)), # Error bot message
            MessageInput(role=TEST_ROLE_USER, content="/cancel", timestamp=self.now - timedelta(minutes=2)), # Reaction 7: 60s. Switch command. (Changed from "Хорошо, попробую позже /cancel")
        ]
        self.empty_messages: List[MessageInput] = []
        self.user_only_messages: List[MessageInput] = [
            MessageInput(role=TEST_ROLE_USER, content="Test 1", timestamp=self.now - timedelta(minutes=2)),
            MessageInput(role=TEST_ROLE_USER, content="Test 2", timestamp=self.now - timedelta(minutes=1)),
        ]
        self.bot_only_messages: List[MessageInput] = [
            MessageInput(role=TEST_ROLE_ASSISTANT, content="Test 1", timestamp=self.now - timedelta(minutes=2)),
            MessageInput(role=TEST_ROLE_ASSISTANT, content="Test 2", timestamp=self.now - timedelta(minutes=1)),
        ]

    def test_get_user_messages(self):
        self.assertEqual(fatigue_metrics.ROLE_USER, "user")
        self.assertEqual(fatigue_metrics.ROLE_ASSISTANT, "assistant")
        user_msgs = fatigue_metrics.get_user_messages(self.messages_fixture)
        self.assertEqual(len(user_msgs), 8) # Counted manually: 8 user messages
        for msg in user_msgs:
            self.assertEqual(msg.role, TEST_ROLE_USER)

    def test_get_assistant_messages(self):
        assistant_msgs = fatigue_metrics.get_assistant_messages(self.messages_fixture)
        self.assertEqual(len(assistant_msgs), 7) # Counted manually: 7 assistant messages
        for msg in assistant_msgs:
            self.assertEqual(msg.role, TEST_ROLE_ASSISTANT)

    def test_calculate_command_frequency(self):
        self.assertEqual(fatigue_metrics.calculate_command_frequency(self.messages_fixture, 5, current_time=self.now), 2)
        self.assertEqual(fatigue_metrics.calculate_command_frequency(self.messages_fixture, 10, current_time=self.now), 4)
        self.assertEqual(fatigue_metrics.calculate_command_frequency(self.messages_fixture, 60, current_time=self.now), 8)
        self.assertEqual(fatigue_metrics.calculate_command_frequency(self.messages_fixture, 5), 3) # Uses end_time of last message
        self.assertEqual(fatigue_metrics.calculate_command_frequency(self.empty_messages, 5, current_time=self.now), 0)
        self.assertEqual(fatigue_metrics.calculate_command_frequency(self.bot_only_messages, 5, current_time=self.now), 0)

    def test_calculate_reaction_times(self):
        # Reaction times based on corrected fixture and trace:
        # 30, 480, 540, 1860, 60, 60, 60
        expected_reactions = [30.0, 480.0, 540.0, 1860.0, 60.0, 60.0, 60.0]
        expected_avg_rt = statistics.mean(expected_reactions) # 3090 / 7 = 441.42857142857144
        expected_med_rt = statistics.median(expected_reactions) # 60.0
        expected_std_rt = statistics.stdev(expected_reactions) # approx 675.2757

        avg_rt, med_rt, std_rt = fatigue_metrics.calculate_reaction_times(self.messages_fixture)
        self.assertAlmostOptionalEqual(avg_rt, expected_avg_rt, places=5)
        self.assertAlmostOptionalEqual(med_rt, expected_med_rt, places=5)
        self.assertAlmostOptionalEqual(std_rt, expected_std_rt, places=5)

        avg_rt_empty, med_rt_empty, std_rt_empty = fatigue_metrics.calculate_reaction_times(self.empty_messages)
        self.assertIsNone(avg_rt_empty)
        self.assertIsNone(med_rt_empty)
        self.assertIsNone(std_rt_empty)

        avg_rt_uo, _, _ = fatigue_metrics.calculate_reaction_times(self.user_only_messages)
        self.assertIsNone(avg_rt_uo)

    def test_calculate_error_rate(self):
        # messages_fixture has 1 assistant error message out of 7 assistant messages.
        self.assertAlmostEqual(fatigue_metrics.calculate_error_rate(self.messages_fixture), 1/7)
        custom_keywords = ["сбой", "problem"]
        messages_with_custom_errors: List[MessageInput] = [
            MessageInput(role=TEST_ROLE_ASSISTANT, content="У нас технический сбой.", timestamp=self.now),
            MessageInput(role=TEST_ROLE_ASSISTANT, content="Все хорошо.", timestamp=self.now),
            MessageInput(role=TEST_ROLE_ASSISTANT, content="There is a problem.", timestamp=self.now),
        ]
        self.assertAlmostEqual(fatigue_metrics.calculate_error_rate(messages_with_custom_errors, bot_error_keywords=custom_keywords), 2/3)
        self.assertAlmostEqual(fatigue_metrics.calculate_error_rate(self.empty_messages), 0.0)
        self.assertAlmostEqual(fatigue_metrics.calculate_error_rate(self.user_only_messages), 0.0)

    def test_calculate_session_duration(self):
        start = self.now - timedelta(hours=1)
        end = self.now
        self.assertAlmostEqual(fatigue_metrics.calculate_session_duration(start, end), 60.0)
        start_tz_naive = datetime(2023, 1, 1, 10, 0, 0)
        end_tz_naive = datetime(2023, 1, 1, 10, 30, 0)
        self.assertAlmostEqual(fatigue_metrics.calculate_session_duration(start_tz_naive, end_tz_naive), 30.0)

    def test_calculate_context_switch_frequency(self):
        # Fixture updated: msg[6] is "/mind_clearing", msg[14] is "/cancel"
        # Both are exact matches to DEFAULT_USER_SWITCH_COMMANDS
        self.assertEqual(fatigue_metrics.calculate_context_switch_frequency(self.messages_fixture), 2)
        custom_switches = ["/reset_dialog", "restart please"]
        messages_with_custom_switches: List[MessageInput] = [
            MessageInput(role=TEST_ROLE_USER, content="/reset_dialog", timestamp=self.now),
            MessageInput(role=TEST_ROLE_USER, content="restart please", timestamp=self.now),
            MessageInput(role=TEST_ROLE_USER, content="Some other text", timestamp=self.now),
        ]
        self.assertEqual(fatigue_metrics.calculate_context_switch_frequency(messages_with_custom_switches, switch_commands=custom_switches), 2)
        self.assertEqual(fatigue_metrics.calculate_context_switch_frequency(self.empty_messages), 0)
        self.assertEqual(fatigue_metrics.calculate_context_switch_frequency(self.bot_only_messages), 0)

    def test_calculate_user_bot_ratio(self):
        ratio, warning = fatigue_metrics.calculate_user_bot_ratio(self.messages_fixture)
        self.assertAlmostOptionalEqual(ratio, 8/7)
        self.assertFalse(warning)

        ratio_uo, warning_uo = fatigue_metrics.calculate_user_bot_ratio(self.user_only_messages)
        self.assertEqual(ratio_uo, float('inf'))
        self.assertFalse(warning_uo)

        ratio_bo, warning_bo = fatigue_metrics.calculate_user_bot_ratio(self.bot_only_messages)
        self.assertAlmostOptionalEqual(ratio_bo, 0.0)
        self.assertFalse(warning_bo)

        ratio_empty, warning_empty = fatigue_metrics.calculate_user_bot_ratio(self.empty_messages)
        self.assertIsNone(ratio_empty)
        self.assertFalse(warning_empty)

        warning_messages: List[MessageInput] = [
            MessageInput(role=TEST_ROLE_USER, content="1", timestamp=self.now),
            MessageInput(role=TEST_ROLE_USER, content="2", timestamp=self.now),
            MessageInput(role=TEST_ROLE_ASSISTANT, content="bot", timestamp=self.now),
            MessageInput(role=TEST_ROLE_USER, content="3", timestamp=self.now),
            MessageInput(role=TEST_ROLE_USER, content="4", timestamp=self.now),
        ]
        ratio_w, warning_w = fatigue_metrics.calculate_user_bot_ratio(warning_messages)
        self.assertAlmostOptionalEqual(ratio_w, 4.0)
        self.assertTrue(warning_w)

        not_enough_messages_for_warning: List[MessageInput] = [
             MessageInput(role=TEST_ROLE_USER, content="1", timestamp=self.now),
             MessageInput(role=TEST_ROLE_ASSISTANT, content="bot", timestamp=self.now),
             MessageInput(role=TEST_ROLE_USER, content="2", timestamp=self.now),
             MessageInput(role=TEST_ROLE_USER, content="3", timestamp=self.now),
        ]
        ratio_ne, warning_ne = fatigue_metrics.calculate_user_bot_ratio(not_enough_messages_for_warning)
        self.assertAlmostOptionalEqual(ratio_ne, 3.0)
        self.assertFalse(warning_ne)

    def test_calculate_fatigue_score(self):
        metrics_low = {
            "average_reaction_time_sec": 10.0, "error_rate": 0.05, "context_switches": 0,
            "user_bot_message_ratio": 1.0, "command_frequency_10m": 3
        }
        score_low = fatigue_metrics.calculate_fatigue_score(metrics_low)
        self.assertAlmostOptionalEqual(score_low, 0.0675, places=4)

        metrics_high = {
            "average_reaction_time_sec": 70.0, "error_rate": 0.5, "context_switches": 3,
            "user_bot_message_ratio": 3.5, "command_frequency_10m": 20
        }
        score_high = fatigue_metrics.calculate_fatigue_score(metrics_high)
        self.assertAlmostOptionalEqual(score_high, 0.825, places=4)

        metrics_mixed = {
            "average_reaction_time_sec": 25.0, "error_rate": 0.1, "context_switches": 1,
            "user_bot_message_ratio": 1.8, "command_frequency_10m": 10
        }
        score_mixed = fatigue_metrics.calculate_fatigue_score(metrics_mixed)
        self.assertAlmostOptionalEqual(score_mixed, 0.365, places=4)

        metrics_missing = {"error_rate": 0.2, "context_switches": 1}
        score_missing = fatigue_metrics.calculate_fatigue_score(metrics_missing)
        self.assertAlmostOptionalEqual(score_missing, 0.13 / 0.55, places=4)

        self.assertIsNone(fatigue_metrics.calculate_fatigue_score({}))

        metrics_with_none = {
            "average_reaction_time_sec": None, "error_rate": 0.1, "context_switches": None,
            "user_bot_message_ratio": 2.0, "command_frequency_10m": 8
        }
        # Expected normalized: err=0.1, ub_ratio=(2-1.5)/1.5 = 0.3333, cmd_freq=(8-5)/10 = 0.3
        # Weights: err=0.35, ub=0.10, cmd=0.10. Total active weight = 0.55
        # Score_num = (0.1*0.35) + (0.333333*0.10) + (0.3*0.10) = 0.035 + 0.0333333 + 0.03 = 0.0983333
        # Final = 0.0983333 / 0.55 = 0.178787
        expected_score_with_none = (0.1 * 0.35 + ((2.0 - 1.5) / 1.5) * 0.10 + ((8.0 - 5.0) / 10.0) * 0.10) / (0.35 + 0.10 + 0.10)
        score_with_none = fatigue_metrics.calculate_fatigue_score(metrics_with_none)
        self.assertAlmostOptionalEqual(score_with_none, expected_score_with_none, places=4)

if __name__ == '__main__':
    unittest.main()
