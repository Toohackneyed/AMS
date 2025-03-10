# Gumamit ng opisyal na Python image
FROM python:3.11

# I-set ang environment variables
ENV PYTHONUNBUFFERED=1

# I-set ang working directory
WORKDIR /app

# I-update at i-install ang dependencies na kailangan
RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake \
    build-essential \
    python3-dev \
    libmariadb-dev-compat \
    libmariadb-dev \
    libssl-dev \
    libffi-dev \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Kopyahin ang requirements file at i-install ang dependencies
COPY ./requirements.txt /app/requirements.txt
RUN pip install --default-timeout=100 --no-cache-dir --progress=off -r requirements.txt

# Kopyahin ang natitirang Django project files
COPY . .

# Expose port 8000
EXPOSE 8000

# Opsyonal: Collect static files kung kailangan
RUN python manage.py collectstatic --noinput || echo "No static files to collect."

# I-run ang Django server (palitan kung production)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
