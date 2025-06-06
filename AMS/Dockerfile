FROM python:3.11-slim-bullseye
ENV PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    cmake \
    build-essential \
    python3-dev \
    libmariadb-dev-compat \
    libmariadb-dev \
    libssl-dev \
    libffi-dev \
    libgl1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
COPY ./requirements.txt /app/requirements.txt
RUN pip install --default-timeout=100 --no-cache-dir --progress=off -r requirements.txt
COPY . .
EXPOSE 8000
RUN python manage.py collectstatic --noinput || echo "No static files to collect."
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]