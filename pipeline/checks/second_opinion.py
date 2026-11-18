"""CHECK 6 — Ý kiến thứ hai: so nhãn với một model lớn hơn (yolo26l)."""
from ..common import WARN, Issue, iou_xywh, parse_yolo_line
from ..model_cache import get_preds


def run(ds, cfg, preds=None):
    """Compare existing YOLO labels against stronger model predictions to flag warnings."""
    if preds is None:
        preds = get_preds(ds, cfg, "checker")

    sc = cfg["second_opinion"]
    conf_thr = sc["conf"]
    min_area = sc["min_area_px"]
    fp_conf = sc["fp_conf"]
    iou_missing = sc["iou_missing"]
    iou_match = sc["iou_match"]
    iou_loose = sc["iou_loose"]
    n_classes = len(ds.classes)

    issues: list[Issue] = []
    for p in ds.image_files():
        stem = p.stem
        if stem not in preds:
            continue
        lines = ds.read_label_lines(stem)
        if lines is None:
            continue
        sz = ds.image_size(stem)
        if sz is None:
            continue

        img_w, img_h = sz
        gt_boxes = ds.valid_boxes(stem)
        all_preds = preds[stem]

        # 1. Prediction -> label comparisons in prediction order
        for r in all_preds:
            p_cls = int(r[0])
            p_conf = float(r[1])
            pcx, pcy, pw, ph = float(r[2]), float(r[3]), float(r[4]), float(r[5])
            if p_conf < conf_thr or (pw * img_w) * (ph * img_h) < min_area:
                continue

            p_box = (pcx, pcy, pw, ph)
            cands = []
            for gt in gt_boxes:
                iou = iou_xywh(p_box, gt[1:])
                if iou >= iou_missing:
                    cands.append((gt, iou))

            if not cands:
                cls_name = ds.classes[p_cls] if 0 <= p_cls < n_classes else str(p_cls)
                issues.append(
                    Issue(
                        "second_opinion",
                        WARN,
                        "POSSIBLE_MISSING",
                        stem,
                        f"model dự đoán {cls_name} (conf={p_conf:.2f}) nhưng không khớp nhãn nào",
                        extra={"conf": round(p_conf, 4), "pred_cls": p_cls},
                    )
                )
                continue

            same_cls = [iou for gt, iou in cands if gt[0] == p_cls]
            if same_cls:
                best_iou = max(same_cls)
                if best_iou < iou_loose:
                    issues.append(
                        Issue(
                            "second_opinion",
                            WARN,
                            "POSSIBLE_LOOSE_BOX",
                            stem,
                            f"box nhãn cùng lớp nhưng IoU={best_iou:.2f} < {iou_loose}",
                            extra={"conf": round(p_conf, 4), "iou": round(best_iou, 4)},
                        )
                    )
                continue

            best_gt, best_iou = max(cands, key=lambda item: item[1])
            if best_iou >= iou_match:
                pred_name = ds.classes[p_cls] if 0 <= p_cls < n_classes else str(p_cls)
                lbl_name = ds.classes[best_gt[0]] if 0 <= best_gt[0] < n_classes else str(best_gt[0])
                issues.append(
                    Issue(
                        "second_opinion",
                        WARN,
                        "POSSIBLE_WRONG_CLASS",
                        stem,
                        f"nghi sai lớp: nhãn là {lbl_name}, model dự đoán {pred_name} (conf={p_conf:.2f}, IoU={best_iou:.2f})",
                        extra={"conf": round(p_conf, 4), "iou": round(best_iou, 4)},
                    )
                )

        # 2. Label -> prediction comparisons for potential false positives
        fp_preds = [r for r in all_preds if float(r[1]) >= fp_conf]
        for line_no, text in lines:
            try:
                l_cls, lcx, lcy, lw, lh = parse_yolo_line(text)
            except ValueError:
                continue
            if not (0 <= l_cls < n_classes):
                continue

            l_box = (lcx, lcy, lw, lh)
            max_iou = max((iou_xywh(l_box, r[2:6]) for r in fp_preds), default=0.0)
            if not fp_preds or max_iou < iou_missing:
                issues.append(
                    Issue(
                        "second_opinion",
                        WARN,
                        "POSSIBLE_FALSE_POS",
                        stem,
                        f"box dòng {line_no} không khớp dự đoán nào của model (max IoU={max_iou:.2f})",
                        line=line_no,
                        extra={"iou": round(max_iou, 4)},
                    )
                )

    return issues
