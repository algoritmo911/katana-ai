import os
from abc import ABC, abstractmethod
import logging
from datetime import datetime # Добавлен импорт datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class NLPProviderConfig:
    """Класс для хранения конфигурации NLP-провайдера."""
    def __init__(self, api_key=None, model_name=None, api_base=None):
        self.api_key = api_key
        self.model_name = model_name
        self.api_base = api_base

class BaseNLPProvider(ABC):
    """Абстрактный базовый класс для NLP-провайдеров."""
    def __init__(self, config: NLPProviderConfig):
        self.config = config
        self.name = self.__class__.__name__
        self.memory = {} # Простая внутрипроцессная память для диалогов
        logging.info(f"Initializing NLP Provider: {self.name} with model: {config.model_name or 'default'}")

    def _get_session_memory(self, session_id: str) -> list:
        """Получает историю сообщений для сессии."""
        if session_id not in self.memory:
            self.memory[session_id] = []
        return self.memory[session_id]

    def _add_to_session_memory(self, session_id: str, user_message: str, bot_message: str):
        """Добавляет сообщение в историю сессии."""
        if session_id:
            session_memory = self._get_session_memory(session_id)
            session_memory.append({"user": user_message, "bot": bot_message})
            # Ограничение размера истории (например, последние 10 обменов)
            if len(session_memory) > 10:
                self.memory[session_id] = session_memory[-10:]

    @abstractmethod
    def process_text_request(self, text: str, context: dict = None, session_id: str = None) -> dict:
        """
        Обработка текстового запроса.
        `context` может содержать метаданные запроса.
        `session_id` используется для управления памятью диалога.
        """
        pass

    @abstractmethod
    def process_multimodal_request(self, text: str = None, image_url: str = None, audio_url: str = None, context: dict = None, session_id: str = None) -> dict:
        """
        Обработка мультимодального запроса.
        `session_id` используется для управления памятью диалога.
        """
        pass

    def get_provider_name(self) -> str:
        """Возвращает имя провайдера."""
        return self.name

class MockNLPProvider(BaseNLPProvider):
    """Заглушка для NLP-провайдера. Используется для разработки и тестирования."""
    def __init__(self, config: NLPProviderConfig):
        super().__init__(config)
        if not self.config.model_name:
            self.config.model_name = "mock-model" # Модель по умолчанию для заглушки

    def process_text_request(self, text: str, context: dict = None, session_id: str = None) -> dict:
        history_prompt = ""
        if session_id:
            session_memory = self._get_session_memory(session_id)
            if session_memory:
                history_prompt = "Previous conversation: " + " ".join([f"User: {turn['user']} Bot: {turn['bot']}" for turn in session_memory])
                history_prompt += " Current User: "

        full_prompt = history_prompt + text
        logging.info(f"[{self.name}] Processing text request: '{full_prompt}' with context: {context}, session_id: {session_id}")

        # Имитация multi-intent: если в тексте есть "и" или "and", считаем, что два намерения
        intents = [{"intent": "mock_intent_primary", "score": 0.9}]
        if " и " in text.lower() or " and " in text.lower():
            intents.append({"intent": "mock_intent_secondary", "score": 0.75})

        response_text = f"Mock response for '{text}' (history processed: {bool(history_prompt)}) from {self.config.model_name}."

        if session_id:
            self._add_to_session_memory(session_id, text, response_text)

        response = {
            "provider": self.name,
            "model": self.config.model_name,
            "input_text": text,
            "response_text": response_text,
            "intents": intents,
            "entities": [{"entity": "mock_entity", "value": "mock_value"}],
            "context": context or {},
            "session_id": session_id,
            "history_processed": bool(history_prompt)
        }
        logging.info(f"[{self.name}] Response: {response}")
        return response

    def process_multimodal_request(self, text: str = None, image_url: str = None, audio_url: str = None, context: dict = None, session_id: str = None) -> dict:
        history_prompt = ""
        if session_id:
            session_memory = self._get_session_memory(session_id)
            if session_memory:
                 history_prompt = "Previous conversation: " + " ".join([f"User: {turn['user']} Bot: {turn['bot']}" for turn in session_memory])
                 history_prompt += " Current User: "

        full_text_input = (history_prompt + text) if text else history_prompt # Если текста нет, только история
        logging.info(f"[{self.name}] Processing multimodal request: text='{full_text_input}', image='{image_url}', audio='{audio_url}' with context: {context}, session_id: {session_id}")

        processed_inputs = []
        if text:
            processed_inputs.append(f"text input '{text}'")
        if image_url:
            processed_inputs.append(f"image at '{image_url}' (simulated processing)")
        if audio_url:
            processed_inputs.append(f"audio at '{audio_url}' (simulated processing)")

        response_text = f"Mock multimodal response for {', '.join(processed_inputs)} (history processed: {bool(history_prompt)}) from {self.config.model_name}."

        if session_id and (text or image_url or audio_url): # Добавляем в память, если был какой-то ввод
             user_input_summary = f"text: {text}, image: {image_url}, audio: {audio_url}"
             self._add_to_session_memory(session_id, user_input_summary, response_text)

        response = {
            "provider": self.name,
            "model": self.config.model_name,
            "input_text": text,
            "input_image_url": image_url,
            "input_audio_url": audio_url,
            "response_text": response_text,
            "intents": [{"intent": "mock_multimodal_intent", "score": 0.85}],
            "entities": [],
            "context": context or {},
            "session_id": session_id,
            "history_processed": bool(history_prompt)
        }
        logging.info(f"[{self.name}] Multimodal Response: {response}")
        return response

