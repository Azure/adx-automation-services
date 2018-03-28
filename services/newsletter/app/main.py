from datetime import datetime, timedelta
from util import (
    PRODUCTS,
    get_receivers,
    get_template,
    http_get,
    logger,
    send_email
)
import templates

def main() -> None:
    logger.info('sending weekly email')
    products = PRODUCTS.split(',')
    for product in products:
        logger.info(f'sending email for product {product}')
        receivers = get_receivers(product)
        template_url = get_template(product)

        before = (datetime.now().date() - timedelta(days=1))
        after = (before - timedelta(days=6)) # results are inclusive
        params = {
            'product': product,
            'before': before.strftime('%m-%d-%Y'),
            'after': after.strftime('%m-%d-%Y')
        }

        runs = http_get('runs', params=params)
        logger.info(f'got runs from {after} to {before}')

        all_tasks = []
        for run in runs:
            run_id = run['id']
            tasks = http_get(f'run/{run_id}/tasks')
            for task in tasks:
                all_tasks.append(task)
        logger.info('got all tasks from runs')

        content, subject = templates.render(template_uri=template_url, runs=runs,
                                            tasks=all_tasks, after=after, before=before)
        logger.info('rendered email content')

        send_email(receivers, subject, content)
        logger.info('email sent')


if __name__ == "__main__":
    main()
