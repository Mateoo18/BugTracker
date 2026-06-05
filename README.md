# BugTracker Django - dokumentacja techniczna

BugTracker to aplikacja biznesowa do zgłaszania, obsługi, przypisywania i priorytetyzacji błędów w produktach informatycznych. Projekt został wykonany w Django i Django REST Framework, z podziałem warstwowym inspirowanym clean architecture oraz dostosowanym do sposobu pracy Django ORM.

## Informacja o zakresie projektu

Projekt możliwie szeroko pokrywa wymagania aplikacji typu BugTracker, przy czym wymagania technologiczne zostały dostosowane do architektury Django. Zamiast implementacji w Blazor Server i Blazor WebAssembly zastosowano ich funkcjonalne odpowiedniki:

- Django REST Framework jako warstwę WebAPI,
- Django Templates jako warstwę interfejsu webowego renderowanego po stronie serwera.

Logika repozytoriów i jednostki pracy została dostosowana do Django ORM oraz serwisów aplikacyjnych. Dzięki temu logika biznesowa jest oddzielona od widoków webowych i endpointów API, a transakcje bazodanowe są obsługiwane w warstwie aplikacyjnej.

Projekt zawiera dane seedowe, konta demo, system ról, dashboardy, zgłaszanie błędów, przypisywanie zgłoszeń do zespołów i developerów, zmianę statusów, historię zmian, obsługę komentarzy, załączników graficznych oraz automatyczne wyliczanie priorytetu zgłoszenia.

## Technologie

- Python 3
- Django 5.1.2
- Django REST Framework 3.17.1
- SQLite
- Pillow 10.1.0 do obsługi plików graficznych
- Bootstrap 5
- Chart.js
- Font Awesome
- Django Templates
- Django ORM
- system logowania Django

## Architektura projektu

Projekt ma strukturę warstwową zgodną z clean architecture, ale dopasowaną do Django:

| Katalog | Odpowiedzialność |
| --- | --- |
| `domain` | Logika domenowa niezależna od frameworka, m.in. algorytm liczenia priorytetu. |
| `application` | Serwisy aplikacyjne i przypadki użycia, np. tworzenie błędu, przypisanie, zmiana statusu, zmiana priorytetu. |
| `infrastructure` | Modele Django, baza danych, migracje, panel admina i komenda seedująca dane demo. |
| `presentation/api` | Warstwa WebAPI oparta na Django REST Framework: serializery, uprawnienia, viewsety i endpointy biznesowe. |
| `presentation/web` | Warstwa webowa renderowana po stronie serwera: widoki Django, formularze, middleware, szablony HTML. |
| `shared_kernel` | Elementy wspólne, np. pomocnicza logika ról. |
| `config` | Konfiguracja Django: ustawienia, routing główny, WSGI/ASGI. |

Najważniejsza logika biznesowa nie jest umieszczona bezpośrednio w widokach. Widoki i endpointy API wywołują serwisy z katalogu `application`, a one korzystają z modeli Django z warstwy `infrastructure`.

## Model danych

Projekt korzysta z bazy SQLite (`db.sqlite3`) oraz Django ORM. W bazie znajduje się ponad pięć tabel biznesowych. Najważniejsze encje to:

| Encja | Opis |
| --- | --- |
| `User` | Użytkownik systemu rozszerzający `AbstractUser`; posiada rolę, firmę, zespoły i flagę wymuszonej zmiany hasła. |
| `Company` | Firma lub organizacja, do której przypisane są produkty, zespoły, użytkownicy i zgłoszenia. |
| `Team` | Zespół w ramach firmy, powiązany z modułem produktu. |
| `Bug` | Główne zgłoszenie błędu z opisem, krokami reprodukcji, statusem, priorytetem, wpływem i modułem. |
| `BugComment` | Komentarze do zgłoszeń, w tym komentarze wewnętrzne widoczne tylko dla personelu. |
| `BugAssignment` | Aktywne i historyczne przypisania błędu do zespołu oraz opcjonalnie konkretnego użytkownika. |
| `BugStatusHistory` | Historia zmian statusów zgłoszenia. |
| `BugAttachment` | Załączniki graficzne dodawane do zgłoszeń. |
| `BugCommentAttachment` | Załączniki graficzne powiązane z komentarzami. |
| `BugPriorityHistory` | Historia automatycznych i ręcznych zmian priorytetu. |

Modele wykorzystują relacje `ForeignKey`, `ManyToManyField`, indeksy bazodanowe oraz walidatory pól liczbowych i plików.

## Role użytkowników

System obsługuje kilka ról:

- `Reporter` - zgłasza błędy i widzi własne zgłoszenia oraz publicznie rozwiązane błędy.
- `Developer` - pracuje nad zgłoszeniami przypisanymi do jego firmy lub zespołu.
- `Product Owner` - zarządza zgłoszeniami w firmie, zespołami i kontami developerów.
- `Admin` - ma pełny dostęp administracyjny do danych i panelu Django Admin.

