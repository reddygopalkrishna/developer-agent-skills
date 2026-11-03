# Data leakage checklist

Leakage means the model sees information during training or evaluation that it won't have when making real predictions. It produces great offline scores and poor production results. Check every item before trusting a number.

## Target leakage (features that encode the answer)

- [ ] For every feature, ask: "Would I know this value at the moment the prediction is made?" If it's set or updated after the outcome, drop it.
- [ ] Look for proxies of the label: status fields, "closed reason", refund flags, follow-up appointments, downstream system IDs created only for positive cases.
- [ ] Aggregates (counts, averages, last values) are computed only from data before the prediction time.
- [ ] Rank features by importance and inspect the top ones. A single feature with overwhelming importance is a red flag.
- [ ] Train a model on each top feature alone. If one feature nearly solves the task, find out why.

## Temporal leakage (using the future)

- [ ] Time-dependent problems use a time-based split, not a random one.
- [ ] Each training row uses a point-in-time view of the data ("as of" joins), not today's values of slowly changing attributes.
- [ ] Rolling windows and lag features are computed strictly from past rows.
- [ ] There is a gap between training and evaluation periods when labels take time to mature (chargebacks, churn windows).
- [ ] Backfilled or corrected historical data is not used in a way that wasn't available at the time.

## Preprocessing leakage (fit on data you evaluate on)

- [ ] Scalers, imputers, encoders (including target encoding), PCA, feature selection and text vectorizers are fit on training data only, inside each CV fold.
- [ ] Oversampling or synthetic samples are created after the split, on training data only.
- [ ] Hyperparameters and thresholds are chosen on validation data, never the test set.
- [ ] Everything above lives in a pipeline object that cross-validation refits per fold.

## Split leakage (same thing in train and test)

- [ ] Exact and near-duplicate rows are removed or kept within one split.
- [ ] All rows for the same entity (user, patient, device, session, document, image source) are in the same split (group split).
- [ ] Augmented copies of a sample stay in the same split as the original.
- [ ] For text or images scraped from the web, check overlap between test data and any pretraining or training corpus where possible.

## Evaluation leakage (process problems)

- [ ] The test set was not looked at while developing features or models.
- [ ] Results are not the best of many runs evaluated on the test set.
- [ ] The evaluation population matches the population the model will serve (same filters, same time of prediction).
- [ ] Labels for evaluation were produced the same way production labels will be.

## Quick sanity checks

- Shuffle the labels and retrain: performance should drop to chance. If not, something leaks through the pipeline or the evaluation is broken.
- Compare validation score with a later out-of-time sample: a large drop suggests temporal leakage or drift.
- Score too good to be true for the domain? Assume leakage until proven otherwise.
