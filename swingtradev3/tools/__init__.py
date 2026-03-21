"""Tool registry."""

from swingtradev3.tools.alerts import AlertsTool
from swingtradev3.tools.fii_dii_data import FiiDiiDataTool
from swingtradev3.tools.fundamental_data import FundamentalDataTool
from swingtradev3.tools.gtt_manager import GTTManager
from swingtradev3.tools.market_data import MarketDataTool
from swingtradev3.tools.news_search import NewsSearchTool
from swingtradev3.tools.options_data import OptionsDataTool
from swingtradev3.tools.order_execution import OrderExecutionTool
from swingtradev3.tools.risk_check import RiskCheckTool


TOOL_REGISTRY = {
    "get_eod_data": MarketDataTool().get_eod_data,
    "get_fundamentals": FundamentalDataTool().get_fundamentals,
    "get_options_data": OptionsDataTool().get_options_data,
    "search_news": NewsSearchTool().search_news,
    "get_fii_dii": FiiDiiDataTool().get_fii_dii,
    "place_order": OrderExecutionTool().place_order,
    "place_gtt": GTTManager().place_gtt,
    "check_risk": RiskCheckTool().check_risk,
}
