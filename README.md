````markdown
# Bankruptcy Scoring System

Система для автоматизированного скоринга потенциальных банкротств организаций на основе данных из различных внешних источников.

## 🚀 Быстрый старт

### 1. Клонирование репозитория
```bash
git clone https://github.com/AlexAvdeev1986/bankruptcy_scoring_system.git
cd bankruptcy_scoring_system
````

### 2. Создание и активация виртуального окружения (Python 3.9)

```bash
python3.9 -m venv venv
source venv/bin/activate
python3.9 --version  # убедитесь, что использовалась версия 3.9
pip install --upgrade pip
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Конфигурация переменных окружения

```bash
export CAPTCHA_API_KEY=<ваш_ключ_от_anti-captcha>
export FEDRESURS_API_KEY=<ваш_ключ_Федресурс>
```

### 5. Где получить API-ключи

#### 5.1. CAPTCHA\_API\_KEY (Anti-Captcha)

* **Источник**: \[anti-captcha.com]
* **Как получить**:

  1. Зарегистрируйтесь на anti-captcha.com.
  2. Перейдите в раздел **API Setup** в личном кабинете.
  3. Скопируйте ваш **Client Key** (32-символьный hex-ключ).
* **Пример ключа**: `174faff8fbc769e94a5862391ecfd010`
* **Цены**:

  * reCAPTCHA: от \$0.95 до \$2 за 1000 капч.
  * ImageCaptcha: от \$0.5 за 1000 капч.
  * Автоматические скидки при больших объемах.

#### 5.2. FEDRESURS\_API\_KEY (Федресурс)

* **Источник**: Федресурс (раздел **Для разработчиков**).
* **Как получить**:

  1. Зарегистрируйтесь на сайте Федресурса как разработчик.
  2. Подайте заявку на доступ к API.
  3. После модерации получите 32-символьный ключ.
* **Пример ключа**: `d3a4f5b6c7d8e9f0a1b2c3d4e5f6a7b8`
* **Условия**:

  * Ключи выдаются только юридическим лицам после проверки документов.
  * Бесплатный тестовый период: 14 дней.
  * Тарифы после тестового периода: от 15 000 ₽/месяц.

### 6. Подготовка данных и прокси

* Поместите CSV-файлы с входными данными в папку `data/`.
* Добавьте реальные HTTP(S) прокси в файл `proxies.txt`, по одному прокси на строку.

### 7. Запуск сервера разработки

```bash
python -m uvicorn app.main:app --reload --port 8000
```

Откройте в браузере: `http://localhost:8000`

## 📁 Структура проекта

```
bankruptcy_scoring_system/
├── app/                  # Основной код приложения
│   ├── __init__.py
│   ├── main.py           # Точка входа: FastAPI сервер
│   ├── database.py       # Работа с БД (PostgreSQL/SQLite)
│   ├── data_normalizer.py# Нормализация и предобработка данных
│   ├── external_parsers.py # Парсеры внешних API (Федресурс и др.)
│   ├── scoring_engine.py # Логика расчета скоринга по правилам
│   ├── proxy_manager.py  # Менеджер прокси
│   ├── config.py         # Настройки приложения и загрузка env-переменных
│   └── captcha_solver.py # Интеграция с anti-captcha API
├── data/                 # Входные CSV-файлы
├── static/               # Статические файлы (CSS, JS)
│   └── styles.css
├── templates/            # HTML-шаблоны (Jinja2)
│   └── index.html
├── logs/                 # Логи приложения
├── exports/              # Экспорт результатов в CSV/Excel
├── proxies.txt           # Список прокси
├── requirements.txt      # Зависимости проекта
└── Dockerfile            # Докерфайл для контейнеризации
```

## ❓ Почему не используется GPT

* **Детерминированная логика**: скоринг основан на чётких правилах, без необходимости NLP.
* **Производительность**: обработка тысяч записей с GPT была бы дорогой и медленной.
* **Требования ТЗ**: техническое задание не содержит пунктов по анализу текста.

## 🐳 Docker

Сборка и запуск контейнера:

```bash
docker build -t bankruptcy_scoring_system .
docker run -d -p 8000:8000 --name bss \
  -e CAPTCHA_API_KEY=<ваш_ключ> \
  -e FEDRESURS_API_KEY=<ваш_ключ> \
  bankruptcy_scoring_system
```

## 📄 Лицензия

MIT License

```
```
