# lambda base image for Docker from AWS
FROM python:3.12.2-slim

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

RUN chmod +x run.sh

CMD ["./run.sh"]