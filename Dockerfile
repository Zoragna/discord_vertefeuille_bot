FROM python:3.8-buster
WORKDIR /usr/src/legolas
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

CMD ["bash", "setup.sh"]
