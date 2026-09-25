from vv_knopka.mpt import final_video_candidates


def test_final_video_is_preferred_over_combined_intermediate():
    task = {
        "videos": ["/tasks/x/final-1.mp4"],
        "combined_videos": ["/tasks/x/combined-1.mp4"],
    }
    assert final_video_candidates(task) == ["/tasks/x/final-1.mp4"]


def test_combined_video_is_only_a_fallback():
    task = {"combined_videos": ["/tasks/x/combined-1.mp4"]}
    assert final_video_candidates(task) == ["/tasks/x/combined-1.mp4"]