class GPT4TurboProvider(BaseNLPProvider):
    """Реализация NLP-провайдера для GPT-4 Turbo (заглушка)."""
    def __init__(self, config: NLPProviderConfig):
        super().__init__(config)
        if not self.config.api_key:
            logging.warning(f"API key for {self.name} is not set. Using mock functionality.")
        if not self.config.model_name:
            self.config.model_name = "gpt-4-turbo"

    def process_text_request(self, text: str, context: dict = None, session_id: str = None) -> dict:
        history_prompt = ""
        if session_id:
            session_memory = self._get_session_memory(session_id)
            # TODO: Форматировать историю для GPT-4 API (например, список сообщений user/assistant)
            if session_memory:
                 history_prompt = " ".join([f"User: {turn['user']} Assistant: {turn['bot']}" for turn in session_memory]) + " User: "

        full_prompt = history_prompt + text
        logging.info(f"[{self.name} ({self.config.model_name})] Processing text request: '{full_prompt}'")

        if not self.config.api_key:
            mock_response_text = f"Mock GPT-4 Turbo response for '{text}'. API key needed. History processed: {bool(history_prompt)}"
            if session_id: self._add_to_session_memory(session_id, text, mock_response_text)
            return {
                "error": f"API key for {self.name} not configured. This is a mock response.",
                "provider": self.name,
                "model": self.config.model_name,
                "input_text": text,
                "response_text": mock_response_text,
                "intents": [{"intent": "gpt4_mock_intent", "score": 0.9}],
                "session_id": session_id,
                "history_processed": bool(history_prompt)
            }

        # Здесь будет реальная логика взаимодействия с API GPT-4 Turbo
        # response_from_api = call_gpt4_api(full_prompt, self.config.api_key, context)
        # intents_from_api = parse_intents(response_from_api)
        # entities_from_api = parse_entities(response_from_api)
        response_text = f"Simulated GPT-4 Turbo response for '{text}'. History processed: {bool(history_prompt)}"

        if session_id:
            self._add_to_session_memory(session_id, text, response_text)

        response = {
            "provider": self.name,
            "model": self.config.model_name,
            "input_text": text,
            "response_text": response_text,
            "intents": [{"intent": "gpt4_simulated_intent", "score": 0.95}],
            "entities": [],
            "context": context,
            "session_id": session_id,
            "history_processed": bool(history_prompt)
        }
        logging.info(f"[{self.name}] Response: {response}")
        return response

    def process_multimodal_request(self, text: str = None, image_url: str = None, audio_url: str = None, context: dict = None, session_id: str = None) -> dict:
        history_prompt = ""
        if session_id:
            session_memory = self._get_session_memory(session_id)
            # TODO: Форматировать историю для GPT-4 Vision API
            if session_memory:
                 history_prompt = " ".join([f"User: {turn['user']} Assistant: {turn['bot']}" for turn in session_memory]) + " User: "

        full_text_input = (history_prompt + text) if text else history_prompt
        logging.info(f"[{self.name} ({self.config.model_name})] Processing multimodal request: text='{full_text_input}', image='{image_url}', audio='{audio_url}'")

        if not self.config.api_key:
            mock_response_text = f"Mock GPT-4 Turbo multimodal response. API key needed. History processed: {bool(history_prompt)}"
            if session_id:
                user_input_summary = f"text: {text}, image: {image_url}, audio: {audio_url}"
                self._add_to_session_memory(session_id, user_input_summary, mock_response_text)
            return {
                "error": f"API key for {self.name} not configured. This is a mock response.",
                "provider": self.name,
                "model": self.config.model_name,
                "input_text": text,
                "input_image_url": image_url,
                "input_audio_url": audio_url,
                "response_text": "Mock GPT-4 Turbo multimodal response. API key needed."
            }

        # Реальная логика взаимодействия с API GPT-4 Vision/Audio
        # response_from_api = call_gpt4_multimodal_api(text, image_url, audio_url, self.config.api_key, context)
        response_text = f"Simulated GPT-4 Turbo multimodal response for text: '{text}', image: '{image_url}', audio: '{audio_url}'."

        response = {
            "provider": self.name,
            "model": self.config.model_name,
            "input_text": text,
            "input_image_url": image_url,
            "input_audio_url": audio_url,
            "response_text": response_text,
            "intents": [],
            "entities": [],
            "context": context
        }
        logging.info(f"[{self.name}] Multimodal Response: {response}")
        return response

