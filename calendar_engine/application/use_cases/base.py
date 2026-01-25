from abc import ABC, abstractmethod


class AbsUseCase(ABC):
    """Базовый контракт application use-case.

    Use-case это прикладной сценарий (application workflow), который:
        - принимает входные параметры из внешних слоев (API, jobs, UI);
        - оркестрирует доменные сервисы;
        - НЕ содержит бизнес-логики;
        - НЕ знает про БД, HTTP, пользователей;
        - возвращает DTO доменного слоя.

    ВАЖНО:
        - вся бизнес-логика живет в domain-слое;
        - use-case лишь управляет порядком шагов."""

    @abstractmethod
    def execute(self, *args, **kwargs):
        """Запускает прикладной сценарий.

        Метод execute():
            - является единой точкой входа в use-case;
            - скрывает внутренние шаги сценария;
            - вызывается из внешних слоёв (API, aggregator, background jobs)."""
        raise NotImplementedError
