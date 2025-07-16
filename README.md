Структура проекта:

bankruptcy_scoring_system/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   ├── data_normalizer.py
│   ├── external_parsers.py
│   ├── scoring_engine.py
│   ├── proxy_manager.py
│   ├── config.py
│   └── captcha_solver.py
├── data/
├── static/
│   └── styles.css
├── templates/
│   └── index.html
├── proxies.txt
├── requirements.txt
└── Dockerfile


Добавьте ключи
export CAPTCHA_API_KEY=ваш_ключ_от_anti-captcha
export FEDRESURS_API_KEY=ваш_ключ_Федресурс

Для запуска системы:

Поместите CSV-файлы в папку data/

Добавьте реальные прокси в proxies.txt

Установите зависимости: pip install -r requirements.txt

Запустите сервер: uvicorn app.main:app --reload --port 8000

Откройте в браузере: http://localhost:8000

