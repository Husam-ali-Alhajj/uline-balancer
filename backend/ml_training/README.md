# ML training (AI engineer)

Everything about training the recommendation model lives here, NOT in `app/`.
The backend only loads the finished model (see `app/ml/registry.py`).

Read first: `MASTER.md` section 7 (ML module) and `app/ml/interface.py`.

Suggested contents (create as needed):

- `generate_data.py`: builds synthetic instances, runs the GA, labels results with rules
- `train.py`: trains a small scikit-learn model with a fixed random seed
- `evaluate.py`: compares the model with the rule-based recommender (report honestly)
- `artifacts/`: the saved model (joblib) plus a version string

Install the extra dependencies with `pip install -r requirements-ml.txt`.
Open decisions that affect this work: D9 (what the model predicts), D10 (training data).
