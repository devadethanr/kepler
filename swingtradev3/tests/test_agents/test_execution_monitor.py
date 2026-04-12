from __future__ import annotations

import pytest
import json
from unittest.mock import patch, MagicMock
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.execution.monitor import execution_monitor
from models import AccountState, PositionState
from datetime import datetime

@pytest.mark.asyncio
async def test_execution_monitor_trailing():
    """
    Test that the ExecutionMonitor correctly trails stops when profit targets are hit.
    """
    # 1. Setup mock state with a profitable position
    now = datetime.now()
    initial_state = AccountState(
        cash_inr=10000,
        positions=[
            PositionState(
                ticker="RELIANCE",
                quantity=10,
                entry_price=1000,
                current_price=1100, # 10% Profit
                stop_price=950,
                target_price=1200,
                opened_at=now,
                stop_gtt_id="gtt-123"
            )
        ]
    )
    
    # 2. Mock storage and GTT manager in the module where they are USED
    with patch("agents.execution.monitor.read_json", return_value=initial_state.model_dump(mode="json")):
        with patch("agents.execution.monitor.write_json") as mock_write:
            with patch("tools.execution.gtt_manager.GTTManager.modify_gtt_async") as mock_modify:
                with patch("tools.execution.alerts.AlertsTool.send_alert") as mock_alert:
                    # Mock the get_gtt_async to avoid actual API calls in PositionChecker
                    with patch("tools.execution.gtt_manager.GTTManager.get_gtt_async", return_value=MagicMock(status="active")):
                        
                        # 3. Setup Runner
                        runner = Runner(
                            app_name="research",
                            agent=execution_monitor,
                            session_service=InMemorySessionService(),
                            auto_create_session=True
                        )
                        
                        # 4. Run Monitor
                        events = []
                        async for event in runner.run_async(
                            user_id="system",
                            session_id="monitor_session",
                            new_message=types.Content(role="user", parts=[types.Part(text="Check positions")])
                        ):
                            events.append(event)
                            
                        # 5. Verify trailing logic
                        # trail_to_pct is 10.0 in config.yaml. Our profit is 10%.
                        # It should trigger.
                        
                        assert mock_modify.called, "GTT modification was not triggered"
                        assert mock_write.called, "State was not saved after trailing"
                        print(f"\n✅ Execution Test Passed: Monitor correctly triggered trailing stop for RELIANCE.")
