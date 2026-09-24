# Используем официальный образ Python
FROM python:3.12-slim

# Устанавливаем зависимости для PostgreSQL
RUN apt-get update && apt-get install -y libpq-dev gcc

# Устанавливаем Poetry
RUN pip install poetry

# Устанавливаем рабочую директорию
WORKDIR /home/app

# Копируем файлы Poetry для установки зависимостей
COPY pyproject.toml poetry.lock /home/app/

# Устанавливаем зависимости
RUN poetry config virtualenvs.create false && poetry install --no-root

# Копируем код приложения
COPY . /home/app

# Создаем папки для статических и медиафайлов
RUN mkdir -p /static /media
