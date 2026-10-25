# v1.1.0 — Windows wizard / kreator Windows

## Polski

Uruchom `Start-Windows.cmd` po rozpakowaniu ZIP. Kreator PL/EN prowadzi przez wybór APK,
sprawdzenie zgodności, wybór narzędzi Java/SDK, utworzenie lub wybór własnego klucza oraz
zapis podpisanego APK. Obsługuje osobne hasło klucza prywatnego. Nie instaluje ani nie usuwa aplikacji.
Wymaga Python 3.10+, JDK 17+ i Android SDK Build Tools. Instrukcja: `README-PL.md`.
Łata aplikacji i obsługiwana wersja ARM64 pozostają takie jak w v1.0.0.

## English

Run `Start-Windows.cmd` after extracting the ZIP. The PL/EN wizard guides you through APK
selection and compatibility checks, Java/SDK selection, creating or choosing your own key,
and saving a signed APK. Separate private-key passwords are supported. It does not install
or uninstall apps. Requires Python 3.10+, JDK 17+ and Android SDK Build Tools. See `README.md`.
The application patch and supported ARM64 build are unchanged from v1.0.0.

---

# v1.0.0 — local patch / lokalna łata

## Polski

Nieoficjalna łata offline dla Microsoft Lens 16.0.19628.20008 (2004969699), ARM64.

* Usuwa wymuszoną migrację do OneDrive i przekierowanie z przycisku migracji.
* Zawiera poprawkę opóźnionego crasha JNI z wersji FIX1.
* Sprawdza SHA-256 oryginału i łaty, odtwarza dwa zmienione pliki oraz porównuje pozostałe 2581.
* Opcjonalnie wyrównuje, podpisuje własnym kluczem i weryfikuje wynik przy użyciu Android SDK.

Pobierz `Lens-local-patch-1.0.0-source.zip`, sprawdź sumę z pliku `.sha256` i rozpakuj.
Zacznij od `README-PL.md`. Potrzebujesz własnego oryginalnego APK; paczka go nie zawiera.
Przed zastąpieniem aplikacji wyeksportuj skany, bo odinstalowanie usuwa jej prywatne dane.

Payload FIX1 sprawdzono na Samsung SM-S721B / Android 16. Nowa paczka przeszła test przebudowy,
podpisu i wyrównania oraz siedem testów syntetycznych na Windows. Nie potwierdzono wszystkich
urządzeń ani działania wyłączonych usług Microsoftu. Szczegóły: `VALIDATION.md`.

## English

Unofficial offline patch for Microsoft Lens 16.0.19628.20008 (2004969699), ARM64.

* Removes forced OneDrive migration and the migration button's external redirect.
* Includes the delayed JNI crash fix from FIX1.
* Pins original/delta SHA-256 hashes, reconstructs two changed files, and compares 2,581 others.
* Optionally aligns, signs with your own key, and verifies the APK using Android SDK tools.

Download `Lens-local-patch-1.0.0-source.zip`, verify it against the `.sha256` file and extract it.
Start with `README.md`. Supply your own original APK; it is not included.
Export your scans before replacing an installation: uninstalling deletes private app data.

The FIX1 payload was tested on Samsung SM-S721B / Android 16. This package passed a real build,
signing and alignment check, plus seven synthetic tests on Windows. Compatibility with every device
and discontinued Microsoft services is not established. See `VALIDATION.md` for the exact scope.
