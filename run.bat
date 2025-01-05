@echo off

SET VENV_FILE=.\venv

echo Checking virtual environment...

IF NOT EXIST "%VENV_FILE%" (
  echo Setting up virtual environment...
  WHERE /R %SystemDrive%\ python.exe >nul 2>&1
  IF %ERRORLEVEL% EQU 0 (
    python -m venv venv
  ) ELSE (
    WHERE /R %SystemDrive%\ python3.exe >nul 2>&1
    IF %ERRORLEVEL% EQU 0 (
      python3 -m venv venv
    ) ELSE (
      echo *** Python not found! ***
      PAUSE
      EXIT /B 1
    )
  )
  echo Virtual environment: %VENV_FILE%
) ELSE (
  echo Activating virtual environment...
  CALL .\venv\Scripts\activate
)

echo Installing Requirement Library...
pip install -r requirements.txt

echo *** SMTP Switcher ***

echo Starting SMTP Switcher server...
python main.py %*