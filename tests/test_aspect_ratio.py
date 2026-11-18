from pipeline.checks import aspect_ratio


def run(make_ds, cfg, lines, size=(640, 480)):
    ds = make_ds(images={"a": 1}, labels={"a": lines}, size=size)
    return [(i.code, i.line, i.severity) for i in aspect_ratio.run(ds, cfg)]


def test_normal_box_is_silent(make_ds, cfg):
    assert run(make_ds, cfg, ["1 0.5 0.5 0.2 0.3", "0 0.5 0.5 0.4 0.2"]) == []


def test_extreme_tall_and_wide_boxes_are_flagged(make_ds, cfg):
    # trên ảnh 640x480: (0.02*640=12.8px, 0.4*480=192px) -> ar=15.0; (0.6*640=384px, 0.05*480=24px) -> ar=16.0
    got = run(make_ds, cfg, ["1 0.5 0.5 0.02 0.4", "0 0.5 0.5 0.6 0.05"])
    assert got == [("BOX_EXTREME_AR", 1, "warn"), ("BOX_EXTREME_AR", 2, "warn")]


def test_broken_and_zero_lines_do_not_crash(make_ds, cfg):
    got = run(make_ds, cfg, ["garbage", "93 0.5 0.5 0.01 0.8", "1 0.5 0.5 0.0 0.5", "1 0.5 0.5 0.02 0.4"])
    assert got == [("BOX_EXTREME_AR", 4, "warn")]


def test_threshold_comes_from_config(make_ds, cfg):
    cfg["aspect_ratio"] = {"max_ratio": 20.0}
    assert run(make_ds, cfg, ["1 0.5 0.5 0.02 0.4"]) == []
