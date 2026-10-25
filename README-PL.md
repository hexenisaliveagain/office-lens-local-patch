# Lokalny patch Microsoft Lens

Nieoficjalna łata do **16.0.19628.20008, kod 2004969699, ARM64**. Usuwa wymuszoną migrację
do OneDrive i przekierowanie z jej przycisku. Zawiera również poprawkę natywnego crasha z FIX1.

W paczce są skrypt, łata binarna i manifest hashy. Użytkownik dostarcza oryginalny APK oraz
własny klucz podpisu. Nie potrzebuje apktool ani dekompilatora. Microsoft nie wspiera tego projektu.

## Pobierz

[Gotowa paczka ZIP — v1.1.0](https://github.com/hexenisaliveagain/office-lens-local-patch/releases/download/v1.1.0/Lens-local-patch-1.1.0-source.zip)
· [Suma SHA-256](https://github.com/hexenisaliveagain/office-lens-local-patch/releases/download/v1.1.0/Lens-local-patch-1.1.0-source.zip.sha256)
· [Wszystkie wydania](https://github.com/hexenisaliveagain/office-lens-local-patch/releases)

Rozpakuj ZIP, otwórz terminal w rozpakowanym katalogu i wykonaj instrukcję poniżej.

## Kreator Windows

Po rozpakowaniu ZIP uruchom **`Start-Windows.cmd`** dwuklikiem i wybierz język polski lub angielski.
Kreator poprowadzi przez:

1. Wybór oryginalnego APK i kontrolę jego zgodności.
2. Potwierdzenie wykrytego JDK i Android SDK Build Tools lub wskazanie ich lokalizacji.
3. Utworzenie własnego klucza PKCS12 albo wybór istniejącego klucza i jego aliasu.
4. Wybór nowej nazwy wynikowego APK oraz podanie hasła do klucza w monicie.

Wynik zostanie przebudowany, wyrównany, podpisany i zweryfikowany. Kreator obsługuje też istniejące
klucze z osobnym hasłem klucza prywatnego. Zachowaj klucz i hasło do przyszłych aktualizacji.
Kreator nie instaluje ani nie odinstalowuje aplikacji. Anulowanie okna kończy pracę; wcześniej utworzony
klucz pozostaje na dysku. Po błędzie podpisywania zachowaj ten klucz i przy ponowieniu wybierz istniejący.
Istniejące APK i klucze nie są nadpisywane. Gdy okna wyboru Tk są niedostępne, ścieżkę wpisujesz w konsoli.

Najpierw zainstaluj Python 3.10+ z [python.org](https://www.python.org/downloads/windows/) z opcją
**Add Python to PATH**, JDK 17+ oraz Android SDK Build Tools (testowane 36.0.0).
Kreator wykrywa Java przez `JAVA_HOME`/`PATH`, a SDK przez `%LOCALAPPDATA%/Android/Sdk/build-tools`.
Build Tools zainstalujesz w SDK Managerze Android Studio. Inne lokalizacje można wskazać ręcznie.
Kreator nie pobiera tych zależności samodzielnie.

## Alternatywa: polecenia ręczne

1. Zainstaluj Python 3.10+; do podpisania także JDK 17+ i Android SDK Build Tools, testowane 36.0.0.
2. Umieść własny oryginalny APK obok skryptu jako `original.apk`.
3. Sprawdź zgodność, utwórz własny klucz i zbuduj plik poleceniami poniżej.

```sh
python patch_lens.py original.apk --verify-only
keytool -genkeypair -keystore my-lens.p12 -storetype PKCS12 -alias lens-local -keyalg RSA -keysize 2048 -validity 10000
python patch_lens.py original.apk -o Lens-local.apk --keystore my-lens.p12 --build-tools "C:/Users/TWOJA_NAZWA/AppData/Local/Android/Sdk/build-tools/36.0.0"
```

Hasła podajesz w interaktywnym monicie. Zachowaj prywatną kopię klucza; nie publikuj go.
Jeżeli `java` wskazuje starszą wersję, dodaj `--java "ścieżka/do/jdk/bin/java.exe"`.
Wynikowy APK ma raport JSON z hashami i wynikiem weryfikacji podpisu. Pliki wejściowe nie są nadpisywane.
Bez opcji podpisywania powstaje plik **niepodpisany**, którego nie można jeszcze zainstalować.

Wymagany SHA-256 oryginału:

```text
c1bb0c9b881b65ff998c572944b6f40c90531fcedc2a2608507c11ed90cdf732
```

Przed instalacją wyeksportuj skany. Usunięcie starej aplikacji kasuje jej prywatne dane.
Własny podpis różni się od podpisu Microsoftu, więc oficjalną aplikację trzeba najpierw odinstalować.
Dotyczy to również poprzedniej przeróbki, jeżeli używała innego klucza.

```sh
adb uninstall com.microsoft.office.officelens
adb install Lens-local.apk
```

Sam patcher nie odinstalowuje aplikacji i nie steruje telefonem.

Do publikacji udostępnij cały katalog źródłowy lub przygotowany ZIP, razem z `patches/`.
Nie dołączaj APK, kluczy, haseł ani logów telefonu. Odbiorca modyfikuje własną kopię lokalnie.
Licencja MIT obejmuje nasz kod i dokumentację; nie nadaje praw do aplikacji Microsoftu.

Zmieniają się dokładnie dwa pliki payloadu; pozostałe 2581 są porównywane bajt po bajcie.
Przetestowany payload pochodzi z FIX1: Samsung SM-S721B / Android 16, import obrazu,
zapis lokalnego PDF i powrót do aparatu, 4 min 35 s bez nowego crasha. Realme GT Master Edition
z RUI 4.0 nie był sprawdzony na fizycznym urządzeniu. Łata nie przywraca wyłączonych usług serwerowych.

[Pełna instrukcja i ograniczenia](README.md) · [Opis zmian](TECHNICAL.md) ·
[Oficjalna dokumentacja podpisywania](https://developer.android.com/tools/apksigner)
