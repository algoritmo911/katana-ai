import openai
from bs4 import BeautifulSoup
from bot import database

# Рекомендуемый размер чанка для моделей эмбеддингов OpenAI
MAX_CHUNK_SIZE = 8000 # 8191 токенов - это максимум, берем с запасом

class DataIngestor:
    """
    Класс для обработки, чанкинга, векторизации и сохранения
    текстовых данных в векторную базу данных.
    """
    def __init__(self):
        # Клиенты для OpenAI и Supabase будут получены по мере необходимости
        # через get_nlp_processor() и get_supabase_client()
        # но для эмбеддингов нужен отдельный клиент OpenAI
        self.openai_client = openai.OpenAI()

    def get_embedding(self, text: str, model="text-embedding-3-small") -> list[float]:
        """Получает векторное представление для текста."""
        text = text.replace("\n", " ")
        try:
            response = self.openai_client.embeddings.create(input=[text], model=model)
            return response.data[0].embedding
        except Exception as e:
            print(f"Ошибка при получении эмбеддинга: {e}")
            return None

    def _chunk_text(self, text: str) -> list[str]:
        """
        Разбивает длинный текст на семантически связанные фрагменты (чанки).
        Простая реализация: разбивка по параграфам.
        """
        chunks = text.split('\n\n')
        # TODO: Добавить более умный чанкинг, который учитывает размер токенов
        return [chunk.strip() for chunk in chunks if chunk.strip()]

    def _save_chunks(self, source: str, chunks: list[str]):
        """Векторизует и сохраняет чанки в базу данных."""
        supabase = database.get_supabase_client()
        if not supabase:
            print("Ошибка: Supabase клиент не инициализирован.")
            return

        for chunk in chunks:
            embedding = self.get_embedding(chunk)
            if embedding:
                try:
                    supabase.table('documents').insert({
                        'source': source,
                        'content': chunk,
                        'embedding': embedding
                    }).execute()
                except Exception as e:
                    print(f"Ошибка при сохранении чанка в БД: {e}")
        print(f"Сохранено {len(chunks)} чанков из источника '{source}'.")

    def ingest_text(self, content: str, source_name: str):
        """Обрабатывает и сохраняет простой текстовый файл."""
        print(f"Начинаю обработку текстового файла: {source_name}")
        chunks = self._chunk_text(content)
        self._save_chunks(source_name, chunks)

    def ingest_html(self, content: str, source_name: str):
        """Обрабатывает и сохраняет HTML файл."""
        print(f"Начинаю обработку HTML файла: {source_name}")
        soup = BeautifulSoup(content, 'html.parser')
        text_content = soup.get_text(separator='\n\n', strip=True)
        chunks = self._chunk_text(text_content)
        self._save_chunks(source_name, chunks)

    def ingest_directive(self, content: str, source_name: str):
        """Обрабатывает и сохраняет файл директивы (Markdown/YAML)."""
        # Для Markdown/YAML простой разбивки по параграфам может быть достаточно
        print(f"Начинаю обработку директивы: {source_name}")
        chunks = self._chunk_text(content)
        self._save_chunks(source_name, chunks)

# Пример использования, который будет вызываться из основного скрипта
if __name__ == '__main__':
    # Этот блок будет использоваться для запуска процесса из командной строки
    # или для тестирования модуля.

    # Моковые данные для тестирования
    test_text = "Это первая часть текста.\n\nЭто вторая часть, она о другом."
    test_html = "<html><body><h1>Заголовок</h1><p>Первый параграф.</p><p>Второй параграф.</p></body></html>"
    test_directive = "# ДИРЕКТИВА\n\n## ЗАДАЧА 1\n\nОписание задачи."

    ingestor = DataIngestor()

    # Здесь должны быть реальные вызовы с реальными данными
    # ingestor.ingest_text(test_text, "test_text.txt")
    # ingestor.ingest_html(test_html, "test_chat.html")
    # ingestor.ingest_directive(test_directive, "KRN-2025-08-11-S1")

    print("Тестовый запуск DataIngestor завершен.")
