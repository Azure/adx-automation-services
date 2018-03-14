import templates.azurecli as azurecli
import templates.azuresdkforgo as gosdk

def get_context(run: dict, tasks: dict) -> dict:
    product = run['details'].get('a01.reserved.product')

    if product == 'azuresdkforgo':
        return gosdk.get_context(run, tasks)
    else:
        return azurecli.get_context(run, tasks)

def get_subject(run: dict, tasks: dict) -> str:
    product = run['details'].get('a01.reserved.product')

    if product == 'azuresdkforgo':
        return gosdk.get_subject(run, tasks)
    else:
        return azurecli.get_subject(run, tasks)
