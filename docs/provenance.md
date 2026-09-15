# Provenance

## Artifact lineage

```
ThermalPlant.mo
    --compiled_by-->
OpenModelica
    --exports-->
ThermalPlant.fmu
    --simulates-->
temperature_sim
    --combined_with-->
synthetic measurement dataset
    --trains-->
ResidualMLP checkpoint
    --produces-->
predicted residual
    --composed_into-->
hybrid prediction
```

Each arrow corresponds to a concrete file/step in this repository:

| Step | Source | Producer | Output |
|---|---|---|---|
| compiled_by | `modelica/ThermalPlant.mo` | `scripts/export_fmu.py` | `artifacts/fmu/ThermalPlant.fmu` |
| simulates | `artifacts/fmu/ThermalPlant.fmu` | `hybrid_model.fmu_simulator.FMUSimulator` | `temperature_sim` column |
| combined_with | `temperature_sim` + `data/raw/synthetic_measurements.csv` | `hybrid_model.dataset.build_dataset` | `data/processed/residual_dataset.csv` |
| trains | `residual_dataset.csv` | `hybrid_model.training.train_residual_model` | `artifacts/checkpoints/residual_model.pt` |
| produces | checkpoint + FMU step | `hybrid_model.inference.run_hybrid_inference` | `predicted_residual` column |
| composed_into | `temperature_sim` + `predicted_residual` | same | `results/hybrid_predictions.csv` |

## Suggested provenance record

Fill in and store alongside each trained model (e.g. as
`artifacts/checkpoints/provenance.yaml`):

```yaml
model_id:
model_type: ResidualMLP
source_file: src/hybrid_model/models.py
tool: PyTorch
tool_version:
fmu_path: artifacts/fmu/ThermalPlant.fmu
fmu_sha256:
input_variables: [power, ambient]
output_variables: [temperature]
parameters:
  R: 0.5
  C: 100.0
  T_start: 25.0
dataset_path: data/processed/residual_dataset.csv
dataset_sha256:
checkpoint_path: artifacts/checkpoints/residual_model.pt
checkpoint_sha256:
training_seed: 42
training_configuration: configs/default.yaml
created_at:
```

Populate `*_sha256` fields using the commands in
`docs/reproducibility.md`, and `created_at` with the UTC timestamp of the
training run. This record is what makes a given `hybrid_predictions.csv`
traceable back to the exact Modelica source, FMU, dataset, and checkpoint
that produced it.
