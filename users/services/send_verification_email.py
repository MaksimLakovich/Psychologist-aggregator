from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def send_verification_email(user):
    """Метод отправки email пользователю для подтверждения регистрации."""
    # Генерирую зашифрованный ID пользователя
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    # Генерирую уникальный токен для подтверждения (работает как пароль на одноразовую ссылку)
    token = default_token_generator.make_token(user)
    # Строю ссылку для активации
    verification_url = f"{settings.FRONT_BASE_URL}/users/verify-email/?uid={uid}&token={token}"

    subject = "Подтверждение регистрации"
    from_email = settings.DEFAULT_FROM_EMAIL  # Отправитель в письме
    to = [user.email]  # Адресат письма

    text_content = f"Для подтверждения регистрации перейдите по ссылке:\n{verification_url}"
    html_content = f"""
        <p>Здравствуйте!</p>
        <p>Для подтверждения регистрации нажмите на ссылку ниже:</p>
        <p><a href="{verification_url}">Подтвердить email</a></p>
        <br>
        <p>Если вы не регистрировались - просто игнорируйте это письмо.</p>
    """

    msg = EmailMultiAlternatives(subject, text_content, from_email, to)
    msg.attach_alternative(html_content, "text/html")
    msg.send()
