FROM python:3.13.3-alpine
WORKDIR /smtp-gateway
COPY . .
RUN python -m venv venv && \
    . ./venv/bin/activate && \
    pip install --no-cache-dir -r ./requirements.txt
EXPOSE 25
CMD ["/smtp-gateway/venv/bin/python", "-u", "main.py", "-p", "25", "-a"]