Dostęp do danych jest filtrowany według roli oraz firmy użytkownika. Część operacji, takich jak przypisywanie zgłoszeń, zmiana statusu i ręczna zmiana priorytetu, wymaga roli Product Owner lub Admin.

## Funkcje biznesowe

Najważniejsze funkcje aplikacji:

- rejestracja i logowanie użytkowników,
- konta demo oraz dane startowe,
- tworzenie zgłoszeń błędów,
- walidacja formularzy po stronie Django,
- lista zgłoszeń z filtrowaniem i paginacją,
- widok szczegółów zgłoszenia,
- dashboard użytkownika,
- dashboard personelu z wykresem statusów,
- tablica kanban pogrupowana według statusów,
- przypisywanie zgłoszeń do zespołów i developerów,
- zmiana statusu zgłoszenia,
- komentarze publiczne i wewnętrzne,
- załączniki graficzne PNG/JPG/JPEG,
- lista adresów e-mail do powiadomień o zmianach w zgłoszeniu,
- tworzenie zespołów przez Product Ownera,
- tworzenie kont developerów przez Product Ownera,
- wysyłka tymczasowego hasła dla developera,
- wymuszenie zmiany hasła przy pierwszym logowaniu developera,
- automatyczne wyliczanie priorytetu,
- ręczne nadpisanie priorytetu z zapisem powodu,
- historia zmian statusów,
- historia zmian priorytetów,
- logowanie zdarzeń aplikacji i błędów do plików.

## Priorytetyzacja zgłoszeń

Priorytet błędu jest wyliczany w module `domain/priority.py`. Algorytm bierze pod uwagę:

- ważność błędu (`severity`),
- wpływ na użytkowników (`impact`),
- liczbę podobnych zgłoszeń (`similar_count`),
- wiek zgłoszenia,
- znaczenie modułu (`module_importance`).

Wynikiem jest `priority_score` w skali do 100 oraz priorytet:

| Zakres punktów | Priorytet |
| --- | --- |
| 85-100 | `P0` |
| 65-84 | `P1` |
| 40-64 | `P2` |
| 0-39 | `P3` |

Priorytet może zostać ponownie przeliczony automatycznie lub ręcznie nadpisany przez uprawnionego użytkownika. Każda zmiana jest zapisywana w `BugPriorityHistory`.

## WebAPI

Warstwa API znajduje się w `presentation/api`. Projekt wykorzystuje Django REST Framework, serializery, viewsety, router DRF oraz dodatkowe endpointy biznesowe.

Główne endpointy biznesowe:

| Metoda i endpoint | Opis |
| --- | --- |
| `POST /api/bugs/create/` | Utworzenie zgłoszenia z opcjonalnym obrazem. |
| `POST /api/bugs/{id}/assign/` | Przypisanie zgłoszenia do zespołu i opcjonalnie developera. |
| `POST /api/bugs/{id}/status/` | Zmiana statusu zgłoszenia. |
| `POST /api/bugs/{id}/priority/recalculate/` | Przeliczenie priorytetu lub ręczne nadpisanie priorytetu. |
| `GET /api/bugs/my/` | Lista zgłoszeń utworzonych przez zalogowanego użytkownika. |
| `GET /api/bugs/assigned/` | Lista zgłoszeń przypisanych do zalogowanego użytkownika. |
| `GET /api/bugs/company-board/` | Tablica zgłoszeń firmy użytkownika. |
| `GET /api/bugs/public-resolved/` | Publiczna lista zgłoszeń rozwiązanych, zweryfikowanych lub zamkniętych. |

CRUD przez router DRF jest dostępny dla:

- `companies`,
- `teams`,
- `users`,
- `bugs`,
- `comments`,
- `assignments`,
- `attachments`,
- `status-history`,
- `priority-history`.

API korzysta z uwierzytelniania sesyjnego i Basic Auth. Domyślnie endpointy wymagają zalogowanego użytkownika.

## Interfejs webowy

Warstwa webowa znajduje się w `presentation/web`. Interfejs jest renderowany po stronie serwera przy pomocy Django Templates. W szablonach wykorzystywane są zewnętrzne biblioteki UI:

- Bootstrap 5 do układu i komponentów,
- Chart.js do wykresów w dashboardzie,
- Font Awesome do ikon.

Główne widoki webowe:

- logowanie,
- rejestracja,
- wymuszona zmiana hasła,
- dashboard użytkownika,
- dashboard personelu,
- lista zgłoszeń,
- publiczna lista rozwiązanych zgłoszeń,
- tablica kanban,
- szczegóły zgłoszenia,
- formularz tworzenia zgłoszenia,
- tworzenie zespołu,
- tworzenie konta developera.

