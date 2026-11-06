| city | front_size_N | rho_O1_ml_plus1p5 | rho_O1_ml_plus3p0 | rho_O2_plus1p5 | rho_O2_plus3p0 |
| --- | --- | --- | --- | --- | --- |
| Shimla | 37 | 0.7524 | 0.5673 | 0.9886 | 0.9798 |
| Jodhpur | 26 | 0.9938 | 0.9906 | 0.9993 | 0.9993 |
| New_Delhi | 44 | 0.9062 | 0.3781 | 0.9964 | 0.9965 |
| Mumbai | 14 | 0.9956 | 0.9945 | 0.9417 | 0.9385 |
| Bengaluru | 1 | not testable (N<5) | not testable (N<5) | not testable (N<5) | not testable (N<5) |

> [!NOTE]
> **Formula Used**: Spearman rank correlation coefficient $\rho = \frac{\mathrm{cov}(\mathrm{rank}(X), \mathrm{rank}(Y))}{\sigma_{\mathrm{rank}(X)} \sigma_{\mathrm{rank}(Y)}}$. Calculated via Python `scipy.stats.spearmanr(valid[col_base], valid[col_scen])`. Ties in ranks are resolved by assigning fractional average mid-ranks to tied positions.
