# Instrukcja konfiguracji środowiska produkcyjnego na Raspberry Pi

Ta instrukcja pomoże Ci skonfigurować środowisko produkcyjne na Raspberry Pi dla systemu wizyjnego i panelu sterowania linii procesowej. Zakładamy, że masz już zainstalowany system operacyjny Raspberry Pi OS oraz dostęp do terminala.

## Kroki
1. **Sklonuj repozytoria z GitHub:**
   ```bash
   git clone https://github.com/SNS-Automatyk/Linia-Procesowa-System-Wizyjny system-wizyjny
   git clone https://github.com/SNS-Automatyk/Panel-Sterowania-Linia-Procesowa panel-sterowania
   ```
2. Zbuduj panel sterowania w Vue.js:
    ```bash
    cd panel-sterowania
    npm install
    npm run build
    cd ..
    ```
3. Zainstaluj wymagane pakiety dla systemu wizyjnego:
    ```bash
    cd system-wizyjny
    uv venv
    uv activate
    uv sync
    sudo apt-get install python3-opencv
    ```
4. Zainstaluj natywną bibliotekę snap7 (`libsnap7.so`):
    ```
    sudo apt update
    sudo apt install git build-essential cmake
    cd /tmp
    git clone https://github.com/gijzelaerr/snap7.git
    cd snap7/build/unix
    make -f arm_v7_linux.mk -j4
    sudo cp ../bin/arm_v7-linux/libsnap7.so /usr/local/lib/
    sudo ldconfig
    ```
4. Stwórz plik `.env` w katalogu `system-wizyjny` z następującą zawartością:
    ```
    PLC_IP=<adres_IP_sterownika>
    PLC_RACK=0 (opcjonalne)
    PLC_SLOT=1 (opcjonalne)
    PLC_PORT=102 (opcjonalne)
    CAMERA_INDEX=0 (opcjonalne)
    ```
5. Skonfiguruj autostart dla systemu wizyjnego:
    ```bash
    nano /etc/systemd/system/vision-system.service
    ```
    Wklej poniższą konfigurację, dostosowując ścieżki do swojego środowiska:
    ```
    [Unit]
    Description=FastAPI+Vue single-process
    After=network.target

    [Service]
    User=pi
    WorkingDirectory=/home/pi/myapp
    ExecStart=/home/pi/myapp/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 80
    Restart=always
    Environment=PYTHONUNBUFFERED=1

    [Install]
    WantedBy=multi-user.target
    ```
    Zapisz i zamknij plik (Ctrl+X, Y, Enter).
6. Włącz i uruchom usługę:
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable vision-system.service
    sudo systemctl start vision-system.service
    ```
7. Sprawdź status usługi:
    ```bash
    sudo systemctl status vision-system.service
    ```