from vv_knopka.long_run_conveyor import pending_longrun_slots
from vv_knopka.manifest import animal_episode_number_for_slot, longrun_slot
from vv_knopka.settings import Settings


def _settings(tmp_path):
    return Settings(
        raw={
            "pilot": {"total_shorts": 15, "runtime_dir": "runtime", "openai_budget_usd": 10.0},
            "content": {
                "default_language": "en",
                "animal_slots": [2, 4, 6, 8, 10, 12, 14],
            },
            "long_run": {
                "enabled": True,
                "pipeline_cycle": ["animal_compilation", "ai_short"],
                "ai_language": "en",
            },
            "animal": {"language_cycle": ["en", "en", "en", "en", "ru"]},
        },
        root=tmp_path,
    )


def test_longrun_schedule_continues_after_pilot(tmp_path):
    settings = _settings(tmp_path)
    assert longrun_slot(settings, 16).pipeline == "animal_compilation"
    assert longrun_slot(settings, 16).language == "en"
    assert longrun_slot(settings, 17).pipeline == "ai_short"
    assert longrun_slot(settings, 17).language == "en"
    assert longrun_slot(settings, 18).language == "en"
    assert longrun_slot(settings, 24).pipeline == "animal_compilation"
    assert longrun_slot(settings, 24).language == "ru"


def test_cat_episode_numbering_continues_after_pilot(tmp_path):
    settings = _settings(tmp_path)
    assert animal_episode_number_for_slot(settings, 14) == 7
    assert animal_episode_number_for_slot(settings, 16) == 8
    assert animal_episode_number_for_slot(settings, 18) == 9
    assert animal_episode_number_for_slot(settings, 24) == 12


def test_longrun_pending_skips_existing_ready_output(tmp_path):
    settings = _settings(tmp_path)
    ready = settings.runtime_dir / "ready_for_review"
    ready.mkdir(parents=True)
    (ready / "slot-16-en-animals.mp4").write_bytes(b"video")

    pending = pending_longrun_slots(settings, count=2)
    assert [(slot.slot, slot.pipeline, slot.language) for slot in pending] == [
        (17, "ai_short", "en"),
        (18, "animal_compilation", "en"),
    ]
