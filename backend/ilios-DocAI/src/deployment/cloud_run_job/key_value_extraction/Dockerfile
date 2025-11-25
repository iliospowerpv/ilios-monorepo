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

COPY requirements_key_extraction.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY . /app

EXPOSE 8080

ENTRYPOINT ["python", "src/deployment/cloud_run_job/key_value_extraction/main.py"]