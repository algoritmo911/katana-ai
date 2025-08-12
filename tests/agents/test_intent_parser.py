import unittest
import sys
import os

# Добавляем корневую директорию проекта в sys.path
# чтобы можно было импортировать модуль katana
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from katana.agents.intent_parser import IntentParser
from katana.contracts.intent_contract import IntentContract, Constraints

class TestIntentParser(unittest.TestCase):
    """
    Тесты для `IntentParser`.
    """

    def setUp(self):
        """
        Настройка перед каждым тестом.
        """
        self.parser = IntentParser()
        self.valid_query = (
            "Мне нужно повысить удержание пользователей на 10% в следующем квартале, "
            "бюджет до 50,000 SC, нельзя использовать темные паттерны"
        )
        self.incomplete_query = "Срочно нужно повысить удержание пользователей."
        self.invalid_query = "Я хочу новый дашборд."

    def test_parse_success_valid_query(self):
        """
        Тест: Успешный парсинг полностью определенного запроса.
        """
        contract = self.parser.parse(self.valid_query)

        self.assertIsInstance(contract, IntentContract)
        self.assertEqual(contract.objective, "Повысить удержание пользователей на 10%")
        self.assertEqual(contract.timeframe, "Следующий квартал")

        self.assertIsInstance(contract.constraints, Constraints)
        self.assertEqual(contract.constraints.max_budget, 50000)
        self.assertEqual(contract.constraints.currency, "SC")
        self.assertEqual(contract.constraints.forbidden_methods, ["темные паттерны"])

        self.assertIn("Удержание пользователей достигло значения X+10%", contract.key_results)

    def test_parse_failure_unrecognized_query(self):
        """
        Тест: Парсер должен вернуть ошибку на нераспознаваемом запросе.
        """
        with self.assertRaises(ValueError) as context:
            self.parser.parse(self.invalid_query)

        self.assertEqual(
            str(context.exception),
            "Не удалось распознать намерение в запросе."
        )

    def test_parse_success_incomplete_query(self):
        """
        Тест: Успешный парсинг неполного запроса.
        """
        contract = self.parser.parse(self.incomplete_query)

        self.assertIsInstance(contract, IntentContract)
        self.assertEqual(contract.objective, "Повысить удержание пользователей")
        self.assertIsNone(contract.timeframe)
        self.assertIsNone(contract.constraints.max_budget)
        self.assertEqual(contract.key_results, [])


if __name__ == '__main__':
    unittest.main()
