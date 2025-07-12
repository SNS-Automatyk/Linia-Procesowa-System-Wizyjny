import cv2 as cv


def detect_contours(
    frame, FRAME_LEFT_MARGIN, FRAME_TOP_MARGIN, FRAME_WIDTH, FRAME_HEIGHT
):
    obiektow = 0
    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    gray = cv.medianBlur(gray, 5)
    krawedzie = cv.Canny(gray, 50, 140)
    kontury, _ = cv.findContours(krawedzie, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    # Filtracja konturów: tylko te, których środek jest w ramce
    kontury_filtered = []
    for kontur in kontury:
        M = cv.moments(kontur)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            if (
                FRAME_LEFT_MARGIN <= cx < FRAME_LEFT_MARGIN + FRAME_WIDTH
                and FRAME_TOP_MARGIN <= cy < FRAME_TOP_MARGIN + FRAME_HEIGHT
            ):
                kontury_filtered.append(kontur)
    kontury = kontury_filtered
    srodki = []
    for kontur in kontury:  # dla wszystkich konturów
        prostokat = cv.minAreaRect(kontur)
        ((x, y), (szer, wys), _) = prostokat
        x = int(x)
        y = int(y)
        rysuj = 1
        if szer * wys > 2000:
            for a, b in srodki:
                if abs(a - x) < 30 or abs(b - y) < 30:
                    rysuj = 0
                    break
            if rysuj:
                obiektow = obiektow + 1
                srodki.append((x, y))

    return kontury, srodki
