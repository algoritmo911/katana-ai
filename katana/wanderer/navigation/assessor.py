from typing import List, Dict
# from katana.services.llm_client import llm_client # Предполагаемый LLM клиент

class LinkAssessor:
    _SYSTEM_PROMPT_TEMPLATE = """
    Ты — 'Штурман', AI-агент, оценивающий релевантность гиперссылок.
    Твоя задача — на основе текущей исследовательской миссии и контекста ссылки
    присвоить каждой ссылке 'оценку релевантности' от 0.0 до 1.0.

    # ИССЛЕДОВАТЕЛЬСКАЯ МИССИЯ:
    {mission_goal}

    # ДАННЫЕ ДЛЯ АНАЛИЗА (список JSON-объектов):
    {links_data}

    # ИНСТРУКЦИИ:
    1. Для каждой ссылки проанализируй её текст (anchor) и окружающий текст (context).
    2. Сопоставь семантику ссылки с целью миссии.
    3. Присвой оценку релевантности. 1.0 — ссылка напрямую ведет к цели, 0.0 — мусор.
    4. Верни ТОЛЬКО JSON-массив объектов в формате `[{{"url": "...", "relevance": 0.X}}]`.
    """

    async def assess(self, links_with_context: List[Dict], mission_goal: str) -> List[Dict]:
        """
        Оценивает список ссылок и возвращает их с приоритетом.
        'links_with_context' - это список словарей, например:
        [{'url': 'http://...', 'anchor': 'наша статья', 'context': '...текст вокруг ссылки...'}]
        """
        if not links_with_context:
            return []

        prompt = self._SYSTEM_PROMPT_TEMPLATE.format(
            mission_goal=mission_goal,
            links_data=str(links_with_context)
        )

        # response_json = await llm_client.generate_json_response(prompt)
        # return response_json # Вернет список словарей

        # Заглушка для тестирования
        print("ASSESSOR: Используется заглушка для оценки ссылок.")
        return [
            {"url": link['url'], "relevance": 0.85} for link in links_with_context
        ]
