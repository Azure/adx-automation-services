import templates.azurecli as azurecli
import templates.azuresdkforgo as azuresdkforgo
import templates.generic as generic

class Email(object):
    def __init__(self, product: str):
        if product == 'azuresdkforgo':
            self._template = azuresdkforgo.TemplateGo
        elif product == 'azurecli':
            self._template = azurecli.TemplateCLI
        elif product == 'generic':
            self._template = generic.TemplateGeneric
        else:
            raise NotImplementedError

    def get_context(self, run: dict, tasks: dict) -> dict:
        return self._template.get_context(self._template, run, tasks)

    def get_subject(self, run: dict, tasks: dict) -> dict:
        return self._template.get_subject(self._template, run, tasks)
