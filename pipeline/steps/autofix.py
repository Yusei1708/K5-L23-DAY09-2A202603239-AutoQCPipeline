"""BƯỚC 2/4 — Sửa tự động những lỗi bắt buộc mà máy sửa được AN TOÀN."""
from collections import defaultdict

import yaml

from ..common import ERROR, parse_yolo_line

REMOVE_CODES = {"DUP_IMAGE_EXACT", "DUP_IMAGE_NEAR", "LEAK_TEST", "CORRUPT_IMAGE", "BAD_SIZE"}
DROP_CODES = {"BAD_FORMAT", "BAD_CLASS_ID", "BOX_ZERO", "DUP_BOX"}


def _fix_yaml(ds, cfg) -> dict | None:
    """Rewrite data.yaml class names to match cfg['classes'] cleanly."""
    existing = {}
    if ds.yaml_path.exists():
        loaded = yaml.safe_load(ds.yaml_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            existing = loaded
    before = existing.get("names", "")
    new_names = dict(enumerate(cfg["classes"]))
    updated = {k: v for k, v in existing.items() if k != "names"}
    if "path" not in updated:
        updated["path"] = "."
    updated["names"] = new_names
    ds.yaml_path.write_text(
        yaml.safe_dump(updated, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return {
        "image": "data.yaml",
        "line": "",
        "action": "rename_classes",
        "before": str(before),
        "after": str(new_names),
    }


def _clip_box(line_text: str) -> tuple[bool, str]:
    """Clip a normalized YOLO line to [0, 1]; return (kept, formatted_line)."""
    cls_id, cx, cy, w, h = parse_yolo_line(line_text)
    x1 = max(0.0, min(1.0, cx - w / 2))
    y1 = max(0.0, min(1.0, cy - h / 2))
    x2 = max(0.0, min(1.0, cx + w / 2))
    y2 = max(0.0, min(1.0, cy + h / 2))
    nw = x2 - x1
    nh = y2 - y1
    if nw <= 1e-6 or nh <= 1e-6:
        return False, "(ngoài ảnh -> xoá dòng)"
    ncx = (x1 + x2) / 2
    ncy = (y1 + y2) / 2
    return True, f"{cls_id} {ncx:.6f} {ncy:.6f} {nw:.6f} {nh:.6f}"


def fix(ds, issues, cfg):
    """Apply safe deterministic autofixes for ERROR issues in ds and log every edit."""
    err_issues = [i for i in issues if i.severity == ERROR]
    fixes: list[dict] = []

    # 1. Remove rejected images and their labels first
    remove_stems = sorted({i.image for i in err_issues if i.code in REMOVE_CODES})
    removed: set[str] = set()
    for stem in remove_stems:
        img_p = ds.image_path(stem)
        lbl_p = ds.label_path(stem)
        had_file = (img_p is not None and img_p.exists()) or lbl_p.exists()
        before_name = img_p.name if img_p is not None else stem
        if img_p is not None:
            img_p.unlink(missing_ok=True)
        lbl_p.unlink(missing_ok=True)
        ds._size_cache.pop(stem, None)
        removed.add(stem)
        if had_file:
            fixes.append(
                {
                    "image": stem,
                    "line": "",
                    "action": "remove_image",
                    "before": before_name,
                    "after": "đã xoá ảnh và nhãn",
                }
            )

    # 2. Fix data.yaml class names (at most once)
    if any(i.code == "BAD_CLASS_NAME" for i in err_issues):
        row = _fix_yaml(ds, cfg)
        if row is not None:
            fixes.append(row)

    # 3. Record missing labels without fabricating empty label files
    missing_stems = sorted(
        {
            i.image
            for i in err_issues
            if i.code == "MISSING_LABEL_FILE" and i.image not in removed
        }
    )
    for stem in missing_stems:
        if not ds.label_path(stem).exists():
            fixes.append(
                {
                    "image": stem,
                    "line": "",
                    "action": "needs_label",
                    "before": "(không có file)",
                    "after": "chuyển người gán",
                }
            )

    # 4. Line-level fixes per remaining label file (drop_line overrides clip_box)
    drop_lines: dict[str, set[int]] = defaultdict(set)
    clip_lines: dict[str, set[int]] = defaultdict(set)
    for i in err_issues:
        if i.image in removed or i.line is None:
            continue
        if i.code in DROP_CODES:
            drop_lines[i.image].add(i.line)
        elif i.code == "BOX_OUT_OF_IMAGE":
            clip_lines[i.image].add(i.line)

    for stem in sorted(set(drop_lines) | set(clip_lines)):
        lp = ds.label_path(stem)
        if not lp.exists():
            continue
        drops = drop_lines[stem]
        clips = clip_lines[stem] - drops
        raw_lines = lp.read_text(encoding="utf-8", errors="replace").splitlines()
        new_lines: list[str] = []

        for line_no, text in enumerate(raw_lines, 1):
            if line_no in drops:
                fixes.append(
                    {
                        "image": stem,
                        "line": line_no,
                        "action": "drop_line",
                        "before": text.strip(),
                        "after": "(xoá dòng)",
                    }
                )
                continue
            if line_no in clips:
                try:
                    kept, out_text = _clip_box(text)
                except ValueError:
                    fixes.append(
                        {
                            "image": stem,
                            "line": line_no,
                            "action": "drop_line",
                            "before": text.strip(),
                            "after": "(xoá dòng)",
                        }
                    )
                    continue
                if not kept:
                    fixes.append(
                        {
                            "image": stem,
                            "line": line_no,
                            "action": "drop_line",
                            "before": text.strip(),
                            "after": "(xoá dòng)",
                        }
                    )
                    continue
                new_lines.append(out_text)
                fixes.append(
                    {
                        "image": stem,
                        "line": line_no,
                        "action": "clip_box",
                        "before": text.strip(),
                        "after": out_text,
                    }
                )
                continue
            new_lines.append(text)

        lp.write_text("\n".join(new_lines) + ("\n" if new_lines else ""), encoding="utf-8")

    return fixes
