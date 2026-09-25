# Лицензированные fallback-источники для cats

Добавлено 25 сентября 2026 года. Основной Pexels/Pixabay-маршрут и порог
качества не изменены. Новый маршрут включается только тогда, когда обычный
поиск не смог собрать минимум релевантных вертикальных роликов со слышимым
исходным звуком.

## Порядок работы

1. Уже одобренные файлы из локальной лицензированной библиотеки.
2. Обычный полный поиск Pexels и Pixabay, включая действующие cooldown и
   контроль повторов.
3. Wikimedia Commons: только Public Domain, CC0, CC BY 3.0 или CC BY 4.0.
4. Если пяти источников всё равно нет — создаётся кэшированная очередь
   YouTube-кандидатов для ручной проверки.

Порог `min_unique_materials=5` не снижается. Обычные YouTube-видео никогда не
скачиваются и не публикуются автоматически. Очередь хранит только публичные
метаданные и URL. Creative Commons тоже требует ручной проверки и существующих
clean-footage/геометрия/звук gates перед импортом.

## Локальная библиотека

Один раз создать пустой manifest:

```powershell
.\.venv\Scripts\vv-cat-sources.exe local-template
```

Файлы кладутся в `runtime/licensed_sources/cats/`, рядом с `manifest.json`.
Пример записи:

```json
{
  "version": 1,
  "clips": [
    {
      "id": "creator-cat-paw-001",
      "file": "cat-paw.mp4",
      "title": "Cat reaching with a paw",
      "creator": "Author name",
      "creator_url": "https://example.com/author",
      "source_url": "https://example.com/original",
      "license": "CC BY 4.0",
      "license_url": "https://creativecommons.org/licenses/by/4.0/",
      "commercial_use_allowed": true,
      "human_approved": true
    }
  ]
}
```

Разрешены только Public Domain, CC0, CC BY 3.0 и CC BY 4.0. CC BY-SA,
CC BY-NC, CC BY-ND и запись без явного `human_approved=true` отклоняются.
Файл всё равно проходит локальные проверки длительности, 9:16 и звука.

## Wikimedia Commons

Commons используется без платного API и без аккаунта. До скачивания бот
проверяет MIME, размер, геометрию и лицензию; затем ограниченный набор preview
проходит существующий Luna visual relevance gate. Скачанный файл повторно
проверяется через FFmpeg. По умолчанию рассматривается не больше 16 кандидатов
и файлов до 80 MB.

Для CC BY в `sources.json` сохраняются автор, оригинальный URL, лицензия,
license URL, SHA-256 и описание изменений. Требуемая атрибуция автоматически
добавляется в YouTube description существующим metadata builder.

## Очередь YouTube

После полного исчерпания автоматических лицензированных источников создаётся:

`runtime/slots/NN/source-candidate-queue.json`

Поиск использует уже настроенный OAuth YouTube Data API. На один проблемный
слот выполняются два `search.list` и один `videos.list`, после чего файл
кэшируется: повтор batch не расходует квоту повторно. Один поиск отбирает
официально помеченные Creative Commons, второй сохраняет обычные Shorts только
как references с пометкой `permission_required_before_use`.

Посмотреть или принудительно обновить очередь:

```powershell
.\.venv\Scripts\vv-cat-sources.exe youtube-queue 57
.\.venv\Scripts\vv-cat-sources.exe youtube-queue 57 --refresh
```

`--refresh` снова расходует бесплатную дневную квоту YouTube Data API.
OpenAI при создании очереди не вызывается.

После ручного просмотра Creative Commons URL можно импортировать существующей
строгой командой:

```powershell
.\.venv\Scripts\vv-cat-youtube.exe cc 57 --url "https://www.youtube.com/watch?v=..."
.\.venv\Scripts\vv.exe recovery-unblock 57
```

Затем используется обычный ярлык/batch. Для standard-license кандидата одной
ссылки недостаточно: сначала нужно разрешение автора или другое документированное
право, после чего файл оформляется через локальную библиотеку.

## Аудит и стоимость

- `runtime/slots/NN/cat_source_fallback.json` — итог всех fallback-этапов;
- `runtime/slots/NN/attribution.json` — обязательные credit entries;
- `runtime/slots/NN/source-candidate-queue.json` — ручная очередь без media;
- OpenAI: `$0` для локальной библиотеки и YouTube metadata queue;
- Wikimedia vision используется только после полного неуспеха stock route и
  ограничен существующим ledger/лимитом visual-review calls;
- общий бюджет `$10` и fail-closed публикация сохранены.

TikTok по-прежнему не подключён к автоматическому поиску или скачиванию.
