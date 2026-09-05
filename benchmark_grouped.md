### Precision / Recall / F1 / AP (IoU >= 0.5)

| Class | GT | TP | FP | FN | Precision | Recall | F1 | AP@0.5 |
|---|---|---|---|---|---|---|---|---|
| `crack` | 87 | 51 | 47 | 36 | 0.520 | 0.586 | 0.551 | 0.385 |
| `fungus_or_dark_spot` | 106 | 37 | 59 | 69 | 0.385 | 0.349 | 0.366 | 0.209 |
| `thorn_split` | 65 | 0 | 68 | 65 | 0.000 | 0.000 | 0.000 | 0.000 |

**Micro P/R/F1:** 0.336 / 0.341 / 0.338  
**Macro P/R/F1:** 0.302 / 0.312 / 0.306  
**mAP@0.5:** 0.198

### Confusion Matrix (rows = ground truth, cols = predicted)

| GT \\ Pred | crack | fungus_or_dark_spot | thorn_split | background |
|---|---|---|---|---|
| `crack` | 51 | 0 | 0 | 36 |
| `fungus_or_dark_spot` | 0 | 37 | 0 | 69 |
| `thorn_split` | 0 | 0 | 0 | 65 |
| `background` | 47 | 59 | 68 | 0 |
