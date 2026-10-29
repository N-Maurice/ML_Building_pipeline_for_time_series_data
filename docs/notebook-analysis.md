# Notebook analysis

## Scope and approach

The notebook covers preprocessing, six descriptive questions, and a seven-day forecasting experiment. Orders are joined to item totals at order granularity before daily aggregation, avoiding inflated counts from a one-to-many join. The questions cover trend, weekday patterns, lag correlation, historical moving averages, order volume and basket value, and unusually high sales.

The supplied CSV inventory contains 99,441 orders and 112,650 item rows. Additional tables contain 99,441 customers, 3,095 sellers, 32,951 products, 71 category translations, 103,886 payments, 99,224 reviews, and 1,000,163 geolocation rows. These are raw record counts, not unique-key counts.

## Methodological strengths

- Duplicate and key checks protect the joins. Invalid item prices exclude the whole affected order, and missing monetary values are reported.
- The target definition distinguishes merchandise value from freight, profit, and realized revenue. Orders are not filtered by their eventual status, which would use information unavailable at purchase time.
- Forecast features use observations available at the end of the origin day. A direct multi-output model predicts seven daily values.
- Chronological train, validation, and test periods replace random splits. Seven-row gaps protect against overlapping training targets, with explicit assertions.
- A seasonal-naive baseline provides a meaningful comparison. Training-only cross-validation tunes the forest; validation selects the approach before the final test.
- Daily MAE, daily RMSE, weekly-total MAE, and horizon-specific errors cover different aspects of performance.

## Limitations and follow-up priorities

1. **Execution portability:** local repository data are not discovered automatically. Local use requires changing the input root, output folder, and archive destination. Dependency versions are not locked, although some runtime versions are exported.
2. **Incomplete execution evidence:** the supplied notebook has execution counts on 18 code cells and no saved error outputs. This does not establish that every cell ran successfully in one clean session. Rerun all cells before quoting model results.
3. **Coverage assumptions:** the January 2017–August 2018 window is chosen manually. Sparse collection edges, especially the final month, need investigation. Zero-filled days represent no recorded usable sales, not verified zero customer demand.
4. **Small evaluation sample:** validation and test each cover four weekly origins. Rankings and error estimates may change across periods; broader rolling-origin evaluation would improve confidence. Overlapping CV windows produce dependent errors.
5. **Business objective alignment:** selection uses daily MAE even though the project question concerns the seven-day total. This choice is declared clearly, but should be agreed with the team before future experiments.
6. **Feature and model limits:** same-day descriptive correlations are not causal evidence. Random forests cannot readily extrapolate sustained growth beyond historical target ranges; no external drivers are available.
7. **Artifact hygiene:** exports reuse a fixed output folder. If a forest is saved on one run and a seasonal baseline wins later, the old model file can remain in the folder and ZIP. Clear the output folder before a fresh run and consult `metadata.json` when consuming artifacts.

## Review validation

All Python code cells passed syntax parsing, and the notebook passed `nbformat` schema validation. Raw CSV rows and headers were inspected. This review did not rerun the complete model-training workflow or verify the current upstream dataset license. The existing notebook and source CSVs were preserved without modification.
