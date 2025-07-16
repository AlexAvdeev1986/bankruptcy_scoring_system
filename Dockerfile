FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data exports logs

ENV CAPTCHA_API_KEY=your_anti_captcha_key
ENV FEDRESURS_API_KEY=your_fedresurs_key

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]