class ClaudeProvider(BaseNLPProvider):
    """Реализация NLP-провайдера для Claude (заглушка)."""
    def __init__(self, config: NLPProviderConfig):
        super().__init__(config)
        if not self.config.api_key:
            logging.warning(f"API key for {self.name} is not set. Using mock functionality.")
        if not self.config.model_name:
            self.config.model_name = "claude-3-opus" # Пример

    def process_text_request(self, text: str, context: dict = None, session_id: str = None) -> dict:
        history_prompt = ""
        if session_id:
            session_memory = self._get_session_memory(session_id)
            # TODO: Форматировать историю для Claude API
            if session_memory:
                history_prompt = "\n\n".join([f"Human: {turn['user']}\n\nAssistant: {turn['bot']}" for turn in session_memory]) + f"\n\nHuman: {text}\n\nAssistant:"
            else:
                history_prompt = f"Human: {text}\n\nAssistant:"
        else:
            history_prompt = f"Human: {text}\n\nAssistant:"

        logging.info(f"[{self.name} ({self.config.model_name})] Processing text request with prompt (history included if session_id provided).")

        if not self.config.api_key:
            mock_response_text = f"Mock Claude response for '{text}'. API key needed. History processed: {bool(session_id and self._get_session_memory(session_id))}"
            if session_id: self._add_to_session_memory(session_id, text, mock_response_text)
            return {
                "error": f"API key for {self.name} not configured. This is a mock response.",
                "provider": self.name,
                "model": self.config.model_name,
                "input_text": text,
                "response_text": mock_response_text,
                "intents": [{"intent": "claude_mock_intent", "score": 0.88}],
                "session_id": session_id,
                "history_processed": bool(session_id and self._get_session_memory(session_id))
            }

        # Здесь будет реальная логика взаимодействия с API Claude
        # response_from_api = call_claude_api(history_prompt, self.config.api_key, context)
        response_text = f"Simulated Claude response for '{text}'. History processed: {bool(session_id and self._get_session_memory(session_id))}"

        if session_id:
            self._add_to_session_memory(session_id, text, response_text)

        response = {
            "provider": self.name,
            "model": self.config.model_name,
            "input_text": text,
            "response_text": response_text,
            "intents": [{"intent": "claude_simulated_intent", "score": 0.92}],
            "entities": [],
            "context": context,
            "session_id": session_id,
            "history_processed": bool(session_id and self._get_session_memory(session_id))
        }
        logging.info(f"[{self.name}] Response: {response}")
        return response

    def process_multimodal_request(self, text: str = None, image_url: str = None, audio_url: str = None, context: dict = None, session_id: str = None) -> dict:
        history_prompt_claude_format = []
        if session_id:
            session_memory = self._get_session_memory(session_id)
            # TODO: Форматировать историю для Claude Multimodal API
            for turn in session_memory:
                history_prompt_claude_format.append({"role": "user", "content": turn["user"]})
                history_prompt_claude_format.append({"role": "assistant", "content": turn["bot"]})

        current_request_content = []
        if image_url: # Claude ожидает base64 или URL для изображений в определенном формате
            current_request_content.append({"type": "image_url", "image_url": {"url": image_url}}) # Примерный формат
        if audio_url: # Аналогично для аудио, если API поддерживает
             logging.warning(f"[{self.name}] Audio URL processing is conceptual for Claude in this mock.")
             current_request_content.append({"type": "text", "text": f"(Audio content from {audio_url} was conceptually processed)"}) # Заглушка
        if text:
            current_request_content.append({"type": "text", "text": text})

        full_claude_prompt = history_prompt_claude_format + [{"role": "user", "content": current_request_content}]

        logging.info(f"[{self.name} ({self.config.model_name})] Processing multimodal request. Image: {bool(image_url)}, Audio: {bool(audio_url)}. History items: {len(history_prompt_claude_format)}")

        if not self.config.api_key:
            mock_response_text = f"Mock Claude multimodal response. API key needed. History items: {len(history_prompt_claude_format)}"
            if session_id:
                user_input_summary = f"text: {text}, image: {image_url}, audio: {audio_url}"
                self._add_to_session_memory(session_id, user_input_summary, mock_response_text)
            return {
                "error": f"API key for {self.name} not configured. This is a mock response.",
                "provider": self.name,
                "model": self.config.model_name,
                "input_text": text,
                "input_image_url": image_url,
                "input_audio_url": audio_url,
                "response_text": "Mock Claude multimodal response. API key needed. Support may vary."
            }

        # Реальная логика взаимодействия с API Claude multimodal
        # response_from_api = call_claude_multimodal_api(text, image_url, audio_url, self.config.api_key, context)
        response_text = f"Simulated Claude multimodal response for text: '{text}', image: '{image_url}', audio: '{audio_url}'."

        response = {
            "provider": self.name,
            "model": self.config.model_name,
            "input_text": text,
            "input_image_url": image_url,
            "input_audio_url": audio_url,
            "response_text": response_text,
            "intents": [],
            "entities": [],
            "context": context
        }
        logging.info(f"[{self.name}] Multimodal Response: {response}")
        return response


