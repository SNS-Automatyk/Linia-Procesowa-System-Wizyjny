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

Aby uruchomić testowy serwer udający PLC snap7 (do testów bez fizycznego PLC), użyj:
```
python -m snap7.server --port 102
```

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

## Ewaluacja i strojenie wykrywania kół (HoughCircles)

W repozytorium znajduje się skrypt, który pozwala przetestować i wystroić parametry detektora kół na zestawie zapisanych obrazów.

Plik: `src/tests/saved_images_test.py`

Co robi skrypt:
- wczytuje obrazy z podanego katalogu (rekurencyjnie),
- uruchamia `detect_circles` na każdym obrazie,
- sprawdza, czy wykryto dokładnie 1 koło (kryterium poprawności),
- opcjonalnie wykonuje przeszukiwanie siatką (grid search) dla pary parametrów `param1` i `param2` funkcji `cv.HoughCircles`,
- pokazuje pasek postępu (wykorzystuje `rich` – jest w requirements), z lekkim fallbackiem gdy `rich` nie jest dostępny,
- opcjonalnie zapisuje podglądy (np. krawędzi) do katalogu `output_images`.

Uruchomienie (dwa sposoby wskazania katalogu z obrazami):
- przez zmienną środowiskową:
    ```bash
    IMAGES_PATH=../wizja_zdjecia/raw python -m src.tests.saved_images_test
    ```
- albo parametrem `--images`:
    ```bash
    python -m src.tests.saved_images_test --images ../wizja_zdjecia/raw
    ```

Jeśli na Twoim systemie komenda `python` nie istnieje (macOS często używa `python3`), użyj:
```bash
python3 -m src.tests.saved_images_test --images ../wizja_zdjecia/raw
```

### Tryb przeszukiwania siatką (grid search)
Skrypt może automatycznie przetestować wiele kombinacji `param1` (próg Canny) i `param2` (próg akumulatora) i wyświetlić najlepsze ustawienia.

Szybka siatka (krótki czas wykonywania):
```bash
python -m src.tests.saved_images_test \
    --images ../wizja_zdjecia/raw \
    --search \
    --p1 80:140:30 \
    --p2 25:55:15 \
    --topk 3
```

Domyślne zakresy (gęstsze):
- `--p1 80:240:20`
- `--p2 20:80:5`

Znaczenie parametrów:
- `param1` – górny próg dla Canny (wewnętrznie używane są progi `param1/2` i `param1`),
- `param2` – próg akumulatora dla środków okręgów (ile „głosów” potrzeba, by uznać środek koła).

Po zakończeniu zobaczysz zestawienie najlepszych kombinacji, np.:
```
== Najlepsza kombinacja ==
param1=120, param2=35 -> OK=45/50 (zero=4, >1=1)

Top kombinacje:
 1. p1=120, p2=35 -> OK=45/50 (90.0%), zero=4, >1=1
 2. p1=100, p2=35 -> OK=44/50 (88.0%), zero=5, >1=1
 3. p1=140, p2=30 -> OK=43/50 (86.0%), zero=6, >1=1
```

Możesz następnie użyć wskazanych parametrów przekazując je do `detect_circles` przez argument `params={"param1": X, "param2": Y}` lub w miejscu wywołania funkcji w Twoim pipeline.

### Zapis podglądów do plików
Aby przy debugowaniu podejrzeć krawędzie (lub adnotacje), uruchom z `--save`:
```bash
python -m src.tests.saved_images_test --images ../wizja_zdjecia/raw --save
```
Przetworzone obrazy trafią do `output_images/` z zachowaniem struktury katalogów względem źródłowego folderu.

Wskazówki praktyczne:
- Zawężaj `minRadius/maxRadius` w `src/config.py` pod swoje obiekty – to ułatwia dobre dopasowanie Hougha.
- Przy zbyt wielu fałszywych detekcjach podnoś `param2` i/lub `param1`.
- Gdy gubisz słabsze koła – obniż `param2` i/lub `param1`.
- `dp` (w `HoughCircles`) większe niż 1 przyspiesza kosztem precyzji; przy większym `dp` zwykle trzeba nieco obniżyć `param2`.

## Konfiguracja produkcyjna
Instrukcje dotyczące konfiguracji produkcyjnej znajdują się w pliku [`production.md`](production.md).

## Autorzy
Projekt stworzony w ramach prac nad systemem wizyjnym dla linii procesowej przez zespół SNS Automatyk PWr:
- [Marvin Ruciński](https://github.com/marvinrucinski)
- Zuzanna Gorczyca