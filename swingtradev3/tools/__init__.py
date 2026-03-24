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

RESEARCH_TOOL_REGISTRY = {
    "get_eod_data": TOOL_REGISTRY["get_eod_data"],
    "get_fundamentals": TOOL_REGISTRY["get_fundamentals"],
    "get_options_data": TOOL_REGISTRY["get_options_data"],
    "search_news": TOOL_REGISTRY["search_news"],
    "get_fii_dii": TOOL_REGISTRY["get_fii_dii"],
}

RESEARCH_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_eod_data",
            "description": "Fetch end-of-day market data and computed indicators for one NSE ticker.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "NSE ticker symbol such as INFY or SBIN"}
                },
                "required": ["ticker"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_fundamentals",
            "description": "Fetch cached or upstream fundamentals for one NSE ticker.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "NSE ticker symbol such as INFY or SBIN"}
                },
                "required": ["ticker"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_options_data",
            "description": "Fetch options positioning or derivatives context for one ticker when available.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "NSE ticker symbol such as INFY or SBIN"}
                },
                "required": ["ticker"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_news",
            "description": "Search recent news headlines relevant to a stock or theme.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural-language news query"}
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_fii_dii",
            "description": "Fetch aggregate FII/DII flow context for the current market session.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
]
