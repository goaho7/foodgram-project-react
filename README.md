### Описание
Проект "Foodgram" представляет собой удобный "продуктовый помощник". В рамках этого сервиса зарегистрированные пользователи могут делиться своими рецептами, подписываться на публикации других пользователей, добавлять понравившиеся рецепты в список "Избранное" и загружать список продуктов, необходимых для приготовления выбранных блюд, перед походом в магазин. Неавторизованные пользователи могут просматривать рецепты и страницы авторов.

### Используемые технологии

- Python
- Django
- Django Rest framework
- Docker
- Postgres
- Nginx

### Запуск проекта локально:

Клонировать репозиторий и перейти в директорию infra:

``` git@github.com:goaho7/foodgram-project-react.git ``` 
``` cd foodgram-project-react/infra ``` 

Запустить docker-compose:

```
docker compose up

```

Выполнить вход в контейнер backend:

```
docker exec -it backend bash

```
Выполнить миграции:

```
python manage.py migrate
```
Создать суперпользователя:
```
python manage.py createsuperuser
```

## Запуск проекта на сервере:

#### В разделе secrets создать:

##### Параметры удалённого сервера:
    SSH_KEY
    SSH_PASSPHRASE
    USER
    HOST
    
##### Логин и пароль DockerHUB:
    DOCKER_PASSWORD
    DOCKER_USERNAME
    
##### Параметры бызы данных:
    POSTGRES_DB
    POSTGRES_PASSWORD
    POSTGRES_USER
    DB_HOST
    DB_PORT

##### Скопировать на сервер файл .env
```
scp -i path_to_SSH/SSH_name .env username@server_ip:/home/username/foodgram/.env
```
Либо создайте на сервере пустой файл .env и с помощью редактора nano добавьте в него содержимое из локального .env

#### Выполнить команды:

- git add .
- git commit -m "Коммит"
- git push

Эти команды запустят workflow:
- проверка кода на PEP8 (flake8)
- сборка и отправка на Docker Hub контейнеров backend и frontend
- автоматический деплой на сервер

##### Создать суперюзера и загрузить в базу данные ингредиентов:
```
sudo docker compose -f docker-compose.production.yml exec backend python manage.py createsuperuser
sudo docker compose -f docker-compose.production.yml exec backend python manage.py loading_ingredients
```

### Автор проекта:

[Александр Савельев](https://github.com/goaho7)