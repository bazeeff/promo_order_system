# Promo Order System

Тестовое задание: HTTP endpoint создания заказа с применением промокода.
Django + Django REST Framework, JWT-аутентификация, Swagger.

## Запуск (docker)

```bash
docker compose up --build     # API за nginx: http://localhost/api/v1/
```

Локально: `poetry install`, `python manage.py runserver` (нужен Postgres
из `.env`, либо docker compose db).

Тесты: `pytest api/v1 apps/mailing` (в docker: `docker compose run web pytest`).

## Эндпоинты

| Методы | URL | Назначение |
|---|---|---|
| CRUD | `/api/v1/categories/` | категории товаров |
| CRUD | `/api/v1/goods/` | товары (`?category=<id>&is_promo_excluded=`) |
| CRUD | `/api/v1/promo-codes/` | промокоды (`?is_active=&category=`) |
| POST | `/api/v1/order/` | создание заказа с промокодом |
| GET | `/api/v1/orders/` | список заказов (`?user=<id>` для админов) |
| GET | `/api/v1/orders/{id}/` | детали заказа |

Изменение справочников — только для администраторов; заказы читают
авторизованные пользователи (обычные — только свои).

### Создание заказа

```json
POST /api/v1/order/
Idempotency-Key: 7d1c4b0e-...

{
  "items": [
    {"good": "<uuid>", "quantity": 2},
    {"good": "<uuid>", "quantity": 1}
  ],
  "promocode": "WELCOME10"
}
```

`promocode` опционален, регистр и пробелы не важны. Пользователь берётся
из JWT-токена. Заголовок `Idempotency-Key` опционален: повторный запрос
с тем же ключом и телом возвращает созданный заказ (200), с другим
телом — 409.

Ответ `201`:

```json
{
  "id": "<uuid>",
  "user": "<uuid>",
  "items": [
    {"good": "<uuid>", "good_name": "Телевизор", "quantity": 2,
     "unit_price": "450.00", "discount_rate": "0.1000",
     "discount_amount": "90.00", "total": "810.00"}
  ],
  "subtotal": "900.00",
  "discount_rate": "0.1000",
  "discount_amount": "90.00",
  "total": "810.00",
  "promo": {"code": "WELCOME10", "discount_rate": "0.1000"},
  "created_at": "2026-09-28T12:00:00Z"
}
```

## Правила применения промокода

Проверяются в порядке: существование → активность → срок действия →
лимит использований → «не использован этим пользователем» →
применимость к товарам.

| Правило | Механизм | HTTP / код |
|---|---|---|
| Существует | lookup по нормализованному коду (trim/upper) | 404 `promo_not_found` |
| Активен | `is_active` | 400 `promo_inactive` |
| Не просрочен | `expires_at > now` | 400 `promo_expired` |
| Лимит использований | `used_count < max_uses`, счётчик растёт при создании заказа | 409 `promo_usage_limit_reached` |
| Один раз на пользователя | `UNIQUE(user, promo)` в `PromoRedemption` + проверка | 409 `promo_already_used` |
| Ограничение категорией | `promo.category` → скидка только на товары категории | |
| Товары вне акций | `good.is_promo_excluded` → позиция без скидки | 400 `promo_not_applicable` |

Скидка (`discount_rate` — доля от 0 до 1) применяется к подходящим
позициям, округление до копеек half-up; цены фиксируются снимком в
`OrderItem.unit_price`. Если подходящих позиций нет — заказ не создаётся.

## Импорт рассылок из XLSX

Импорт запускается management-командой; каждая строка файла — письмо,
которое ставится в отправку Celery-воркером. По условию задачи отправка
имитируется: письмо записывается в лог с задержкой
`MAILING_SEND_DELAY_SECONDS` (по умолчанию 5 c) вместо SMTP.

```bash
python manage.py import_mailings path/to/mailings.xlsx [--batch-size 500] [--dry-run]
```

Первая строка файла — заголовки колонок (порядок не важен):
`external_id`, `user_id`, `email`, `subject`, `message`.
`external_id` уникален и защищает от повторной обработки при повторном
импорте. Файл читается потоково и пишется батчами — размер не ограничен
памятью.

Пример вывода:

```
Строка 3 ошибочна: user_id не является UUID: 'bad-uuid'
Импорт завершён: обработано строк 4, создано записей 2, пропущено записей 1, ошибочных строк 1.
```

Строка считается ошибочной, если: пуст `external_id`/`subject`/`message`,
`user_id` не UUID или пользователь не найден, email некорректный. Дубли
(в файле или уже в БД) пропускаются. `--dry-run` проверяет файл, ничего
не создавая.

Статусы письма: `pending` → `sent` (ставит задача
`apps.mailing.tasks.send_mailing`, идемпотентна). Если брокер недоступен,
импорт завершается штатно, письма остаются в `pending`.

## Архитектура

```
project/
├── apps/order/
│   ├── models/       # Category, Good, PromoCode, Order, OrderItem, PromoRedemption
│   └── services.py   # OrderCreationService: транзакция, блокировка промокода, расчёт
├── apps/mailing/
│   ├── models/       # Mailing: письмо рассылки с external_id и статусом
│   ├── services.py   # MailingsImportService: потоковое чтение XLSX, батчи, валидация
│   ├── tasks.py      # send_mailing: отправка письмом в лог с задержкой
│   └── management/commands/import_mailings.py
└── api/v1/order/
    ├── serializers.py  # вход/выход для всех сущностей заказа
    ├── views.py        # OrderCreateView + ViewSet'ы справочников и заказов
    ├── filters.py      # django-filter наборы
    └── tests/          # тесты API создания заказа
```

Ключевые решения:

- **Сервисный слой.** Логика промокодов живёт в `OrderCreationService`,
  переиспользуется вне HTTP и тестируется напрямую.
- **Конкурентность.** Создание заказа — одна транзакция; строка промокода
  блокируется `SELECT ... FOR UPDATE`; ограничения уникальности
  (`uniq_promo_per_user`, `promo_used_lte_max`) страхуют от гонок.
- **Идемпотентность.** `UNIQUE(user, idempotency_key)` на заказе и
  отпечаток тела запроса: повторный запрос не создаёт дублей.
- **Деньги.** Только `Decimal`; ответ отдаёт суммы строками.
