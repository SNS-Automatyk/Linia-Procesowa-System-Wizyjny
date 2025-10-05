# Linia Przenośnikowa - System Wizyjny (SNS Automatyk PWr)

Oprogramowanie systemu wizyjnego dla linii produkcyjnej. Projekt umożliwia wykrywanie obiektów oraz rozpoznawanie kolorów i kształtów (głównie kół) na podstawie obrazów z kamery. System może być używany do automatycznej inspekcji produktów na linii produkcyjnej. 
System komunikuje się z PLC (Programmable Logic Controller) za pomocą protokołu snap7, umożliwiając integrację z istniejącą infrastrukturą przemysłową.
System udostępnia interfejs wiersza poleceń (CLI) do konfiguracji i uruchamiania różnych trybów pracy, takich jak podgląd na żywo z kamery, tryb produkcyjny oraz testowanie wykrywania kół.
System udostępnia również API (napisane w FastAPI) do zdalnego monitorowania i sterowania systemem wizyjnym np. z poziomu aplikacji webowej.

## Wymagania wstępne

- Python 3.x
- OpenCV

## Instalacja

1. Zainstaluj uv (manager pakietów i środowisk wirtualnych):
    ```
    pip install uv
    ```

2. Utwórz i aktywuj środowisko wirtualne:
    ```
    uv venv
    uv activate
    ```

3. Zainstaluj wymagane pakiety:
    ```
    uv sync
    ```

2. Zainstaluj OpenCV:
Na systemach Ubuntu lub Debian możesz zainstalować OpenCV za pomocą:
    ```
    sudo apt-get install python3-opencv
    ```
    Na innych systemach możesz zainstalować go za pomocą pip:

    ```
    pip install opencv-python
    ```

2. Skonfiguruj hooki pre-commit, aby zapewnić jakość kodu:
    ```
    pre-commit install
    ```

## Wykorzystanie
Uruchom to, aby zobaczyć dostępne polecenia:

```python
python cli.py --help
```

Przykładowe polecenie uruchamiające system wizyjny z podglądem na żywo z kamery i wykrywaniem kół:
```
python cli.py --live --circles
```

Przykładowe polecenie uruchamiające połączenie z PLC snap7 i pracujące w trybie produkcyjnym:
```
python cli.py --plc --ip 192.168.0.1
```
gdzie `--ip` jest adresem IP PLC.

### FastAPI
Aby uruchomić deweloperski serwer API FastAPI, użyj następującego polecenia:
```
fastapi dev main.py
```

> **Note:**  
> Jeśli zobaczysz błąd taki jak `can't find snap7 shared library`, musisz zainstalować natywną bibliotekę snap7 (`libsnap7.so`).  
> Na Raspberry Pi lub ARM Linux uruchom następujące polecenia:
> ```
> sudo apt update
> sudo apt install git build-essential cmake
> cd /tmp
> git clone https://github.com/gijzelaerr/snap7.git
> cd snap7/build/unix
> make -f arm_v7_linux.mk -j4
> sudo cp ../bin/arm_v7-linux/libsnap7.so /usr/local/lib/
> sudo ldconfig
> ```
> Następnie spróbuj ponownie uruchomić polecenie.

## Konfiguracja
Plik konfiguracyjny `src/config.py` zawiera parametry dla systemu wizyjnego, takie jak wymiary klatki, marginesy i limity dla powtórzeń wykrywania obiektów. Możesz dostosować te parametry, aby dopasować je do swojego konkretnego przypadku użycia.

## Konfiguracja produkcyjna
Instrukcje dotyczące konfiguracji produkcyjnej znajdują się w pliku [`production.md`](production.md).

## Autorzy
Projekt stworzony w ramach prac nad systemem wizyjnym dla linii procesowej przez zespół SNS Automatyk PWr:
- [Marvin Ruciński](https://github.com/marvinrucinski)
- Zuzanna Gorczyca