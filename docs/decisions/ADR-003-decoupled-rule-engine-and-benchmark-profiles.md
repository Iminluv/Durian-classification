# ADR-003: Decoupled Rule Engine and Dynamic Benchmark Profiles

## Status
Accepted

## Date
2026-05-22

## Context
In agricultural fruit packing, quality grading criteria (Grade A, Grade B, Grade C, and Reject) frequently change based on:
- **Target Export Markets**: E.g., Premium China export requires strict 0-crack tolerance, whereas domestic retail allows minor superficial thorn splits.
- **Seasonal Quality Fluctuations**: Fruit harvest conditions vary by dry vs rainy season.
- **Customer Specifications**: Different buyers require tailored defect tolerance thresholds.

Baking grading classification rules directly into deep learning model outputs (e.g. training an end-to-end multi-class classifier that outputs "Grade A" directly) would require expensive re-labeling and re-training for every customer contract change.

## Decision
Decouple **defect detection** from **fruit grading** via a standalone **Rule Engine** (`core/rule_engine.py`) powered by dynamic JSON benchmark profiles stored in `config/benchmarks/*.json`:

1. **Object Detection Layer**: Deep learning model detects individual defects (`crack`, `dark_spot`, `fungus`, `thorn_split`, `reject`) with precise bounding boxes $[x, y, w, h]$ and confidence scores.
2. **Rule Evaluation Layer**: The `RuleEngine` evaluates bounding boxes against active benchmark rules:
   - Defect counts per grade (`max_count_A`, `max_count_B`, `max_count_C`).
   - Defect area ratio relative to fruit surface (`max_area_ratio`).
   - Hard quarantine overrides (`force_reject = true` for `fungus`).
   - Global cumulative limits across all defects combined (`max_total_defects`, `max_total_area_ratio`).
3. **Hot-Reloading**: Changes saved to benchmark profiles take effect immediately at runtime without restarting the vision service.

## Alternatives Considered

### 1. End-to-End Deep Learning Grade Classifier
- **Pros**: Direct image-to-grade output with a single model inference.
- **Cons**: Black-box decision making; невозможно to explain why a fruit was graded B instead of A; requires re-annotating hundreds of images and re-training the neural network whenever business grading criteria change.
- **Rejected**: Inflexible and unmaintainable for real-world agricultural commerce.

### 2. Hardcoded Python Grading Logic
- **Pros**: Fast execution.
- **Cons**: Requires code modifications, git commits, and developer intervention to change quality thresholds.
- **Rejected**: Factory operators and QA supervisors cannot edit Python code on packing line machines.

## Consequences
- **Positive**:
  - Full auditability: Every sorting event outputs exact human-readable reasons (e.g., `["crack count (1) exceeded limits for Grade A"]`).
  - QA managers can create, edit, clone, and switch benchmark profiles in real-time via the UI.
  - Zero downtime when adjusting grading standards.
- **Negative / Trade-offs**:
  - Requires maintaining benchmark JSON schemas and API validation.
  - Area estimation relies on 2D bounding box approximations relative to frame dimensions.
