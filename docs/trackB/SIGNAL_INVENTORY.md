# Track B signal inventory

The machine-readable inventory is [`SIGNAL_INVENTORY.csv`](SIGNAL_INVENTORY.csv). It deliberately separates a simulator field, a command, a derived feature, a physical measurement, and a hidden label.

## Current classification summary

| Class | Current entries | Interpretation |
|---|---|---|
| experimentally observable online | none yet | The repository contains no setup-specific measurement validation sufficient to award this status. |
| potentially observable / literature-dependent | substrate temperature; transverse width; maximum positive width change; early-prefix width change; melt-pool length/area | Plausible candidates, each requiring modality-specific evidence and a matched definition. |
| simulation-only / hidden | internal depth/penetration; internal particle/phase/void topology; manual `has_keyhole` | These must not be supplied to an online predictor under the current evidence. |
| uncertain | P, VX, LS as delivered quantities; `log h`; width-monitor missingness; optical temperature/intensity; post-process defect outcome | Availability, definition, or timing must be resolved before use. |

Commanded P and VX may be recorded in a real machine, but this repository does not document that interface or prove equivalence to delivered power and realized speed. They therefore remain “uncertain” rather than being promoted by convention.

## Width proof of concept

The old 405-simulation Phase 2.1R analysis found that `max_positive_delta_W` contained modest additional ranking information beyond the four process inputs. The effect was predominantly a startup-width phenomenon: the retained claim ledger reports that 95.4% of trace maxima occurred in the first 5% of the trace. This does not show a directly observed keyhole-onset event. Phase 2.2 did not convert the feature into a successful acquisition policy.

The defensible statement is: **a transient-like simulation width signal contains modest internal information about a hidden simulation-labelled state.** Experimental observability, domain transfer, and real-time feasibility remain open.

## Promotion rule

A signal may move to “experimentally observable online” only after recording all of the following:

1. measurement hardware and physical quantity;
2. spatial support, sampling rate, latency, and synchronization;
3. calibration, uncertainty, saturation, and missingness;
4. a mapping between experimental and simulation definitions;
5. availability strictly before the intended inference time;
6. evidence for the actual experimental setup, not only a generic literature example.