class NLPService:
    """Сервис для управления и использования NLP-провайдеров."""
    def __init__(self):
        self.providers = {}
        self.default_provider_name = None
        self.load_providers_from_config()

    def load_providers_from_config(self):
        """Загружает и инициализирует NLP-провайдеров на основе конфигурации (переменные окружения)."""
        # Пример конфигурации через переменные окружения:
        # NLP_PROVIDERS="mock,gpt4,claude"
        # DEFAULT_NLP_PROVIDER="mock"
        # MOCK_MODEL_NAME="mock-experimental"
        # MOCK_FINETUNE_MODEL_ID="ft:mock-model:my-org:my-dataset:12345" # Пример ID для fine-tuned модели
        # GPT4_API_KEY="sk-..."
        # GPT4_MODEL_NAME="gpt-4-turbo-preview"
        # GPT4_FINETUNE_MODEL_ID="ft:gpt-3.5-turbo:my-org:custom-name:abcdef"
        # CLAUDE_API_KEY="claude-api-key-..."
        # CLAUDE_MODEL_NAME="claude-3-opus-20240229"
        # CLAUDE_API_BASE="https://api.anthropic.com"
        # FINETUNING_ENABLED_PROVIDERS="mock,gpt4" # Провайдеры, для которых разрешено fine-tuning

        provider_names_str = os.getenv("NLP_PROVIDERS", "mock")
        self.default_provider_name = os.getenv("DEFAULT_NLP_PROVIDER", "mock")

        self.available_provider_classes = { # Сделаем доступным извне для тестов
            "mock": MockNLPProvider,
            "gpt4": GPT4TurboProvider,
            "claude": ClaudeProvider
        }
        self.finetuning_enabled_providers = os.getenv("FINETUNING_ENABLED_PROVIDERS", "").split(',')

        providers_loaded_successfully = False
        if provider_names_str: # Только если NLP_PROVIDERS не пустая строка
            for name in provider_names_str.split(','):
                name = name.strip()
                if not name: continue # Пропускаем пустые имена после split

                if name in self.available_provider_classes:
                    api_key = os.getenv(f"{name.upper()}_API_KEY")
                    model_name_env = os.getenv(f"{name.upper()}_MODEL_NAME")
                    api_base = os.getenv(f"{name.upper()}_API_BASE")

                    finetuned_model_id = None
                    if name in self.finetuning_enabled_providers:
                        finetuned_model_id = os.getenv(f"{name.upper()}_FINETUNE_MODEL_ID")

                    effective_model_name = finetuned_model_id or model_name_env

                    config = NLPProviderConfig(api_key=api_key, model_name=effective_model_name, api_base=api_base)
                    try:
                        self.providers[name] = self.available_provider_classes[name](config)
                        logging.info(f"Successfully loaded NLP provider: {name} with model: {effective_model_name or 'default'}")
                        if finetuned_model_id and finetuned_model_id == effective_model_name:
                            logging.info(f"Provider {name} is using a fine-tuned model: {finetuned_model_id}")
                        providers_loaded_successfully = True
                    except Exception as e:
                        logging.error(f"Failed to initialize provider {name}: {e}")
                else:
                    logging.warning(f"Unknown NLP provider specified in NLP_PROVIDERS: {name}")

        # Если ни один провайдер не был успешно загружен из NLP_PROVIDERS (или NLP_PROVIDERS был пуст)
        if not providers_loaded_successfully:
            logging.warning("No providers loaded from environment or all failed. Setting up emergency fallback mock provider.")
            # Удаляем любые частично загруженные или failed провайдеры, чтобы гарантировать чистое состояние
            self.providers.clear()
            self.providers["mock"] = MockNLPProvider(NLPProviderConfig(model_name="emergency-fallback-mock"))
            self.default_provider_name = "mock"
        else:
            # Если провайдеры были загружены, проверяем default_provider_name
            if self.default_provider_name not in self.providers:
                logging.warning(f"Default provider '{self.default_provider_name}' not found or failed to load. Falling back to first available or mock.")
                # Пытаемся установить default_provider_name на первый доступный
                # Если 'mock' среди них, он хороший кандидат. Иначе первый из self.providers.
                if "mock" in self.providers:
                    self.default_provider_name = "mock"
                elif self.providers: # Если есть хоть какие-то провайдеры
                    self.default_provider_name = next(iter(self.providers))
                else:
                    # Этот случай не должен произойти, если providers_loaded_successfully is True,
                    # но для безопасности:
                    logging.error("Critical: Providers were thought to be loaded, but self.providers is empty. Re-falling back to emergency mock.")
                    self.providers["mock"] = MockNLPProvider(NLPProviderConfig(model_name="emergency-fallback-mock"))
                    self.default_provider_name = "mock"


    def get_provider(self, provider_name: str = None) -> BaseNLPProvider:
        """Возвращает инстанс указанного NLP-провайдера или провайдера по умолчанию."""
        name_to_use = provider_name or self.default_provider_name
        provider = self.providers.get(name_to_use)
        if not provider:
            logging.error(f"NLP Provider '{name_to_use}' not found. Available: {list(self.providers.keys())}")
            if self.default_provider_name in self.providers:
                logging.warning(f"Falling back to default provider: {self.default_provider_name}")
                return self.providers[self.default_provider_name]
            elif "mock" in self.providers:
                logging.warning("Falling back to mock provider.")
                return self.providers["mock"]
            else:
                raise ValueError(f"No NLP providers available, including mock. Critical configuration error.")
        return provider

    def process_text(self, text: str, provider_name: str = None, context: dict = None, task_type: str = "general", session_id: str = None) -> dict:
        """
        Обрабатывает текстовый запрос.
        `session_id` передается из katana_bot.py, если доступен (например, из chat_id).
        """
        if provider_name and provider_name in self.providers:
            selected_provider_name = provider_name
            logging.info(f"Using explicitly specified provider: {selected_provider_name} for task_type: {task_type}")
        elif task_type == "faq":
            if "mock" in self.providers:
                selected_provider_name = "mock"
            else:
                selected_provider_name = self.default_provider_name
            logging.info(f"Dynamically selected '{selected_provider_name}' provider for task_type: 'faq'")
        elif task_type == "complex_context":
            if "gpt4" in self.providers:
                selected_provider_name = "gpt4"
            elif "claude" in self.providers:
                selected_provider_name = "claude"
            else:
                selected_provider_name = self.default_provider_name
            logging.info(f"Dynamically selected '{selected_provider_name}' provider for task_type: 'complex_context'")
        else:
            selected_provider_name = self.default_provider_name
            logging.info(f"Using default provider '{selected_provider_name}' for task_type: '{task_type}'")

        provider = self.get_provider(selected_provider_name)
        logging.info(f"Processing text with {provider.get_provider_name()} (Model: {provider.config.model_name}) for task type '{task_type}' using selected provider '{selected_provider_name}', session: {session_id}")

        start_time = datetime.utcnow()
        try:
            response = provider.process_text_request(text, context=context, session_id=session_id)
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            logging.info(f"[METRIC] Provider: {provider.get_provider_name()}, Model: {provider.config.model_name}, Type: Text, Task: {task_type}, Time: {processing_time:.4f}s, Session: {session_id}, Success: True")
            return response
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            logging.error(f"[METRIC] Provider: {provider.get_provider_name()}, Model: {provider.config.model_name}, Type: Text, Task: {task_type}, Time: {processing_time:.4f}s, Session: {session_id}, Success: False, Error: {str(e)}")
            raise # Перевыбрасываем исключение, чтобы оно было обработано выше

    def process_multimodal(self, text: str = None, image_url: str = None, audio_url: str = None, provider_name: str = None, context: dict = None, task_type: str = "general_multimodal", session_id: str = None) -> dict:
        """
        Обрабатывает мультимодальный запрос.
        `session_id` передается из katana_bot.py.
        """
        selected_provider_name_for_multimodal = self.default_provider_name # Инициализация значением по умолчанию

        if provider_name and provider_name in self.providers:
            selected_provider_name_for_multimodal = provider_name
            logging.info(f"Using explicitly specified provider for multimodal: {selected_provider_name_for_multimodal} for task_type: {task_type}")
        elif task_type == "simple_multimodal_caption":
            potential_providers = ["mock", "gpt4", "claude"] # Порядок предпочтения
            for p_name in potential_providers:
                if p_name in self.providers and hasattr(self.providers[p_name], 'process_multimodal_request'):
                    selected_provider_name_for_multimodal = p_name
                    break
            logging.info(f"Dynamically selected '{selected_provider_name_for_multimodal}' provider for task_type: '{task_type}'")
        elif task_type == "complex_multimodal_analysis":
            potential_providers = ["gpt4", "claude", "mock"] # Порядок предпочтения для сложных задач
            for p_name in potential_providers:
                if p_name in self.providers and hasattr(self.providers[p_name], 'process_multimodal_request'):
                    selected_provider_name_for_multimodal = p_name
                    break
            logging.info(f"Dynamically selected '{selected_provider_name_for_multimodal}' provider for task_type: '{task_type}'")
        else:
            # Для general_multimodal или неизвестного типа, используем default_provider_name, если он подходит
             if self.default_provider_name in self.providers and hasattr(self.providers[self.default_provider_name], 'process_multimodal_request'):
                selected_provider_name_for_multimodal = self.default_provider_name
             else: # Иначе ищем первый подходящий
                potential_providers = ["gpt4", "claude", "mock"]
                for p_name in potential_providers:
                    if p_name in self.providers and hasattr(self.providers[p_name], 'process_multimodal_request'):
                        selected_provider_name_for_multimodal = p_name
                        break
             logging.info(f"Using provider '{selected_provider_name_for_multimodal}' for multimodal task_type: '{task_type}'")

        provider = self.get_provider(selected_provider_name_for_multimodal)

        if not hasattr(provider, 'process_multimodal_request'):
            logging.error(f"Provider {provider.name} selected for multimodal task but does not support it. Critical fallback error.")
            return {"error": f"No suitable provider found for multimodal task '{task_type}'. Selected '{provider.name}' does not support it."}

        logging.info(f"Processing multimodal request with {provider.get_provider_name()} (Model: {provider.config.model_name}) for task type '{task_type}' using selected provider '{selected_provider_name_for_multimodal}', session: {session_id}")

        start_time = datetime.utcnow()
        try:
            response = provider.process_multimodal_request(text=text, image_url=image_url, audio_url=audio_url, context=context, session_id=session_id)
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            logging.info(f"[METRIC] Provider: {provider.get_provider_name()}, Model: {provider.config.model_name}, Type: Multimodal, Task: {task_type}, Time: {processing_time:.4f}s, Session: {session_id}, Success: True")
            return response
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            logging.error(f"[METRIC] Provider: {provider.get_provider_name()}, Model: {provider.config.model_name}, Type: Multimodal, Task: {task_type}, Time: {processing_time:.4f}s, Session: {session_id}, Success: False, Error: {str(e)}")
            raise

