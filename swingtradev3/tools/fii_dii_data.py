from __future__ import annotations

from datetime import date


class FiiDiiDataTool:
    def get_fii_dii(self) -> dict[str, object]:
        return {"date": date.today().isoformat(), "fii_net_crore": None, "dii_net_crore": None, "sector_flows": {}}
