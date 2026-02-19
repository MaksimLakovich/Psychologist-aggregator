from django.shortcuts import render


def ratelimited_view(request, exception=None):
    """Отображает понятную страницу для случаев превышения лимитов запросов (django-ratelimit).
    Красивая обработка ошибок 403 и 429."""

    context = {
        "title_ratelimit_view": "Слишком много запросов",
        "message": "Слишком много повторяющихся запросов. Пожалуйста, проверьте данные и повторите попытку позже!",
    }

    return render(request, "users/ratelimited.html", context, status=429)