# Пример использования (для локального тестирования модуля):
if __name__ == "__main__":
    # Для тестирования, установите переменные окружения:
    # Например:
    # export NLP_PROVIDERS="mock,gpt4,claude"
    # export DEFAULT_NLP_PROVIDER="mock"
    # export MOCK_MODEL_NAME="mock-base-model"
    # export GPT4_API_KEY="" # Оставьте пустым для теста заглушки GPT4
    # export GPT4_MODEL_NAME="gpt-4-vision-preview"
    # export CLAUDE_API_KEY="" # Оставьте пустым для теста заглушки Claude
    # export CLAUDE_MODEL_NAME="claude-3-haiku-20240307"


    # Можно также создать специфичного "дешевого" мок-провайдера для FAQ
    # os.environ['NLP_PROVIDERS'] = os.getenv('NLP_PROVIDERS', "") + ",mock_faq"
    # os.environ['MOCK_FAQ_MODEL_NAME'] = "super-fast-faq-model"
    # if "mock_faq" not in NLPService.available_provider_classes: # Динамическое добавление для теста
    #     class MockFAQProvider(MockNLPProvider):
    #         pass # Просто чтобы иметь другой класс для выбора
    #     NLPService.available_provider_classes["mock_faq"] = MockFAQProvider # type: ignore


    print("--- Testing NLPService ---")
    # Устанавливаем переменные окружения для теста fine-tuning и памяти
    os.environ['NLP_PROVIDERS'] = "mock,gpt4,claude"
    os.environ['DEFAULT_NLP_PROVIDER'] = "mock"
    os.environ['MOCK_MODEL_NAME'] = "mock-base"
    os.environ['MOCK_FINETUNE_MODEL_ID'] = "ft:mock-model:my-org:my-dataset:12345xyz"
    os.environ['GPT4_MODEL_NAME'] = "gpt-4-base"
    os.environ['GPT4_FINETUNE_MODEL_ID'] = "ft:gpt-4:my-org:another-dataset:67890abc"
    os.environ['FINETUNING_ENABLED_PROVIDERS'] = "mock,gpt4" # Включаем fine-tuning для mock и gpt4

    service = NLPService()

    print(f"\nAvailable providers: {list(service.providers.keys())}")
    print(f"Default provider: {service.default_provider_name}")
    for name, prov in service.providers.items():
        print(f"Provider '{name}' is using model: '{prov.config.model_name}' (API Key set: {bool(prov.config.api_key)})")


    # --- Тесты текстовых запросов ---
    print("\n--- Testing Text Requests ---")
    # 1. Общий запрос к default (mock с fine-tuned моделью)
    session_1_id = "session_test_123"
    print(f"\n1. Text request to default (mock fine-tuned) - session {session_1_id}, turn 1:")
    response1 = service.process_text("Hello, what is your name?", session_id=session_1_id)
    print(f"Response: {response1}")

    print(f"\n2. Text request to default (mock fine-tuned) - session {session_1_id}, turn 2 (with memory):")
    response2 = service.process_text("Can you remember my previous question?", session_id=session_1_id)
    print(f"Response: {response2}")
    assert response2.get("history_processed") == True

    # 3. Запрос к gpt4 (с fine-tuned моделью, если API ключ не задан, будет mock)
    print(f"\n3. Text request to gpt4 (fine-tuned or mock if no API key) - new session:")
    response3 = service.process_text("Explain the concept of zero-knowledge proofs.", provider_name="gpt4", session_id="session_gpt4_abc")
    print(f"Response: {response3}")

    # 4. Запрос к claude (без fine-tuning, т.к. не включен в FINETUNING_ENABLED_PROVIDERS)
    print(f"\n4. Text request to claude (base model) - new session:")
    response4 = service.process_text("What are the latest advancements in AI?", provider_name="claude", session_id="session_claude_def")
    print(f"Response: {response4}")
    if "claude" in service.providers: # Проверка, что используется базовая модель
        assert service.providers["claude"].config.model_name == os.getenv("CLAUDE_MODEL_NAME", "claude-3-opus")


    # --- Тесты мультимодальных запросов ---
    print("\n--- Testing Multimodal Requests ---")
    session_mm_1_id = "session_multimodal_789"
    # 5. Мультимодальный запрос к default (mock fine-tuned)
    print(f"\n5. Multimodal request to default (mock fine-tuned) - session {session_mm_1_id}, turn 1:")
    response_mm1 = service.process_multimodal(
        text="What is depicted in this image and how does it relate to the sound?",
        image_url="http://example.com/image1.jpg",
        audio_url="http://example.com/audio1.mp3",
        session_id=session_mm_1_id
    )
    print(f"Response: {response_mm1}")

    print(f"\n6. Multimodal request to default (mock fine-tuned) - session {session_mm_1_id}, turn 2 (with memory):")
    response_mm2 = service.process_multimodal(
        text="Based on our last interaction, what should I look for next?",
        session_id=session_mm_1_id
    )
    print(f"Response: {response_mm2}")
    assert response_mm2.get("history_processed") == True


    # --- Тесты Multi-intent (имитация в MockNLPProvider) ---
    print("\n--- Testing Multi-Intent (Mock Provider) ---")
    # 7. Запрос с "и" для имитации multi-intent к mock
    print(f"\n7. Text request with 'and' to mock for multi-intent:")
    response_multi_intent = service.process_text("Tell me a joke and what is the weather like?", provider_name="mock")
    print(f"Response: {response_multi_intent}")
    if response_multi_intent.get("provider") == "MockNLPProvider":
      assert len(response_multi_intent.get("intents", [])) > 1, "Mock provider should simulate multi-intent"

    # Очистка переменных окружения, если они были установлены только для этого теста
    del os.environ['NLP_PROVIDERS']
    del os.environ['DEFAULT_NLP_PROVIDER']
    del os.environ['MOCK_MODEL_NAME']
    del os.environ['MOCK_FINETUNE_MODEL_ID']
    del os.environ['GPT4_MODEL_NAME']
    del os.environ['GPT4_FINETUNE_MODEL_ID']
    del os.environ['FINETUNING_ENABLED_PROVIDERS']

    print("\n--- Testing NLPService Complete ---")
