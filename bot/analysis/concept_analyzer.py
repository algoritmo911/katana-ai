import numpy as np
import json
from sklearn.cluster import AgglomerativeClustering
from bot import database
import openai
import networkx

class ConceptAnalyzer:
    """
    Анализирует загруженные документы для идентификации концепций,
    извлечения их деталей и построения графа связей.
    """
    def __init__(self):
        self.openai_client = openai.OpenAI()
        self.documents = []
        self.embeddings = []
        self.clusters = {}

    def fetch_data(self):
        """Извлекает все документы из базы данных."""
        print("Извлечение документов из базы данных...")
        all_docs = database.get_all_documents()
        if not all_docs:
            print("В базе данных не найдено документов для анализа.")
            return False

        # Разделяем данные на документы и их векторные представления
        self.documents = all_docs

        # Эмбеддинги из Supabase приходят в виде строк '[1.23, 4.56, ...]'
        # Их нужно распарсить в списки float
        embedding_list = []
        for doc in all_docs:
            if isinstance(doc['embedding'], str):
                try:
                    # Используем json.loads, т.к. это валидный JSON-массив
                    embedding_list.append(json.loads(doc['embedding']))
                except json.JSONDecodeError:
                    print(f"Ошибка декодирования JSON для эмбеддинга документа id={doc['id']}")
                    # Пропускаем этот документ или добавляем нулевой вектор? Пока пропускаем.
                    continue
            elif isinstance(doc['embedding'], list):
                 embedding_list.append(doc['embedding'])

        self.embeddings = np.array(embedding_list)
        print(f"Загружено {len(self.documents)} документов, обработано {len(self.embeddings)} эмбеддингов.")
        return True

    def cluster_documents(self, n_clusters=None, distance_threshold=0.5):
        """
        Кластеризует документы на основе их векторных представлений.
        Можно указать либо количество кластеров, либо порог расстояния.
        """
        if self.embeddings is None or len(self.embeddings) == 0:
            print("Нет данных для кластеризации.")
            return

        print("Начало кластеризации документов...")
        # Используем агломеративную кластеризацию.
        # Она хорошо работает, когда количество кластеров неизвестно.
        # linkage='ward' требует n_clusters, поэтому используем 'average' или 'complete'
        # с distance_threshold.
        # n_clusters=None и distance_threshold не могут быть использованы одновременно.
        if n_clusters:
            clustering_model = AgglomerativeClustering(n_clusters=n_clusters, linkage='ward')
        else:
            # affinity='cosine' и linkage='average' - хорошая комбинация для текстовых векторов
            clustering_model = AgglomerativeClustering(
                n_clusters=None,
                distance_threshold=distance_threshold,
                linkage='average',
                metric='cosine'
            )

        labels = clustering_model.fit_predict(self.embeddings)

        # Группируем документы по кластерам
        for i, label in enumerate(labels):
            if label not in self.clusters:
                self.clusters[label] = []
            self.clusters[label].append(self.documents[i])

        print(f"Документы сгруппированы в {len(self.clusters)} кластеров.")

    def name_clusters(self):
        """
        Дает имя каждому кластеру, используя LLM для обобщения содержимого.
        """
        print("Начинаю именование кластеров...")
        self.named_clusters = {}

        system_prompt = (
            "Твоя задача - проанализировать набор текстовых фрагментов и дать им одно общее, "
            "краткое и осмысленное название (2-3 слова). Это название должно отражать главную тему, "
            "проект или концепцию, обсуждаемую в текстах. Отвечай только названием, без лишних слов."
        )

        for cluster_id, docs in self.clusters.items():
            # Объединяем контент всех документов в кластере
            full_text = "\n---\n".join([doc['content'] for doc in docs])

            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": full_text}
                    ],
                    temperature=0,
                )
                cluster_name = response.choices[0].message.content.strip()
                self.named_clusters[cluster_name] = docs
                print(f"Кластер {cluster_id} назван: '{cluster_name}'")
            except Exception as e:
                print(f"Ошибка при именовании кластера {cluster_id}: {e}")
                # В случае ошибки даем кластеру временное имя
                self.named_clusters[f"Неназванный кластер {cluster_id}"] = docs

    def extract_concept_details(self):
        """
        Извлекает цель, статус и риски для каждой концепции.
        """
        print("Начинаю извлечение деталей концепций...")
        self.concept_details = {}

        system_prompt = (
            "Проанализируй предоставленный текст, который описывает проект или концепцию. "
            "Твоя задача - извлечь следующую информацию и вернуть ее в виде JSON-объекта со СТРОГО следующими ключами: "
            "'goal' (цель), 'status' (статус), 'risks' (риски, списком строк). "
            "Если какая-то информация отсутствует, оставь соответствующее поле пустым или null."
        )

        for name, docs in self.named_clusters.items():
            full_text = "\n---\n".join([doc['content'] for doc in docs])

            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": full_text}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0,
                )
                details = response.choices[0].message.content
                self.concept_details[name] = json.loads(details)
                print(f"Извлечены детали для концепции: '{name}'")
            except Exception as e:
                print(f"Ошибка при извлечении деталей для '{name}': {e}")
                self.concept_details[name] = {"goal": None, "status": None, "risks": ["Ошибка анализа"]}

    def build_relationship_graph(self):
        """
        Строит граф взаимосвязей между концепциями.
        """
        print("Начинаю построение графа связей...")
        # Используем DiGraph для направленных связей (A -> использует -> B)
        self.graph = networkx.DiGraph()

        concept_names = list(self.concept_details.keys())
        for name in concept_names:
            # GML требует, чтобы атрибуты были строками или числами. Конвертируем все в строки.
            attributes = self.concept_details[name]
            sanitized_attributes = {}
            for key, value in attributes.items():
                if value is None:
                    sanitized_attributes[key] = ""
                elif isinstance(value, list):
                    sanitized_attributes[key] = ", ".join(map(str, value))
                else:
                    sanitized_attributes[key] = str(value)

            self.graph.add_node(name, **sanitized_attributes)

        # Собираем весь текст в один большой контекст
        full_context = "\n\n".join([doc['content'] for doc in self.documents])

        system_prompt = (
            "На основе предоставленного общего контекста, опиши связь между 'Проектом A' и 'Проектом B'. "
            "Ответь краткой фразой в 3-5 слов (например, 'является компонентом', 'используется для автоматизации', 'это долгосрочная цель'). "
            "Если прямой и явной связи нет, ответь словом 'None'."
        )

        # Итерируемся по всем уникальным парам концепций
        from itertools import combinations
        for concept_a, concept_b in combinations(concept_names, 2):
            prompt = (
                f"Общий контекст:\n---\n{full_context}\n---\n"
                f"Проект A: {concept_a}\n"
                f"Проект B: {concept_b}\n\n"
                "Какова связь между Проектом A и Проектом B?"
            )
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0,
                )
                relationship = response.choices[0].message.content.strip()

                if "none" not in relationship.lower():
                    # Решаем, в какую сторону направить ребро (это эвристика)
                    # Если в ответе есть слова "использует", "зависит от", то B -> A
                    if any(word in relationship for word in ["использует", "зависит от", "основан на"]):
                        self.graph.add_edge(concept_b, concept_a, label=relationship)
                        print(f"Найдена связь: {concept_b} -> {concept_a} ({relationship})")
                    else: # В остальных случаях считаем A -> B
                        self.graph.add_edge(concept_a, concept_b, label=relationship)
                        print(f"Найдена связь: {concept_a} -> {concept_b} ({relationship})")

            except Exception as e:
                print(f"Ошибка при определении связи между {concept_a} и {concept_b}: {e}")

    def run_analysis(self):
        """
        Запускает полный пайплайн анализа.
        """
        if not self.fetch_data():
            return

        self.cluster_documents()
        self.name_clusters()
        self.extract_concept_details()
        self.build_relationship_graph()

# Для запуска анализа будет использоваться отдельный скрипт
if __name__ == '__main__':
    # Примерный вызов для тестирования
    analyzer = ConceptAnalyzer()
    analyzer.run_analysis()
    print("Анализ завершен.")
