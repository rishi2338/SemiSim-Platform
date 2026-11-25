# SemiSim — Python + Streamlit

A Python rewrite of the supplied SemiSim web platform. It preserves the five semiconductor material datasets, Varshni bandgap equation, intrinsic carrier concentration, simplified conductivity model, quick simulation, plots, heuristic application ranking and PDF experiment report.

## Run locally

```bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit (usually http://localhost:8501).

## Deploy on Streamlit Community Cloud

1. Push this folder to a GitHub repository.
2. Open https://share.streamlit.io/
3. Select the repository, branch, and `app.py`.
4. Deploy.

## Notes

- `Voltage` is retained in the interface because it exists in the original project, but the original conductivity formula does not use it.
- Optimization scores are heuristic rankings copied from the original app's weighting logic; they are not validated device-performance predictions.
- The band diagram is an illustrative energy-gap view.
