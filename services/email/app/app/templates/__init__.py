from app.templates.template import Template


def create_template(product: str) -> Template:
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
