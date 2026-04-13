import reflex as rx

from dashboard.components.sidebar import layout
from dashboard.components.command_center import command_center
from dashboard.styles import global_styles
from dashboard.state import GlobalState
from dashboard.pages.portfolio import portfolio
from dashboard.pages.research import research
from dashboard.pages.approvals import approvals
from dashboard.pages.knowledge import knowledge
from dashboard.pages.activity import activity

def index() -> rx.Component:
    return layout(
        command_center()
    )

app = rx.App(style=global_styles)
app.add_page(index, route="/", title="Kepler Command Center", on_load=GlobalState.fetch_initial_data)
app.add_page(portfolio, route="/portfolio", title="Portfolio | Kepler", on_load=GlobalState.fetch_initial_data)
app.add_page(research, route="/research", title="Research | Kepler", on_load=GlobalState.fetch_initial_data)
app.add_page(approvals, route="/approvals", title="Approvals | Kepler", on_load=GlobalState.fetch_initial_data)
app.add_page(knowledge, route="/knowledge", title="Knowledge Graph | Kepler", on_load=GlobalState.fetch_initial_data)
app.add_page(activity, route="/activity", title="Agent Activity | Kepler", on_load=GlobalState.fetch_initial_data)
