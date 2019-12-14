FROM python:3.7-alpine
WORKDIR /usr/src/legolas
RUN apk update && apk add postgresql-dev gcc python3-dev musl-dev bash
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

CMD ["bash", "setup.sh"]
