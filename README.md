# ZaStoGram — Telegram для Android с усиленной маскировкой MTProxy

<img width="1916" height="821" alt="image" src="https://github.com/user-attachments/assets/0850c5cd-6d7f-4304-9347-2cc54d5ba416" />

> Экспериментальный форк официального Telegram для Android. Цель форка —
> сделать подключение к MTProxy FakeTLS (`ee`-secret) менее похожим на
> стандартный Telegram MTProxy-трафик и ближе к обычному браузерному HTTPS.

Это не новый мессенджер и не отдельный протокол. База остаётся официальным
Telegram Android, а изменения сосредоточены вокруг MTProxy/FakeTLS-пути.

## Простыми словами

- **MTProxy** — прокси для Telegram.
- **FakeTLS** — режим MTProxy, где начало соединения выглядит как TLS/HTTPS.
- **DPI / ТСПУ** — оборудование провайдера, которое классифицирует и режет
  трафик по признакам на проводе.
- **JA4** — отпечаток TLS ClientHello. По нему можно отличить настоящий браузер
  от синтетического FakeTLS, если ClientHello сделан плохо.

Проблема MTProxy не только в одном хеше. DPI может смотреть на TLS-рукопожатие,
тайминги, размеры записей, количество одновременных соединений и поведение после
handshake. Поэтому здесь важна аккуратная маскировка без поломки MTProto.

## Что сейчас реализовано

### MTProxy FakeTLS path от tsrman-коммита

В активном transport path сохранено поведение, близкое к рабочему
`tsrman/tg`-варианту:

- ClientHello отправляется целиком одним `send()`;
- фаза данных использует стабильный фиксированный cap `2878`;
- рискованные эксперименты с dynamic record sizing сейчас убраны из активного
  пути.

Это важно для надёжности: сначала соединение должно стабильно работать, и только
потом можно снова усиливать маскировку фазы данных.

### Sticky-выбор TLS-профиля

Для MTProxy FakeTLS выбранный TLS-профиль теперь не меняется хаотично на каждое
соединение. Профиль выбирается стабильно по `endpoint + secret + локальная соль`.

Сейчас в пуле:

- Firefox;
- Android Chrome;
- Firefox Android;
- Android OkHttp;
- Yandex.

Так разные установки и разные прокси могут получать разные wire images, но один
конкретный proxy endpoint не прыгает между профилями каждую секунду.

### Guard-проверки ClientHello

Перед отправкой ClientHello проверяется на базовую совместимость с MTProxy:

- корректная TLS-запись и длины;
- ожидаемый offset списка cipher suites;
- первый не-GREASE cipher из TLS 1.3 `TLS_AES_*`;
- наличие SNI-домена из `ee`-secret;
- размер в пределах серверного лимита.

Это защищает от красивого, но несовместимого ClientHello.

### Рандомизация внутри ClientHello

Оставлены низкорисковые элементы маскировки:

- случайные поля ClientHello;
- случайный ECH payload там, где профиль его использует;
- случайная цель padding extension вместо старого фиксированного размера;
- безопасная генерация GREASE-значений без выхода за границы массива.

### MTProxy connection scheduler

Для `ee` FakeTLS добавлен endpoint admission-controller. Он ограничивает не
скорость уже установленного MTProto-трафика, а только залп одинаковых
`connect -> ClientHello -> server_hello_hmac_ok` к одному proxy endpoint.

Ключ scheduler-а: `proxy host:port:SNI`.

Что он делает:

- по умолчанию держит максимум один активный FakeTLS handshake на endpoint;
- после недавних успешных `server_hello_hmac_ok` может поднять лимит до двух;
- ставит новые handshakes в очередь по приоритету:
  `Generic/Temp -> GenericMedia -> Push -> Download -> Upload -> ProxyCheck`;
- освобождает слот сразу после `server_hello_hmac_ok`, поэтому download/upload
  после подключения идут параллельно как раньше;
- после зависания в фазе `client_hello_sent` включает cooldown endpoint-а с
  jitter, чтобы не долбить один и тот же маршрут одинаковыми попытками;
- работает через cancellable `Timer` и не блокирует network thread.

