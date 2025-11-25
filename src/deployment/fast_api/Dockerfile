FROM python:3.10.13

ENV PYTHONUNBUFFERED True

WORKDIR /app


COPY requirements.txt /app/requirements.txt


RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt


COPY . /app

EXPOSE 8080

CMD ["python", "src/deployment/fast_api/main.py"]