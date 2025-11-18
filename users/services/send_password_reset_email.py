from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def send_password_reset_email(user):
    """Отправляет письмо со ссылкой для восстановления пароля (HTML + текстовая версия)."""

    # Генерирую зашифрованный ID пользователя
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    # Генерирую уникальный токен для подтверждения (работает как пароль на одноразовую ссылку)
    token = default_token_generator.make_token(user)
    # Строю ссылку для сброса пароля
    reset_url = f"{settings.FRONT_BASE_URL}/users/password-reset-confirm/?uid={uid}&token={token}"

    subject = "Восстановление пароля"
    from_email = settings.DEFAULT_FROM_EMAIL  # Отправитель в письме
    to = [user.email]  # Адресат письма

    text_content = (
        "Здравствуйте!\n\n"
        "Вы запросили восстановление пароля.\n\n"
        "Для смены пароля перейдите по ссылке:\n"
        f"{reset_url}\n\n"
        "Если вы не запрашивали восстановление пароля, просто проигнорируйте это письмо."
    )

    html_content = (
        "<p>Здравствуйте!</p>"
        "<p>Вы запросили восстановление пароля.</p>"
        f'<p><a href="{reset_url}">Нажмите здесь, чтобы сменить пароль</a></p>'
        "<p>Если вы не запрашивали восстановление пароля, просто проигнорируйте это письмо.</p>"
    )

    # Создаем мультиформатное письмо вместо обычного send_mail()
    msg = EmailMultiAlternatives(subject, text_content, from_email, to)
    msg.attach_alternative(html_content, "text/html")
    msg.send()
