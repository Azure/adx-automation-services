from typing import List
from abc import ABCMeta, abstractmethod


class Template(metaclass=ABCMeta):
    @abstractmethod
    def get_context(self, run: dict, tasks: List[dict]) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_subject(self, run: dict, tasks: List[dict]) -> str:
        raise NotImplementedError

    @staticmethod
    def create_template(product: str) -> 'Template':
        if product == 'azuresdkforgo':
            import app.templates.azuresdkforgo
            return app.templates.azuresdkforgo.TemplateGo()
        elif product == 'azurecli':
            import app.templates.azurecli
            return app.templates.azurecli.TemplateCLI()
        elif product == 'generic':
            import app.templates.generic
            return app.templates.generic.TemplateGeneric()
        else:
            raise ValueError
