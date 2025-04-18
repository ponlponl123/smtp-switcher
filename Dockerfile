FROM python:3.14.0a7-alpine3.21
WORKDIR /smtp-gateway
COPY . .
RUN pip install -r ./requirements.txt
EXPOSE 25
CMD [ "python", "main.py" ]