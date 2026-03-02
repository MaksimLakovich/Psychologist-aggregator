from users.models import Topic


def build_topics_grouped_by_type():
    """Группирует темы по виду консультации и по названию группы.

    Возвращает структуру вида:
        {
            "Индивидуальная": {
                "Группа 1": [Topic, Topic],
                "Группа 2": [Topic],
            },
            "Парная": {
                ...
            }
        }

    Почему это вынесено в отдельный service:
        - одна и та же группировка нужна и странице personal-questions, и каталогу psychologist_catalog;
        - так мы держим источник истины в одном месте и не дублируем код в разных view.
    """
    topics = Topic.objects.all().order_by("type", "group_name", "name")

    grouped_topics = {
        "Индивидуальная": {},
        "Парная": {},
    }

    for topic in topics:
        type_bucket = grouped_topics.setdefault(topic.type, {})
        group_bucket = type_bucket.setdefault(topic.group_name, [])
        group_bucket.append(topic)

    return grouped_topics


def serialize_topics_grouped_by_type(topics_by_type):
    """Преобразует сгруппированные Topic-объекты в JSON-совместимый словарь.

    Это нужно для frontend-кода каталога, потому что:
        - JS не умеет напрямую работать с Python-объектами Topic;
        - в json_script лучше передавать только простые данные: id, name и type.
    """
    serialized_topics = {}

    for topic_type, grouped_topics in (topics_by_type or {}).items():
        serialized_topics[topic_type] = {}

        for group_name, topics in grouped_topics.items():
            serialized_topics[topic_type][group_name] = [
                {
                    "id": str(topic.pk),
                    "name": topic.name,
                    "type": topic.type,
                }
                for topic in topics
            ]

    return serialized_topics
