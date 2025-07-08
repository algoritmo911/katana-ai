import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone

# Add project root to sys.path to allow direct import of src modules
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent # src/tests/test_reporter.py -> project root
sys.path.insert(0, str(project_root))

from src.reporter import generate_weekly_report, get_notes_for_period, analyze_notes, format_report_markdown
from src.memory.memory_manager import MemoryManager # Used for mocking

# Helper to create datetime objects easily
def dt(days_ago, hour=12, minute=0, second=0):
    return datetime.now(timezone.utc) - timedelta(days=days_ago, hours=hour, minutes=minute, seconds=second)

class TestReporter(unittest.TestCase):

    def setUp(self):
        # Common timestamps for testing
        self.now = datetime.now(timezone.utc)
        self.one_day_ago = self.now - timedelta(days=1)
        self.three_days_ago = self.now - timedelta(days=3)
        self.seven_days_ago = self.now - timedelta(days=7)
        self.eight_days_ago = self.now - timedelta(days=8)

        self.test_chat_id = "test_chat_123"
        self.report_period_str = f"{(self.now - timedelta(days=7)).strftime('%Y-%m-%d')} - {self.now.strftime('%Y-%m-%d')}"

        # Sample notes data
        self.sample_notes_in_period = [
            {"role": "user", "content": "First note from three days ago about project Alpha.", "timestamp": self.three_days_ago.isoformat()},
            {"role": "user", "content": "Second note, a key insight regarding team performance.", "timestamp": self.one_day_ago.isoformat()},
            {"role": "assistant", "content": "Understood.", "timestamp": self.one_day_ago.isoformat()}, # Should be ignored
            {"role": "user", "content": "A very important discussion on project Beta and project Gamma.", "timestamp": (self.now - timedelta(days=2)).isoformat()},
            {"role": "user", "content": "Performance is key for project Alpha.", "timestamp": (self.now - timedelta(days=4)).isoformat()},
        ]
        self.sample_notes_outside_period = [
            {"role": "user", "content": "Note from eight days ago, too old.", "timestamp": self.eight_days_ago.isoformat()},
        ]
        self.all_sample_notes = self.sample_notes_in_period + self.sample_notes_outside_period

    @patch('src.reporter.memory_manager')
    def test_get_notes_for_period(self, mock_memory_manager):
        mock_memory_manager.get_history.return_value = self.all_sample_notes

        notes = get_notes_for_period(self.test_chat_id, self.seven_days_ago, self.now)

        mock_memory_manager.get_history.assert_called_once_with(self.test_chat_id)
        self.assertEqual(len(notes), 4) # 4 user notes within the last 7 days
        self.assertTrue(all(note['role'] == 'user' for note in notes))
        for note in notes:
            note_ts = datetime.fromisoformat(note['timestamp'])
            self.assertTrue(self.seven_days_ago <= note_ts <= self.now)

    @patch('src.reporter.memory_manager')
    def test_get_notes_for_period_no_notes(self, mock_memory_manager):
        mock_memory_manager.get_history.return_value = []
        notes = get_notes_for_period(self.test_chat_id, self.seven_days_ago, self.now)
        self.assertEqual(len(notes), 0)

    @patch('src.reporter.memory_manager')
    def test_get_notes_for_period_only_old_notes(self, mock_memory_manager):
        mock_memory_manager.get_history.return_value = self.sample_notes_outside_period
        notes = get_notes_for_period(self.test_chat_id, self.seven_days_ago, self.now)
        self.assertEqual(len(notes), 0)

    def test_analyze_notes_empty(self):
        insights, topics, stats = analyze_notes([])
        self.assertEqual(insights, [])
        self.assertEqual(topics, [])
        self.assertEqual(stats, {"total_notes": 0, "notes_by_day": {}})

    def test_analyze_notes_with_data(self):
        # Prepare notes that would be returned by get_notes_for_period
        user_notes_in_period = [n for n in self.sample_notes_in_period if n['role'] == 'user']
        insights, topics, stats = analyze_notes(user_notes_in_period)

        self.assertIsInstance(insights, list)
        self.assertTrue(len(insights) <= 3) # Max 3 insights
        if user_notes_in_period:
            self.assertTrue(insights[0].startswith(user_notes_in_period[0]['content'][:100]))

        self.assertIsInstance(topics, list)
        self.assertTrue(len(topics) <= 5) # Max 5 topics
        # Check for some expected words (case-insensitive, simplified check)
        all_content = " ".join(n['content'].lower() for n in user_notes_in_period)
        if "project" in all_content and len(topics) > 0 : # "project" is a likely hot topic
             self.assertTrue(any("project" in topic for topic in topics) or "alpha" in topics or "beta" in topics or "gamma" in topics )


        self.assertEqual(stats['total_notes'], len(user_notes_in_period))
        self.assertIn(self.three_days_ago.strftime('%A'), stats['notes_by_day'])
        self.assertEqual(stats['notes_by_day'][self.three_days_ago.strftime('%A')], 1)
        self.assertEqual(stats['notes_by_day'][self.one_day_ago.strftime('%A')], 1)

    def test_format_report_markdown_no_data(self):
        report = format_report_markdown(self.test_chat_id, [], [], {"total_notes": 0, "notes_by_day": {}}, self.report_period_str)
        self.assertIn(f"# Еженедельный отчет по заметкам ({self.report_period_str})", report)
        self.assertIn(f"Для пользователя: `{self.test_chat_id}`", report)
        self.assertIn("_За прошедшую неделю инсайтов не найдено._", report)
        self.assertIn("_Горячих тем не выявлено._", report)
        self.assertIn("Всего заметок за неделю: **0**", report)

    def test_format_report_markdown_with_data(self):
        key_insights = ["Insight 1: A very long insight that will be truncated if it exceeds 100 characters, which this one certainly does as I keep typing.", "Insight 2"]
        hot_topics = ["project", "alpha", "performance"]
        activity_stats = {
            "total_notes": 5,
            "notes_by_day": {
                "Monday": 2,
                "Wednesday": 3
            }
        }
        report = format_report_markdown(self.test_chat_id, key_insights, hot_topics, activity_stats, self.report_period_str)

        self.assertIn("🌟 Ключевые инсайты:", report)
        self.assertIn("1. Insight 1: A very long insight that will be truncated if it exceeds 100 characters, which this one certainly does as I keep typing.", report)
        self.assertIn("2. Insight 2", report)

        self.assertIn("🔥 Горячие темы (ключевые слова):", report)
        self.assertIn("`project`, `alpha`, `performance`", report)

        self.assertIn("📊 Статистика активности:", report)
        self.assertIn("Всего заметок за неделю: **5**", report)
        self.assertIn("Monday: 2 заметок", report)
        self.assertIn("Wednesday: 3 заметок", report)

    @patch('src.reporter.get_notes_for_period')
    @patch('src.reporter.analyze_notes')
    @patch('src.reporter.format_report_markdown')
    @patch('src.reporter.memory_manager', new_callable=MagicMock) # Mock the global memory_manager instance
    def test_generate_weekly_report_flow(self, mock_mm_instance, mock_format, mock_analyze, mock_get_notes):
        # Ensure the mocked memory_manager in reporter.py has a redis_client attribute
        mock_mm_instance.redis_client = True

        mock_notes = [{"role": "user", "content": "Test note", "timestamp": self.one_day_ago.isoformat()}]
        mock_get_notes.return_value = mock_notes

        mock_insights = ["Test insight"]
        mock_topics = ["test_topic"]
        mock_stats = {"total_notes": 1, "notes_by_day": {"Monday": 1}}
        mock_analyze.return_value = (mock_insights, mock_topics, mock_stats)

        mock_format.return_value = "Final Report Markdown"

        report = generate_weekly_report(self.test_chat_id)

        mock_get_notes.assert_called_once()
        # We need to check args of get_notes_for_period carefully for datetime objects
        args_get_notes, _ = mock_get_notes.call_args
        self.assertEqual(args_get_notes[0], self.test_chat_id)
        self.assertAlmostEqual(args_get_notes[1], self.now - timedelta(days=7), delta=timedelta(seconds=1))
        self.assertAlmostEqual(args_get_notes[2], self.now, delta=timedelta(seconds=1))

        mock_analyze.assert_called_once_with(mock_notes)

        args_format, _ = mock_format.call_args
        self.assertEqual(args_format[0], self.test_chat_id)
        self.assertEqual(args_format[1], mock_insights)
        self.assertEqual(args_format[2], mock_topics)
        self.assertEqual(args_format[3], mock_stats)
        # args_format[4] is the report_period_str, check it contains correct dates
        self.assertTrue((self.now - timedelta(days=7)).strftime('%Y-%m-%d') in args_format[4])
        self.assertTrue(self.now.strftime('%Y-%m-%d') in args_format[4])

        self.assertEqual(report, "Final Report Markdown")

    @patch('src.reporter.get_notes_for_period')
    @patch('src.reporter.memory_manager', new_callable=MagicMock)
    def test_generate_weekly_report_no_notes(self, mock_mm_instance, mock_get_notes):
        mock_mm_instance.redis_client = True
        mock_get_notes.return_value = [] # No notes found

        report = generate_weekly_report(self.test_chat_id)

        expected_start_date = (self.now - timedelta(days=7)).strftime('%Y-%m-%d')
        expected_end_date = self.now.strftime('%Y-%m-%d')
        expected_msg = f"За последнюю неделю ({expected_start_date} - {expected_end_date}) у вас не было заметок. Отчет не может быть сформирован."
        self.assertEqual(report, expected_msg)

    @patch('src.reporter.memory_manager', new_callable=MagicMock)
    def test_generate_weekly_report_memory_manager_unavailable(self, mock_global_mm_in_reporter):
        # Simulate MemoryManager failing to initialize or connect.
        # Scenario 1: The global 'memory_manager' in 'reporter.py' is None
        with patch('src.reporter.memory_manager', None) as mm_is_none:
            report = generate_weekly_report(self.test_chat_id)
            self.assertEqual(report, "Ошибка: Сервис памяти недоступен. Невозможно сгенерировать отчет.")
            # mm_is_none is the MagicMock for 'src.reporter.memory_manager' which is now None

        # Scenario 2: The global 'memory_manager' instance exists, but its 'redis_client' is None
        # We need to make the global 'memory_manager' in 'reporter.py' be this specific mock
        mock_mm_instance_no_client = MagicMock(spec=MemoryManager)
        mock_mm_instance_no_client.redis_client = None

        with patch('src.reporter.memory_manager', mock_mm_instance_no_client) as mm_no_client:
            report = generate_weekly_report(self.test_chat_id)
            self.assertEqual(report, "Ошибка: Сервис памяти недоступен. Невозможно сгенерировать отчет.")
            # mm_no_client is the MagicMock for 'src.reporter.memory_manager' which is mock_mm_instance_no_client


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

# To run these tests:
# Ensure you are in the project root directory.
# Run: python -m unittest src/tests/test_reporter.py
# Or, if pytest is installed and configured: pytest src/tests/test_reporter.py
