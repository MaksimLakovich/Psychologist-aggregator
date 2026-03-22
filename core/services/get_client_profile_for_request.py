from core.services.anonymous_client_flow_for_search_and_booking import build_guest_profile


def get_client_profile_for_request(request):
    """Возвращает профиль, с которым дальше должен работать matching-flow:
        - если клиент уже авторизован, то используется реальный ClientProfile из БД;
        - если клиент еще гость, то используется session и временный профиль гостя.
    """
    if request.user.is_authenticated:
        return request.user.client_profile
    return build_guest_profile(request.session)
