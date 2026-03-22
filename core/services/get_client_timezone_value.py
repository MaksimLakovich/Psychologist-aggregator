from core.services.anonymous_client_flow_for_search_and_booking import get_guest_matching_state


def get_client_timezone_value_for_request(request) -> str:
    """Возвращает timezone текущего участника flow в строковом виде:
        - для авторизованного клиента timezone берется из аккаунта;
        - для гостя из временного guest-anonymous-состояния в session, собранного на первом шаге подбора.
    """
    if request.user.is_authenticated:
        return str(getattr(request.user, "timezone", "") or "")

    general = get_guest_matching_state(request.session)["general"]
    return general.get("timezone", "") or ""
