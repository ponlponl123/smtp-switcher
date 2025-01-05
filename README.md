# smtp-switcher

this solution for who have more than one smtp endpoint server and mail server can only send one smtp endpoint

## how to configure

* `-p <number>` or `--port <number>`
  the port of your smtp server (default: 25)

* `-a` or `--public`
  host smtp server on `0.0.0.0`

## how to run

* windows

  ```cmd
  ./run.bat
  ```

* linux

  ```bash
  bash run.sh
  ```

## relayers.json

example:

```json
  {
    "example.com": {
      "host": "smtp.example.com",
      "username": "my_smtp",
      "password": "psw123456",
      "port": 587
    },
    "gmail.com": {
      "host": "smtp.gmail.com",
      "username": "google",
      "password": "gg123456",
      "port": 465
    }
  }
```

## note

* smtp server must support STARTTLS

* this is a simple solution, you may need to handle error, retry, and so on according to your needs.
