# VV_knopka — feedback loop по YouTube-комментариям

Статус: **planned**, не включено в production.

## Цель

Использовать комментарии зрителей как дополнительный сигнал качества Shorts, в первую очередь для фоновой музыки, не позволяя одному случайному негативному комментарию автоматически менять production policy.

## Планируемый flow

```text
YouTube comments
  -> локальный snapshot/history
  -> topic classification
     - music/BGM
     - narration/voice
     - video/content
     - unrelated
  -> sentiment only inside relevant topic
  -> aggregate signal over multiple videos/comments
  -> recommendation
     - keep
     - lower volume
     - rotate/replace tracks
     - disable music experiment
  -> human approval before material policy change
```

## Music-specific rules

Сигналом считаются только комментарии, которые действительно относятся к музыке/фоновому звуку. Общий негатив про ролик не должен ошибочно интерпретироваться как негатив про BGM.

Примеры music complaints:

- `music is too loud`;
- `annoying background music`;
- `the music ruins it`;
- `музыка слишком громкая`;
- `фон мешает голосу`.

Позитивные/нейтральные упоминания музыки тоже сохраняются.

## Anti-overreaction

Не менять production policy из-за единичного комментария.

Будущий decision gate должен учитывать как минимум:

- количество независимых music-related комментариев;
- долю negative среди music-related;
- число разных Shorts, на которых повторяется сигнал;
- период времени;
- текущую громкость/track metadata из `music.json`;
- YouTube performance metrics из `vv-youtube stats/report`.

На первом этапе система только строит отчёт и рекомендацию. Автоматическое изменение `[music]` без отдельного human approval не планируется.

## Возможные действия

Если устойчивый негатив именно про музыку подтверждается:

1. сначала снизить `ai_volume` / `cat_volume`;
2. если жалуются на конкретные композиции — вывести их из rotation;
3. сгенерировать новую candidate library через ACE-Step;
4. повторно провести controlled comparison music ON/OFF;
5. полностью отключать музыку только если данные показывают, что она стабильно мешает.

## Связь с текущей системой

- `music.json` уже хранит track name, SHA256, generator, volume, ducking и applied state;
- `vv-youtube stats/report` уже собирают performance data;
- комментарии должны стать отдельным observational source, а не publication blocker;
- TikTok остаётся вне этого work block.
