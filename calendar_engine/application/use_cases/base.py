from abc import ABC, abstractmethod


class AbsUseCase(ABC):
    """Базовый контракт application use-case.

    Use-case:
        - описывает прикладной сценарий (application workflow);
        - оркестрирует доменные сервисы;
        - НЕ содержит бизнес-логики;
        - возвращает DTO доменного слоя."""

    @abstractmethod
    def execute(self, *args, **kwargs):
        """Запускает прикладной сценарий.

        Метод execute():
            - является единым входом в use-case;
            - скрывает внутренние шаги сценария;
            - вызывается из внешних слоев (aggregator, API, jobs и т.д.)."""
        raise NotImplementedError
