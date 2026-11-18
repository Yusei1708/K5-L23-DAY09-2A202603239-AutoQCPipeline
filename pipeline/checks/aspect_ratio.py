"""Check bổ sung (thưởng +3) — phát hiện box có tỉ lệ khung hình (pixel aspect ratio) lệch cực đoan."""
from ..common import WARN, Issue, parse_yolo_line


def run(ds, cfg):
    """Flag boxes whose pixel width/height aspect ratio exceeds max_ratio."""
    max_ratio = (cfg.get("aspect_ratio") or {}).get("max_ratio", 6.0)
    n_classes = len(ds.classes)
    issues: list[Issue] = []

    for lf in ds.label_files():
        stem = lf.stem
        lines = ds.read_label_lines(stem)
        if not lines:
            continue
        sz = ds.image_size(stem)
        if sz is None:
            continue
        img_w, img_h = sz

        for line_no, text in lines:
            try:
                cls_id, _, _, w, h = parse_yolo_line(text)
            except ValueError:
                continue
            if not (0 <= cls_id < n_classes) or w <= 0 or h <= 0:
                continue

            bw = w * img_w
            bh = h * img_h
            short_side = min(bw, bh)
            if short_side <= 0:
                continue
            ratio = max(bw / bh, bh / bw)
            if ratio > max_ratio:
                issues.append(
                    Issue(
                        "aspect_ratio",
                        WARN,
                        "BOX_EXTREME_AR",
                        stem,
                        f"tỉ lệ khung hình {ratio:.2f}:1 ({bw:.1f}x{bh:.1f}px) > {max_ratio}",
                        line=line_no,
                        extra={"ratio": round(ratio, 2), "px": [round(bw, 1), round(bh, 1)]},
                    )
                )

    return issues
