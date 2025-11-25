FROM python:3.10.13

ENV PYTHONUNBUFFERED True

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y libreoffice # Install libreoffice for conversion docx to pdf on Linux

COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY . /app

ENTRYPOINT ["pytest", "-v", "src/validation_test"]