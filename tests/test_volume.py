"""浮力ガードレールのテスト。"""

from surf_feel.dictionary import load_boards
from surf_feel.models import RiderProfile
from surf_feel.volume import recommend_dimensions, weight_band


def test_weight_band():
    assert weight_band(55) == "light"
    assert weight_band(68) == "mid"
    assert weight_band(85) == "heavy"


def test_glide_boards_get_more_volume():
    """「浮力の余りはグライドの原資」: グライド系ほど推奨ボリュームが大きい。"""
    boards = load_boards()
    profile = RiderProfile(weight_kg=70, skill="intermediate")
    perf = recommend_dimensions(profile, boards["performance"])
    mid = recommend_dimensions(profile, boards["midlength"])
    glider = recommend_dimensions(profile, boards["glider"])
    assert perf.volume_min_l < mid.volume_min_l < glider.volume_min_l


def test_beginner_gets_more_volume_than_advanced():
    boards = load_boards()
    beginner = RiderProfile(weight_kg=70, skill="beginner")
    advanced = RiderProfile(weight_kg=70, skill="advanced")
    b = recommend_dimensions(beginner, boards["fish"])
    a = recommend_dimensions(advanced, boards["fish"])
    assert b.volume_min_l > a.volume_min_l


def test_volume_range_is_sane():
    boards = load_boards()
    profile = RiderProfile(weight_kg=70, skill="intermediate")
    d = recommend_dimensions(profile, boards["performance"])
    # 70kg 中級のパフォーマンス系はおおむね 27〜33L 帯
    assert 25 < d.volume_min_l < d.volume_max_l < 35


def test_low_frequency_adds_volume():
    boards = load_boards()
    weekly = RiderProfile(weight_kg=70, frequency="weekly")
    rarely = RiderProfile(weight_kg=70, frequency="rarely")
    assert (
        recommend_dimensions(rarely, boards["twin"]).volume_min_l
        > recommend_dimensions(weekly, boards["twin"]).volume_min_l
    )
