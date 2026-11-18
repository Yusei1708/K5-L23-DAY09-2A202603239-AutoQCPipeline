"""BƯỚC 4 — Cửa chặn: quyết định Release / Hold / Rework."""
from ..common import ERROR, WARN


def decide(issues, image_stems, cfg, reviewed=frozenset()):
    """Decide Release, Hold, or Rework from remaining errors, warnings, and reviewed stems."""
    stems = set(image_stems)
    reviewed_set = set(reviewed)
    hold_thr = cfg["gate"]["warn_ratio_hold"]

    n_errors = sum(1 for i in issues if i.severity == ERROR)
    warn_images = {
        i.image
        for i in issues
        if i.severity == WARN and i.image in stems and i.image not in reviewed_set
    }

    n_images = len(stems)
    n_warn_images = len(warn_images)
    raw_ratio = (n_warn_images / n_images) if n_images else 0.0
    warn_ratio = round(raw_ratio, 4)

    reasons: list[str] = []
    if n_errors >= 1:
        decision = "Rework"
        reasons.append(f"còn {n_errors} lỗi bắt buộc (ERROR), chặn phát hành")
        if n_warn_images:
            reasons.append(
                f"{n_warn_images}/{n_images} ảnh còn cảnh báo chưa duyệt ({warn_ratio:.2%})"
            )
    elif raw_ratio >= hold_thr:
        decision = "Hold"
        reasons.append(
            f"0 lỗi bắt buộc, nhưng tỉ lệ ảnh còn cảnh báo chưa duyệt là "
            f"{n_warn_images}/{n_images} ({warn_ratio:.2%}) >= ngưỡng {hold_thr:.2%}"
        )
    else:
        decision = "Release"
        reasons.append(
            f"0 lỗi bắt buộc; tỉ lệ ảnh còn cảnh báo là "
            f"{n_warn_images}/{n_images} ({warn_ratio:.2%}) < ngưỡng {hold_thr:.2%}"
        )

    return {
        "decision": decision,
        "n_errors": n_errors,
        "n_warn_images": n_warn_images,
        "n_images": n_images,
        "warn_ratio": warn_ratio,
        "reasons": reasons,
    }
