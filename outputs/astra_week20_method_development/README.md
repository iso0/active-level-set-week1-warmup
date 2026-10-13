**Week 20 independent method-development package**

Start with [the research design][design] and [the prepared implementation request][request]. This directory is separate from the thesis checkout. The package contains a numerical reference and synthetic checks; no new SPH model benchmark was run.

| File | Purpose |
|---|---|
| ASTRA_WEEK20_METHOD_DESIGN.md | Evidence, two researched directions, selected joint model, inference, acquisition, numerical results and limitations. |
| OPUS_METHOD_IMPLEMENTATION_REQUEST.md | Integration contract, controls, fixed first-pass priors, tuning boundaries and bounded NEW DEV experiment. |
| joint_depth_label_gp.py | Standalone NumPy/SciPy reference; no repository imports or network access. |
| run_checks.py | Controlled checks and one synthetic paid update. |
| prototype_results.json | Saved inputs, predictions, metrics, check outcomes, diagnostics, runtime versions and source hashes. |
| prototype_mechanisms.png | Three panels illustrating both mechanisms and prior sensitivity. |
| SELECTION_RECORD.json / CHANGE_LOG.md | Method selection before comparative toy results, and explicit later numerical repairs. |
| requirements.txt | Versions used for the reference and checks. |

Run locally from this directory:

~~~powershell
python run_checks.py --output prototype_results_reproduced.json
~~~

The tested environment was Python 3.14.4, NumPy 2.4.6 and SciPy 1.17.1. The two dependencies in requirements.txt are sufficient; plotting is not required. The code does not install packages or access the simulator. The output path above preserves the delivered record.

Minimal interface:

~~~python
import numpy as np
from joint_depth_label_gp import Config, JointDepthLabelGP

# X_ref: fixed feature-only training candidate pool, in frozen scaled coordinates.
# X_paid, y_paid, depth_paid_um: only simulations already queried.
z_paid = np.full(len(y_paid), np.nan)
valid = np.isfinite(depth_paid_um) & (depth_paid_um > 0)
z_paid[valid] = np.log(depth_paid_um[valid] / 111.0)
model = JointDepthLabelGP(X_ref, Config()).fit(X_paid, y_paid, z_paid)
p_test = model.predict_proba(X_test)       # X only; no test monitor
scores = model.acquisition(X_unpaid)      # caller excludes already paid IDs
~~~

Config defaults are for the one-dimensional controlled prototype. The implementation request specifies separate, explicit four-input development priors. The code conditions on fixed hyperparameters and uses a Laplace approximation. Passing every check does not establish superiority on real simulations or accurate rare-negative probabilities.

[design]: <C:/Users/ozgur/Documents/Codex/2026-10-10/files-pasted-by-the-user-you/outputs/week20_method_development/ASTRA_WEEK20_METHOD_DESIGN.md>
[request]: <C:/Users/ozgur/Documents/Codex/2026-10-10/files-pasted-by-the-user-you/outputs/week20_method_development/OPUS_METHOD_IMPLEMENTATION_REQUEST.md>
