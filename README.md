### Подготовка окружения

Для того чтобы развернуть проект для разработки, необходимо пройти следующие шаги:

```bash
# клонировать проект
git clone git@github.com:vkitaebiz/adv_bot.git

# создать виртуальное окружение
python3 -m venv adv_bot-env

# активировать это виртуальное окружение
source adv_bot-env/bin/activate

# запустить Redis
docker run -d --rm --net=host --name redis redis

# запустить PostgreSQL
docker run -d --rm --name postgres-lotb -v "$(pwd)"/_postgres:/var/lib/postgresql/data -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:16-alpine

# создать базу adv_bot
docker run --rm -it --link postgres-lotb:postgres -e PGPASSWORD=postgres postgres:16-alpine createdb -h postgres -U postgres adv_bot

# перейти в adv_bot и накатить миграции
alembic upgrade head
```

После всего этого нужно положить в корень проекта `setting.yaml`, который можно получить у Андрея.

### Запуск ботов

```bash
python admin_bot_run.py
python client_bot_run.py
```