## Załączniki i obrazy

Aplikacja obsługuje obrazy jako załączniki do zgłoszeń. Pliki są przechowywane w katalogu `media/`, a model `BugAttachment` akceptuje rozszerzenia:

- `png`,
- `jpg`,
- `jpeg`.

Formularze webowe ograniczają rozmiar pliku do 4 MB. Do obsługi obrazów używana jest biblioteka Pillow.

## Powiadomienia e-mail

Projekt obsługuje wysyłkę wiadomości e-mail w kilku miejscach:

- utworzenie konta developera i wysłanie hasła tymczasowego,
- powiadomienie o komentarzu,
- powiadomienie o nowym załączniku,
- powiadomienie o zmianie statusu,
- powiadomienie o zmianie lub przeliczeniu priorytetu.

Konfiguracja poczty jest pobierana z pliku `.env`. Przykładowe wartości znajdują się w `.env.sample`.

## Logowanie

Konfiguracja logowania znajduje się w `config/settings.py`. Aplikacja zapisuje:

- logi aplikacyjne do pliku `logs/bugtracker_<data>.log`,
- logi błędów do pliku `logs/errors_<data>.log`,
- logi serwera Django również do dziennego pliku aplikacyjnego.

Data jest dodawana do nazwy pliku na podstawie dnia uruchomienia aplikacji. Logger `bugtracker` jest wykorzystywany w warstwie aplikacyjnej i webowej.

## Dane seedowe

Projekt zawiera komendę:

```bash
python manage.py seed_demo
```

Komenda tworzy:

- firmy demo,
- zespoły,
- użytkowników w różnych rolach,
- przykładowe zgłoszenia,
- przypisania zgłoszeń,
- przykładowe statusy i priorytety.

## Konta demo

Hasło dla wszystkich kont demo:

```text
demo1234
```

| Login | Imię i nazwisko | Rola |
| --- | --- | --- |
| `reporter` | Olivia Reporter | Reporter |
| `admin` | Ava Admin | Admin / superuser |
| `po.acme` | Emma Carter | Product Owner |
| `dev.acme.james` | James Wilson | Developer |
| `dev.acme.sophia` | Sophia Martin | Developer |
| `po.northwind` | Liam Anderson | Product Owner |
| `dev.northwind.noah` | Noah Brown | Developer |
| `dev.northwind.mia` | Mia Davis | Developer |
| `po.globex` | Charlotte Miller | Product Owner |
| `dev.globex.ethan` | Ethan Moore | Developer |
| `dev.globex.amelia` | Amelia Taylor | Developer |
| `po.initech` | Benjamin Thomas | Product Owner |
| `dev.initech.harper` | Harper Jackson | Developer |
| `dev.initech.lucas` | Lucas White | Developer |

## Uruchomienie lokalne

1. Utwórz i aktywuj środowisko wirtualne:

```bash
python -m venv .venv
.venv\Scripts\activate
```

2. Zainstaluj zależności:

```bash
python -m pip install -r requirements.txt
```

3. Wykonaj migracje:

```bash
python manage.py migrate
```

4. Utwórz dane demo:

```bash
python manage.py seed_demo
```

5. Uruchom serwer developerski:

```bash
python manage.py runserver
```

Adresy po uruchomieniu:

- Web UI: <http://127.0.0.1:8000/>
- API: <http://127.0.0.1:8000/api/>
- Admin: <http://127.0.0.1:8000/admin/>

## Testy

Testy Django można uruchomić poleceniem:

```bash
python manage.py test
```

## Konfiguracja środowiskowa

Przykładowy plik `.env.sample` zawiera konfigurację poczty i adresu aplikacji. Najważniejsze zmienne:

| Zmienna | Opis |
| --- | --- |
| `EMAIL_BACKEND` | Backend poczty Django. |
| `EMAIL_HOST` | Serwer SMTP. |
| `EMAIL_PORT` | Port SMTP. |
| `EMAIL_USE_TLS` | Czy używać TLS. |
| `EMAIL_HOST_USER` | Login do skrzynki e-mail. |
| `EMAIL_HOST_PASSWORD` |token aplikacyjny. |
| `DEFAULT_FROM_EMAIL` | Nadawca wiadomości. |
| `SITE_URL` | Bazowy adres aplikacji do linków w e-mailach. |

## Podsumowanie

BugTracker jest kompletną aplikacją webową z API, bazą danych, warstwą domenową, serwisami aplikacyjnymi, interfejsem użytkownika, danymi demo i obsługą ról. Projekt realizuje założenia aplikacji do zarządzania błędami, a technologie Django REST Framework oraz Django Templates pełnią w nim role odpowiadające warstwom WebAPI i webowego interfejsu użytkownika.
