import unittest
from unittest.mock import patch, MagicMock
import os
import logging

# Подавление избыточного вывода логов во время тестов
logging.disable(logging.CRITICAL)

# Импортируем классы из модуля nlp_service
from bot.nlp_service import ( # Изменен импорт на абсолютный от корня проекта
    NLPService,
    NLPProviderConfig,
    MockNLPProvider,
    GPT4TurboProvider,
    ClaudeProvider,
    BaseNLPProvider
)

class TestNLPService(unittest.TestCase):

    def setUp(self):
        """Настройка перед каждым тестом."""
        # Сбрасываем переменные окружения, которые могли быть установлены в других тестах или глобально
        self.original_environ = os.environ.copy()
        os.environ.clear()

    def tearDown(self):
        """Очистка после каждого теста."""
        os.environ.clear()
        os.environ.update(self.original_environ)
        # Восстанавливаем логирование после тестов
        logging.disable(logging.NOTSET)


    @patch.dict(os.environ, {
        "NLP_PROVIDERS": "mock",
        "DEFAULT_NLP_PROVIDER": "mock",
        "MOCK_MODEL_NAME": "test-mock-model"
    })
    def test_01_load_mock_provider(self):
        service = NLPService()
        self.assertIn("mock", service.providers)
        self.assertIsInstance(service.providers["mock"], MockNLPProvider)
        self.assertEqual(service.providers["mock"].config.model_name, "test-mock-model")
        self.assertEqual(service.default_provider_name, "mock")

    @patch.dict(os.environ, {
        "NLP_PROVIDERS": "gpt4,claude",
        "DEFAULT_NLP_PROVIDER": "gpt4",
        "GPT4_MODEL_NAME": "test-gpt4-model",
        "CLAUDE_MODEL_NAME": "test-claude-model",
        # API ключи не установлены, будут использоваться заглушки
    })
    def test_02_load_multiple_providers_no_api_keys(self):
        service = NLPService()
        self.assertIn("gpt4", service.providers)
        self.assertIn("claude", service.providers)
        self.assertIsInstance(service.providers["gpt4"], GPT4TurboProvider)
        self.assertIsInstance(service.providers["claude"], ClaudeProvider)
        self.assertEqual(service.providers["gpt4"].config.model_name, "test-gpt4-model")
        self.assertEqual(service.providers["claude"].config.model_name, "test-claude-model")
        self.assertIsNone(service.providers["gpt4"].config.api_key) # Проверяем, что ключ не установлен

        # Тест ответа GPT-4 без ключа (должен быть mock response)
        response = service.process_text("Hello GPT-4", provider_name="gpt4")
        self.assertIn("error", response)
        self.assertIn("API key for GPT4TurboProvider not configured", response["error"])

    def test_03_mock_provider_text_request(self):
        config = NLPProviderConfig(model_name="test-text-mock")
        provider = MockNLPProvider(config)
        response = provider.process_text_request("Test input")
        self.assertEqual(response["provider"], "MockNLPProvider")
        self.assertEqual(response["model"], "test-text-mock")
        self.assertEqual(response["input_text"], "Test input")
        self.assertIn("Mock response for 'Test input'", response["response_text"])
        self.assertTrue(len(response["intents"]) > 0)

    def test_04_mock_provider_multimodal_request(self):
        config = NLPProviderConfig(model_name="test-mm-mock")
        provider = MockNLPProvider(config)
        response = provider.process_multimodal_request(text="Describe image", image_url="http://example.com/img.jpg")
        self.assertEqual(response["provider"], "MockNLPProvider")
        self.assertEqual(response["model"], "test-mm-mock")
        self.assertIn("image at 'http://example.com/img.jpg'", response["response_text"])

    @patch.dict(os.environ, {
        "NLP_PROVIDERS": "mock",
        "DEFAULT_NLP_PROVIDER": "mock",
        "MOCK_MODEL_NAME": "session-mock"
    })
    def test_05_mock_provider_session_memory(self):
        service = NLPService()
        session_id = "test_session_1"

        # Первый запрос
        response1 = service.process_text("My name is Jules.", session_id=session_id)
        self.assertFalse(response1.get("history_processed", False)) # Нет истории на первом шаге

        # Второй запрос
        response2 = service.process_text("What is my name?", session_id=session_id)
        self.assertTrue(response2.get("history_processed", False)) # История должна быть обработана
        # В MockNLPProvider история добавляется в лог, но сам ответ не сильно меняется от истории
        # Проверяем, что ответ содержит упоминание обработки истории
        self.assertIn("(history processed: True)", response2["response_text"])

        # Проверяем, что память сессии существует у провайдера
        mock_provider_instance = service.get_provider("mock")
        self.assertIn(session_id, mock_provider_instance.memory)
        self.assertEqual(len(mock_provider_instance.memory[session_id]), 2) # Два обмена

    @patch.dict(os.environ, {
        "NLP_PROVIDERS": "mock",
        "DEFAULT_NLP_PROVIDER": "mock",
        "MOCK_MODEL_NAME": "multi-intent-mock"
    })
    def test_06_mock_provider_multi_intent(self):
        service = NLPService()
        # Запрос без "и" / "and"
        response_single = service.process_text("Tell me a joke.")
        self.assertEqual(len(response_single.get("intents", [])), 1)

        # Запрос с "и"
        response_multi = service.process_text("Tell me a joke and what is the weather?")
        self.assertGreater(len(response_multi.get("intents", [])), 1, "Should have more than one intent")
        self.assertEqual(response_multi["intents"][0]["intent"], "mock_intent_primary")
        self.assertEqual(response_multi["intents"][1]["intent"], "mock_intent_secondary")


    @patch.dict(os.environ, {
        "NLP_PROVIDERS": "mock,gpt4",
        "DEFAULT_NLP_PROVIDER": "mock",
        "MOCK_MODEL_NAME": "dynamic-mock",
        "GPT4_MODEL_NAME": "dynamic-gpt4",
    })
    def test_07_dynamic_model_selection_text(self):
        service = NLPService()
        # FAQ должен выбрать mock
        response_faq = service.process_text("How to reset password?", task_type="faq")
        self.assertEqual(response_faq["provider"], "MockNLPProvider")

        # Complex context должен выбрать gpt4 (даже если это mock gpt4 без ключа)
        response_complex = service.process_text("Analyze this complex data.", task_type="complex_context")
        self.assertEqual(response_complex["provider"], "GPT4TurboProvider") # GPT4 провайдер, но может вернуть ошибку API ключа

        # General должен выбрать default (mock)
        response_general = service.process_text("General query.", task_type="general")
        self.assertEqual(response_general["provider"], "MockNLPProvider")

        # Явное указание провайдера
        response_explicit_gpt4 = service.process_text("Query for GPT4.", provider_name="gpt4")
        self.assertEqual(response_explicit_gpt4["provider"], "GPT4TurboProvider")


    @patch.dict(os.environ, {
        "NLP_PROVIDERS": "mock,gpt4", # gpt4 (mock) поддерживает multimodal
        "DEFAULT_NLP_PROVIDER": "mock", # mock поддерживает multimodal
        "MOCK_MODEL_NAME": "dynamic-mm-mock",
        "GPT4_MODEL_NAME": "dynamic-mm-gpt4",
    })
    def test_08_dynamic_model_selection_multimodal(self):
        service = NLPService()
        # simple_multimodal_caption должен выбрать mock
        response_simple_mm = service.process_multimodal(text="Describe", image_url="url", task_type="simple_multimodal_caption")
        self.assertEqual(response_simple_mm["provider"], "MockNLPProvider")

        # complex_multimodal_analysis должен выбрать gpt4
        response_complex_mm = service.process_multimodal(text="Analyze", image_url="url", task_type="complex_multimodal_analysis")
        self.assertEqual(response_complex_mm["provider"], "GPT4TurboProvider")


    @patch.dict(os.environ, {
        "NLP_PROVIDERS": "mock",
        "DEFAULT_NLP_PROVIDER": "mock",
        "MOCK_MODEL_NAME": "base-mock-model",
        "MOCK_FINETUNE_MODEL_ID": "ft:mock-tuned:123",
        "FINETUNING_ENABLED_PROVIDERS": "mock"
    })
    def test_09_load_finetuned_model(self):
        service = NLPService()
        self.assertIn("mock", service.providers)
        mock_provider = service.get_provider("mock")
        self.assertEqual(mock_provider.config.model_name, "ft:mock-tuned:123")

    @patch.dict(os.environ, {
        "NLP_PROVIDERS": "gpt4",
        "DEFAULT_NLP_PROVIDER": "gpt4",
        "GPT4_MODEL_NAME": "base-gpt4-model",
        # FINETUNE_MODEL_ID не указан, но FINETUNING_ENABLED_PROVIDERS включает gpt4
        "FINETUNING_ENABLED_PROVIDERS": "gpt4"
    })
    def test_10_finetuning_enabled_no_id_uses_base_model(self):
        service = NLPService()
        self.assertIn("gpt4", service.providers)
        gpt4_provider = service.get_provider("gpt4")
        self.assertEqual(gpt4_provider.config.model_name, "base-gpt4-model")

    @patch.dict(os.environ, {
        "NLP_PROVIDERS": "claude",
        "DEFAULT_NLP_PROVIDER": "claude",
        "CLAUDE_MODEL_NAME": "base-claude-model",
        "CLAUDE_FINETUNE_MODEL_ID": "ft:claude-tuned:abc",
        # FINETUNING_ENABLED_PROVIDERS НЕ включает claude
    })
    def test_11_finetuning_not_enabled_uses_base_model(self):
        service = NLPService()
        self.assertIn("claude", service.providers)
        claude_provider = service.get_provider("claude")
        self.assertEqual(claude_provider.config.model_name, "base-claude-model")

    def test_12_get_provider_fallback(self):
        # Случай, когда default_provider_name не существует, должен вернуться mock
        with patch.dict(os.environ, {"NLP_PROVIDERS": "mock", "DEFAULT_NLP_PROVIDER": "non_existent_provider"}):
            service = NLPService()
            provider = service.get_provider() # Должен вернуть mock, так как non_existent_provider нет
            self.assertIsInstance(provider, MockNLPProvider)
            self.assertEqual(service.default_provider_name, "mock") # default_provider_name должен был быть исправлен

        # Случай, когда вообще нет провайдеров, должен создаться аварийный mock
        with patch.dict(os.environ, {"NLP_PROVIDERS": "", "DEFAULT_NLP_PROVIDER": ""}):
            service = NLPService()
            self.assertIn("mock", service.providers)
            self.assertIsInstance(service.providers["mock"], MockNLPProvider)
            self.assertEqual(service.providers["mock"].config.model_name, "emergency-fallback-mock")
            self.assertEqual(service.default_provider_name, "mock")
            provider = service.get_provider("some_other_non_existent")
            self.assertIsInstance(provider, MockNLPProvider) # Должен вернуть аварийный mock


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

# Для запуска из командной строки в директории `bot`:
# python -m unittest test_nlp_service.py
# или если nlp_service не виден как модуль:
# PYTHONPATH=. python -m unittest test_nlp_service.py
# (Убедитесь, что nlp_service.py и test_nlp_service.py в одной директории `bot`)
