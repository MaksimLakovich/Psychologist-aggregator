from calendar_engine.domain.matching.dto import MatchResultDTO


def map_match_result_to_dict(result: MatchResultDTO) -> dict:
    """Адаптирует MatchResultDTO в JSON-совместимый формат для API.
    Потому что web-слой НЕ работает с доменными DTO напрямую.

    ВАЖНО:
        - slot.day и slot.start уже находятся в локальной TZ специалиста;
        - timezone специалиста передается отдельно в контракте;
        - start_time сериализуется как локальное время специалиста.
    """
    return {
        "status": "matched" if result.has_match else "no_match",
        "matched_slots": [
            {
                "day": slot.day.isoformat(),
                "start_time": slot.start.strftime("%H:%M"),
            }
            for slot in result.matched_slots
        ],
    }