Это сделано против узнаваемого burst-паттерна, когда клиент почти одновременно
открывает много одинаковых FakeTLS-соединений к одному прокси. Жёсткий режим
типа "один SYN в секунду" не используется: он слишком грубо замедляет Telegram и
сам может стать странной сигнатурой.

### Startup diagnostics

Добавлены диагностические точки для MTProxy-подключения:

- `connect_start`;
- `socket_connected`;
- `client_hello_sent`;
- `server_hello_hmac_ok`;
- `on_connected`;
- `mtproxy_disconnect` с причиной и состоянием.
- `admission_grant`, `admission_queue`, `admission_release`,
  `admission_freeze_detected`, `admission_freeze_cooldown`.

Это нужно, чтобы отличать DPI-обрыв от багов в нашем transport path.

### Корректная дорезка TLS-записи при partial send

Для wrapped TLS-записей добавлена pending-frame очередь: если `send()` отправил
только часть TLS record, остаток досылается как продолжение того же record, а
MTProto payload не выбрасывается раньше полной отправки.

## Сборка

Готового APK здесь намеренно нет. Собирай приложение из исходников.

1. Получи `api_id` и `api_hash` на [my.telegram.org](https://my.telegram.org).
2. Укажи свои значения в проекте Telegram Android.
3. Подставь свой release keystore.
4. Собери через Android Studio или GitHub Actions.

GitHub Actions настроен на ccache с `CCACHE_COMPILERCHECK=content`, чтобы
повторные native-сборки были заметно быстрее после прогрева кэша.

## Как пользоваться

1. Подними MTProxy с FakeTLS вне зоны блокировки.
2. Используй `ee`-secret с доменом.
3. В приложении добавь MTProto proxy обычным способом:
   **Настройки -> Данные и память -> Прокси -> Добавить прокси -> MTProto**.

Маскировка из этого форка применяется именно к FakeTLS/`ee`-secret. Для обычных
`dd`/non-FakeTLS secret эти изменения не дают того же эффекта.

## Честные ограничения

- SNI не ротируется сам по себе. Он берётся из `ee`-secret.
- Фаза данных пока не имитирует настоящий HTTP/2 или HTTP/1.1.
- Dynamic record sizing сейчас не включён в активный путь.
- Scheduler ограничивает только фазу открытия FakeTLS-соединения. Он не пытается
  полностью замаскировать статистику уже установленного MTProto-трафика.
- Это не гарантия вечного обхода блокировок: DPI-правила меняются.
- Это неофициальный форк, использовать его нужно с пониманием рисков.

## Потом реализуем

- Вернуть DRS аккуратно: random TLS record sizes, фазовая модель, anti-repeat и
  idle reset, но только после проверки partial-send/data-path на реальном
  MTProxy.
- IPT: неблокирующая имитация inter-packet timing с разделением
  `handshake / keepalive / interactive / bulk`.
- Больше sticky browser profiles из `telemt/tdlib-obf`: Android Brave,
  дополнительные Chrome/Firefox/Yandex-варианты, Windows/iOS профили, но только
  через guard-тесты совместимости с MTProxy.
- Ручной debug override профиля без публичного GUI, чтобы быстро сравнивать
  профили при тестах.
- Route-aware ECH policy с circuit breaker, чтобы не долбить сеть ECH-вариантом,
  если конкретный маршрут его режет.
- ClientHello fragmentation / MSS-clamp как отдельный эксперимент. Сейчас это
  не включено в стабильный путь.
- L7 camouflage: HTTP/2 или HTTP/1.1 framing поверх TLS-like transport. Это
  самый глубокий и самый рискованный слой, его нельзя делать косметически.
- Idle chaff и connection lifecycle camouflage, если они не будут ломать
  MTProto и батарею на Android.

## Основа и благодарности

- [DrKLO/Telegram](https://github.com/DrKLO/Telegram) — официальный Telegram
  Android.
- [tsrman/tg](https://github.com/tsrman/tg) — рабочая база FakeTLS JA4/pacing
  изменений.
- [telemt/tdlib-obf](https://github.com/telemt/tdlib-obf) — идеи и референсы по
  stealth-профилям, DRS/IPT и profile registry.
