from __future__ import annotations


def compute_wfe_ratio(in_sample_return: float, out_of_sample_return: float) -> float:
    if in_sample_return == 0:
        return 0.0
    return out_of_sample_return / in_sample_return
