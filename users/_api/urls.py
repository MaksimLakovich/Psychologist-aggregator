from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from users._api.views import (AppUserRetrieveUpdateView, ChangePasswordView,
                              ClientProfileRetrieveUpdateView,
                              CustomTokenObtainPairView,
                              EducationListCreateView,
                              EducationRetrieveUpdateDestroyView,
                              EmailVerificationView, LogoutAPIView,
                              MethodDetailView, MethodListView,
                              PasswordResetConfirmView, PasswordResetView,
                              PsychologistProfileRetrieveUpdateView,
                              PublicPsychologistProfileRetrieveView,
                              RegisterView, ResendEmailVerificationView,
                              SaveHasPreferencesAjaxView,
                              SavePreferredGenderAjaxView,
                              SavePreferredMethodsAjaxView,
                              SavePreferredTopicTypeAjaxView,
                              SaveRequestedTopicsAjaxView,
                              SpecialisationDetailView, SpecialisationListView,
                              TopicDetailView, TopicListView)
from users.apps import UsersConfig

app_name = UsersConfig.name

urlpatterns = [
    # Регистрация / подтверждения / работа с аккаунтом / работа с профилем
    path("register/psychologist/", RegisterView.as_view(), name="register-psychologist"),
    path("register/client/", RegisterView.as_view(), name="register-client"),
    path("verify-email/", EmailVerificationView.as_view(), name="verify-email"),
    path("resend-verify-email/", ResendEmailVerificationView.as_view(), name="resend-verify-email"),
    path("my-account/", AppUserRetrieveUpdateView.as_view(), name="my-account"),
    path(
        "my-psychologist-profile/",
        PsychologistProfileRetrieveUpdateView.as_view(),
        name="my-psychologist-profile"
    ),
    path("my-client-profile/", ClientProfileRetrieveUpdateView.as_view(), name="my-client-profile"),
    path(
        "psychologists/<uuid:uuid>/", PublicPsychologistProfileRetrieveView.as_view(), name="psychologist-detail"
    ),

    # Auth
    path("login/", CustomTokenObtainPairView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),

    # Пароли
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("password-reset/", PasswordResetView.as_view(), name="password-reset"),
    path("password-reset-confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),

    # Topic (справочник)
    path("topics/", TopicListView.as_view(), name="topic-list"),
    path("topics/<slug:slug>/", TopicDetailView.as_view(), name="topic-detail"),

    # Specialisation (справочник)
    path("specialisations/", SpecialisationListView.as_view(), name="specialisation-list"),
    path("specialisations/<slug:slug>/", SpecialisationDetailView.as_view(), name="specialisation-detail"),

    # Method (справочник)
    path("methods/", MethodListView.as_view(), name="method-list"),
    path("methods/<slug:slug>/", MethodDetailView.as_view(), name="method-detail"),

    # Education (CRUD психолога)
    path("educations/", EducationListCreateView.as_view(), name="education-list-create"),
    path("educations/<int:pk>/", EducationRetrieveUpdateDestroyView.as_view(), name="education-detail"),

    # AJAX-запрос (fetch) на моментальное сохранение указанных клиентом на html-страницах данных в БД
    path(
        "save-preferred-topic-type/", SavePreferredTopicTypeAjaxView.as_view(), name="save-preferred-topic-type"
    ),
    path("save-requested-topics/", SaveRequestedTopicsAjaxView.as_view(), name="save-topics"),
    path("save-has-preferences/", SaveHasPreferencesAjaxView.as_view(), name="save-has-preferences"),
    path("save-preferred-gender/", SavePreferredGenderAjaxView.as_view(), name="save-preferred-gender"),
    path("save-preferred-methods/", SavePreferredMethodsAjaxView.as_view(), name="save-methods"),
]
