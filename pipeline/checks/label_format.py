"""CHECK 2 — Dòng nhãn YOLO: sai định dạng, ID lớp lạ, box tràn ảnh, box rỗng, box lặp."""
from collections import defaultdict

from ..common import ERROR, WARN, Issue, iou_xywh, parse_yolo_line


def run(ds, cfg):
    """Check YOLO label files for format, ID, bounds, duplicate, and size issues."""
    lc = cfg["label_format"]
    tol = lc["overflow_tol"]
    min_px = lc["min_box_px"]
    max_frac = lc["max_box_frac"]
    dup_iou = lc["dup_box_iou"]
    n_classes = len(ds.classes)

    issues = []
    for lf in ds.label_files():
        stem = lf.stem
        lines = ds.read_label_lines(stem)
        if not lines:
            continue
        sz = ds.image_size(stem)
        seen_by_cls: dict[int, list[tuple[float, float, float, float]]] = defaultdict(list)

        for line_no, text in lines:
            try:
                cls_id, cx, cy, w, h = parse_yolo_line(text)
            except ValueError as exc:
                issues.append(
                    Issue("label_format", ERROR, "BAD_FORMAT", stem, f"dòng nhãn sai định dạng: {exc}", line=line_no)
                )
                continue

            if not (0 <= cls_id < n_classes):
                issues.append(
                    Issue(
                        "label_format",
                        ERROR,
                        "BAD_CLASS_ID",
                        stem,
                        f"id lớp {cls_id} ngoài khoảng 0..{n_classes - 1}",
                        line=line_no,
                        extra={"class_id": cls_id},
                    )
                )
                continue

            if w <= 0 or h <= 0:
                issues.append(
                    Issue("label_format", ERROR, "BOX_ZERO", stem, f"box có kích thước không hợp lệ w={w}, h={h}", line=line_no)
                )
                continue

            box = (cx, cy, w, h)
            overflow = max(
                0.0,
                -(cx - w / 2),
                -(cy - h / 2),
                (cx + w / 2) - 1.0,
                (cy + h / 2) - 1.0,
            )
            if overflow > tol:
                issues.append(
                    Issue(
                        "label_format",
                        ERROR,
                        "BOX_OUT_OF_IMAGE",
                        stem,
                        f"box tràn mép ảnh {overflow:.4f} > {tol}",
                        line=line_no,
                        extra={"overflow": round(overflow, 6)},
                    )
                )

            if any(iou_xywh(box, prev) > dup_iou for prev in seen_by_cls[cls_id]):
                issues.append(
                    Issue(
                        "label_format",
                        ERROR,
                        "DUP_BOX",
                        stem,
                        f"box lớp {cls_id} trùng với dòng trước (IoU > {dup_iou})",
                        line=line_no,
                    )
                )
            seen_by_cls[cls_id].append(box)

            if sz is not None:
                short_px = min(w * sz[0], h * sz[1])
                if short_px < min_px:
                    issues.append(
                        Issue(
                            "label_format",
                            WARN,
                            "BOX_TINY",
                            stem,
                            f"cạnh ngắn {short_px:.1f}px < {min_px}px",
                            line=line_no,
                            extra={"px": round(short_px, 2)},
                        )
                    )

            area_frac = w * h
            if area_frac > max_frac:
                issues.append(
                    Issue(
                        "label_format",
                        WARN,
                        "BOX_HUGE",
                        stem,
                        f"diện tích chuẩn hoá {area_frac:.3f} > {max_frac}",
                        line=line_no,
                        extra={"area_frac": round(area_frac, 4)},
                    )
                )

    return issues
