# katana/agents/suggest_agent.py

from typing import List, Dict, Optional
import re

class SuggestAgent:
    def __init__(self):
        # Статический словарь для быстрого поиска (режим 1)
        self.static_commands = {
            "отмен": ["katana cancel <task_id>"],
            "лог": ["katana log", "katana log --error"],
            "истор": ["katana history", "katana history --user"],
            "статус": ["katana status"],
            "флеш": ["katana flush"],
            "помощь": ["/help", "/commands"],
        }
        # TODO: сюда можно подгрузить CLI-манифест или NLP модель

    def suggest_static(self, user_input: str) -> List[str]:
        """
        Простой режим: поиск по ключевым подстрокам в статическом словаре
        """
        user_input = user_input.lower()
        suggestions = []
        for key, cmds in self.static_commands.items():
            if key in user_input:
                suggestions.extend(cmds)
        return suggestions

    def suggest_semantic(self, user_input: str, context: Optional[Dict] = None) -> List[str]:
        """
        Средний уровень: семантический поиск с использованием NLP (заглушка)
        - Здесь можно подключить embeddings, cosine similarity и т.п.
        """
        # Пока-заглушка: отдаем static, но в будущем — свой интеллект
        return self.suggest_static(user_input)

    def suggest_llm(self, user_input: str, context: Optional[Dict] = None) -> List[str]:
        """
        Топовый режим: генерация через LLM (OpenAI, Anthropic, др.)
        - Формируем prompt с контекстом
        - Парсим ответ LLM в список предложений
        """
        # Псевдо-код:
        # prompt = f"User input: {user_input}\nSuggest commands:"
        # response = llm_api_call(prompt)
        # suggestions = parse_response(response)
        # return suggestions

        # Для демо — просто вызываем static
        return self.suggest_static(user_input)

    def suggest(self, user_input: str, context: Optional[Dict] = None, mode: str = "static") -> List[str]:
        """
        Универсальный метод: выбирает режим работы
        """
        if mode == "static":
            return self.suggest_static(user_input)
        elif mode == "semantic":
            return self.suggest_semantic(user_input, context)
        elif mode == "llm":
            return self.suggest_llm(user_input, context)
        else:
            raise ValueError(f"Unknown suggest mode: {mode}")


# Тестовый запуск
if __name__ == "__main__":
    agent = SuggestAgent()
    test_inputs = [
        "хочу отменить задачу",
        "покажи логи с ошибками",
        "какой статус?",
        "как очистить очередь",
        "помощь",
    ]
    for text in test_inputs:
        print(f"> {text}")
        print("Suggestions:", agent.suggest(text, mode="static"))
