# eduVULCAN — integracja Home Assistant

Nieoficjalna integracja Home Assistant dla dziennika **eduVULCAN** (nowe API hebeCE firmy VULCAN).
Pobiera dla każdego dziecka: plan lekcji (z zastępstwami i odwołaniami), prace domowe,
sprawdziany i szczęśliwy numerek.

Oparta na zwendorowanej kopii biblioteki [bbrjpl1310b/iris](https://github.com/bbrjpl1310b/iris)
(AGPL-3.0). Zero zewnętrznych zależności — wszystko, czego potrzebuje (pydantic, cryptography,
aiohttp), jest już w Home Assistant Core.

> **Uwaga:** to nieoficjalne API. Korzystasz na własną odpowiedzialność — regulamin eduVULCAN
> nie przewiduje klientów zewnętrznych.

## Instalacja (HACS)

1. HACS → Integrations → menu (⋮) → **Custom repositories**
2. Dodaj `https://github.com/PiotrOrman/eduVulcan` jako typ **Integration**
3. Zainstaluj **eduVULCAN**, zrestartuj Home Assistant

## Konfiguracja

1. W przeglądarce zaloguj się na **https://eduvulcan.pl/api/ap**
2. Po zalogowaniu otwórz źródło strony (Ctrl+U / prawy klik → Zbadaj) i znajdź ukryte pole
   `<input type="hidden" value="...">` — jego wartość to JSON z listą `Tokens`
   (jeden token JWT na dziecko)
3. W HA: **Ustawienia → Urządzenia i usługi → Dodaj integrację → eduVULCAN**
4. Wklej cały JSON (albo same tokeny JWT) i zatwierdź

Tokeny są **jednorazowe** i służą tylko do rejestracji "wirtualnego telefonu" (klucz RSA).
Po rejestracji integracja odświeża dane sama — tokeny nie są nigdzie zapisywane.
Hasło do eduVULCAN nigdy nie jest podawane w HA.

## Encje

Dla każdego dziecka powstaje urządzenie `Szkoła <imię>` z sensorami:

| Encja | Stan | Atrybuty |
|---|---|---|
| `sensor.szkola_<imie>_nastepna_lekcja` | np. `Matematyka (08:00)` | `dzis`, `jutro` (pełny plan z salami, nauczycielami, zastępstwami), `nastepny_dzien_szkolny` + `nastepny_dzien_szkolny_plan` (najbliższy dzień z lekcjami — w weekend pokazuje poniedziałek), `nastepna_lekcja_start` |
| `sensor.szkola_<imie>_zadania_domowe` | liczba otwartych zadań | `zadania` (przedmiot, treść, termin, dni do terminu) |
| `sensor.szkola_<imie>_sprawdziany` | liczba nadchodzących | `sprawdziany` (przedmiot, typ, treść, data) |
| `sensor.szkola_<imie>_szczesliwy_numerek` | numerek | `numer_w_dzienniku`, `trafiony` |

Dane odświeżane co 30 minut.

## Zmiany względem oryginalnej biblioteki iris

Pliki w `custom_components/eduvulcan/iris/` to kopia upstreamu z trzema rodzajami zmian
(każda oznaczona komentarzem `PATCHED for HA vendoring`):

- importy `from iris.*` przepisane na względne,
- adnotacje `any` (wbudowana funkcja) zamienione na `typing.Any` — zgodność z pydantic 2.13
  pinowanym przez HA Core,
- `HttpClient` dostał metodę `close()` (upstreamowy `__aexit__` odwoływał się do
  nieistniejącego pola).

## Licencja

AGPL-3.0 (dziedziczona po bibliotece iris).
