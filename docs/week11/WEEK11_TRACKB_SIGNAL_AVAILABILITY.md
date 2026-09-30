# Week 11 Track B metadata availability

This table records path presence only. No monitor value, image, archive, class, or outcome was opened, and no Track B statistic was computed.

| Item | Status for 185 new simulations | What is established |
|---|---:|---|
| Melt/gas position-bounds files, which are source inputs for width/length/penetration derivation | PRESENT (185/185) | Filename and object metadata only; derived trajectories are not validated |
| Temperature monitor files | PRESENT (185/185) | Filename and object metadata only |
| `time.dat`, `dt.dat`, `iter.dat` | PRESENT (185/185) | Filename and object metadata only |
| Explicit area monitor | ABSENT from the 34 listed monitor names | No explicit area file was identified |
| Laser-on timing metadata | UNRESOLVED | Filename inventory does not establish it |
| Raw geometry inside archive | UNRESOLVED | Archives were not opened |
| Images and archives | PRESENT as metadata (185/185) | Contents and integrity were not inspected |
| Experimental observability | UNRESOLVED | Simulation-file presence is not sensor evidence |

Six monitor object IDs recur across 179 simulations: `time.dat`, `dt.dat`, `iter.dat`, `minimum-heat-capacity_gas.dat`, `minimum-heat-capacity_substrate.dat`, and `particle-number_gas.dat`. These are file-level identity matches, not duplicate simulations or exclusions.
