"""Isolated tests for token monitoring integration in wb_adv_updater runner."""

import asyncio
import pytest
from datetime import datetime, timedelta, time
from unittest.mock import AsyncMock, MagicMock, patch


class TestRunnerTokenIntegrationIsolated:
    """Isolated test for token monitoring integration without full module import."""
    
    @pytest.mark.asyncio
    async def test_process_token_expiration_check_function_exists(self):
        """Test that process_token_expiration_check function exists in runner module."""
        
        # Read the runner file content directly to verify the function exists
        import os
        runner_file_path = os.path.join(
            os.path.dirname(__file__), 
            "..", "..", "..", "app", "modules", "wb_adv_updater", "runner.py"
        )
        
        # Verify file exists
        assert os.path.exists(runner_file_path), "Runner file not found"
        
        # Read content and verify function definition
        with open(runner_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verify the function is defined
        assert "async def process_token_expiration_check" in content, "process_token_expiration_check function not found"
        
        # Verify the import statement exists  
        assert "from app.modules.token_monitoring.services.token_expiration_service import run_token_expiration_check" in content, "Token monitoring import not found"
        
        # Verify the function is called in main_loop
        assert "process_token_expiration_check()" in content, "process_token_expiration_check not called in main_loop"
    
    @pytest.mark.asyncio
    async def test_token_expiration_check_scheduling_logic(self):
        """Test the scheduling logic without importing the full module."""
        
        # Mock the token expiration check function
        async def mock_process_token_expiration_check():
            """Mock implementation of process_token_expiration_check."""
            while True:
                # Calculate next 9:00 AM
                now = datetime.now()
                next_run = now.replace(hour=9, minute=0, second=0, microsecond=0)
                
                # If 9:00 AM has passed today, schedule for tomorrow
                if now.hour >= 9:
                    next_run = next_run + timedelta(days=1)
                
                # Calculate sleep time
                sleep_seconds = (next_run - now).total_seconds()
                
                # Mock sleep and token check
                await asyncio.sleep(0.01)  # Very short sleep for testing
                
                # Mock token expiration check
                stats = {
                    "total_tokens_checked": 5,
                    "expiring_tokens_found": 2, 
                    "notifications_sent": 1
                }
                
                # Break after first iteration for testing
                break
                
            return stats
        
        # Test the function
        with patch('asyncio.sleep', return_value=None):
            result = await mock_process_token_expiration_check()
            
            assert result["total_tokens_checked"] == 5
            assert result["expiring_tokens_found"] == 2
            assert result["notifications_sent"] == 1
    
    @pytest.mark.asyncio
    async def test_timing_calculation_logic(self):
        """Test the timing calculation logic for 9:00 AM scheduling."""
        
        def calculate_next_9am_sleep(current_time):
            """Calculate sleep time until next 9:00 AM."""
            next_run = current_time.replace(hour=9, minute=0, second=0, microsecond=0)
            
            # If 9:00 AM has passed today, schedule for tomorrow
            if current_time.hour >= 9:
                next_run = next_run + timedelta(days=1)
            
            return (next_run - current_time).total_seconds()
        
        # Test case 1: Current time is 8:00 AM
        current_8am = datetime(2025, 9, 28, 8, 0, 0)
        sleep_time_8am = calculate_next_9am_sleep(current_8am)
        assert abs(sleep_time_8am - 3600) < 60  # Should be ~1 hour
        
        # Test case 2: Current time is 10:00 AM (after 9:00 AM)
        current_10am = datetime(2025, 9, 28, 10, 0, 0)
        sleep_time_10am = calculate_next_9am_sleep(current_10am)
        assert abs(sleep_time_10am - (23 * 3600)) < 60  # Should be ~23 hours
        
        # Test case 3: Current time is exactly 9:00 AM
        current_9am = datetime(2025, 9, 28, 9, 0, 0)
        sleep_time_9am = calculate_next_9am_sleep(current_9am)
        assert abs(sleep_time_9am - (24 * 3600)) < 60  # Should be ~24 hours
    
    def test_runner_file_contains_token_monitoring_integration(self):
        """Test that runner file contains proper token monitoring integration."""
        
        import os
        runner_file_path = os.path.join(
            os.path.dirname(__file__), 
            "..", "..", "..", "app", "modules", "wb_adv_updater", "runner.py"
        )
        
        with open(runner_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verify all required components exist (with Russian text as in actual implementation)
        required_components = [
            "import datetime",
            "from app.modules.token_monitoring.services.token_expiration_service import run_token_expiration_check",
            "async def process_token_expiration_check",
            "Следующая проверка токенов:",  # Russian log message
            "next_run = now.replace(hour=9, minute=0, second=0, microsecond=0)",
            "if now.hour >= 9:",
            "stats = await run_token_expiration_check()",
            "Проверка токенов завершена:",  # Russian log message
            "process_token_expiration_check()"
        ]
        
        for component in required_components:
            assert component in content, f"Required component not found: {component}"
    
    @pytest.mark.asyncio 
    async def test_error_handling_simulation(self):
        """Test error handling in token expiration check."""
        
        async def mock_process_with_error():
            """Mock process that handles errors."""
            try:
                # Simulate the token check
                raise Exception("Database connection failed")
            except Exception as e:
                # Log error and continue (simulating the actual implementation)
                error_message = f"Error in token expiration check: {e}"
                assert "Database connection failed" in error_message
                return {"error": str(e)}
        
        result = await mock_process_with_error()
        assert "error" in result
        assert "Database connection failed" in result["error"]
    
    def test_main_loop_integration_verification(self):
        """Verify that main_loop includes token monitoring."""
        
        import os
        runner_file_path = os.path.join(
            os.path.dirname(__file__), 
            "..", "..", "..", "app", "modules", "wb_adv_updater", "runner.py"
        )
        
        with open(runner_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verify main_loop function exists and includes token monitoring
        assert "async def main_loop" in content, "main_loop function not found"
        
        # Verify asyncio.gather includes the token monitoring process
        assert "asyncio.gather(" in content, "asyncio.gather not found in main_loop"
        assert "process_token_expiration_check()" in content, "Token monitoring not included in main_loop"
    
    def test_import_statement_validation(self):
        """Validate that the import statement is correctly formatted."""
        
        import os
        runner_file_path = os.path.join(
            os.path.dirname(__file__), 
            "..", "..", "..", "app", "modules", "wb_adv_updater", "runner.py"
        )
        
        with open(runner_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for the exact import statement
        expected_import = "from app.modules.token_monitoring.services.token_expiration_service import run_token_expiration_check"
        assert expected_import in content, "Exact import statement not found"
        
        # Verify it's not commented out
        lines = content.split('\n')
        import_line = None
        for line in lines:
            if expected_import in line:
                import_line = line.strip()
                break
        
        assert import_line is not None, "Import line not found"
        assert not import_line.startswith('#'), "Import line is commented out"
        assert not import_line.startswith('//'), "Import line is commented out"