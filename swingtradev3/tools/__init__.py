"""Tool registry."""

from swingtradev3.tools.execution.alerts import AlertsTool
from swingtradev3.tools.execution.gtt_manager import GTTManager
from swingtradev3.tools.execution.order_execution import OrderExecutionTool
from swingtradev3.tools.execution.risk_check import RiskCheckTool
from swingtradev3.tools.market.fii_dii_data import FiiDiiDataTool
from swingtradev3.tools.market.fundamental_data import FundamentalDataTool
from swingtradev3.tools.market.market_data import MarketDataTool
from swingtradev3.tools.market.news_search import NewsSearchTool
from swingtradev3.tools.market.options_data import OptionsDataTool


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
