FROM 3.14.0a7-alpine3.21
WORKDIR /smtp-gateway
COPY . .
RUN pip install -r ./requiirements.txt
EXPOSE 25
CMD [ "python", "main.py" ]