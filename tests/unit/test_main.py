"""Unit tests for main entry point."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from nightscout_backup_bot.main import _run_api_server, main  # noqa: SLF001


class TestRunAPIServer:
    """Test _run_api_server function."""

    def test_run_api_server_success(self) -> None:
        """Test API server starts successfully."""
        mock_app = MagicMock()
        mock_config = MagicMock()
        mock_server = MagicMock()

        with (
            patch("nightscout_backup_bot.main.logger") as mock_logger,
            patch("nightscout_backup_bot.api.server.app", mock_app),
            patch("nightscout_backup_bot.main.uvicorn.Config", return_value=mock_config) as mock_config_class,
            patch("nightscout_backup_bot.main.uvicorn.Server", return_value=mock_server) as mock_server_class,
            patch("nightscout_backup_bot.main.asyncio.new_event_loop") as mock_new_loop,
            patch("nightscout_backup_bot.main.asyncio.set_event_loop") as mock_set_loop,
        ):
            # Mock event loop to avoid blocking
            mock_loop = MagicMock()
            mock_new_loop.return_value = mock_loop

            # Make run_until_complete return immediately
            mock_loop.run_until_complete = MagicMock()

            _run_api_server()

            # Verify logger was called
            mock_logger.info.assert_called_once()
            # Verify Config was created with correct parameters
            mock_config_class.assert_called_once_with(mock_app, host="0.0.0.0", port=8000, log_level="info")
            # Verify Server was created with config
            mock_server_class.assert_called_once_with(mock_config)
            # Verify event loop was set up and server.serve was called
            mock_new_loop.assert_called_once()
            mock_set_loop.assert_called_once()
            mock_loop.run_until_complete.assert_called_once()

    def test_run_api_server_import_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test API server handles import errors gracefully."""
        import sys
        import types

        # Create a fake module that raises ImportError when 'app' is accessed
        fake_module = types.ModuleType("nightscout_backup_bot.api.server")

        def raise_on_app_access() -> None:
            raise ImportError("Cannot import app")

        # Make accessing 'app' raise ImportError
        fake_module.__getattr__ = lambda name: raise_on_app_access() if name == "app" else None

        # Replace module in sys.modules
        with patch.dict(sys.modules, {"nightscout_backup_bot.api.server": fake_module}):
            with patch("nightscout_backup_bot.main.logger") as mock_logger:
                _run_api_server()

                # Verify error was logged
                mock_logger.error.assert_called_once()
                error_call = mock_logger.error.call_args
                assert "API server failed to start" in str(error_call)
                assert "error" in error_call.kwargs

    def test_run_api_server_runtime_error(self) -> None:
        """Test API server handles runtime errors gracefully."""
        mock_app = MagicMock()
        mock_config = MagicMock()
        mock_server = MagicMock()
        mock_server.serve = MagicMock(side_effect=RuntimeError("Server failed"))

        with (
            patch("nightscout_backup_bot.main.logger") as mock_logger,
            patch("nightscout_backup_bot.api.server.app", mock_app),
            patch("nightscout_backup_bot.main.uvicorn.Config", return_value=mock_config),
            patch("nightscout_backup_bot.main.uvicorn.Server", return_value=mock_server),
            patch("nightscout_backup_bot.main.asyncio.new_event_loop") as mock_new_loop,
            patch("nightscout_backup_bot.main.asyncio.set_event_loop"),
        ):
            # Mock event loop
            mock_loop = MagicMock()
            mock_new_loop.return_value = mock_loop
            # Make run_until_complete raise RuntimeError
            mock_loop.run_until_complete = MagicMock(side_effect=RuntimeError("Server failed"))

            _run_api_server()

            # Verify error was logged
            mock_logger.error.assert_called_once()
            error_call = mock_logger.error.call_args
            assert "API server failed to start" in str(error_call)


class TestMain:
    """Test main function."""

    def test_main_success_with_api_enabled(self) -> None:
        """Test main function runs successfully with API enabled."""
        mock_bot = MagicMock()
        mock_bot.run = MagicMock()

        with (
            patch("nightscout_backup_bot.main.setup_logging") as mock_setup_logging,
            patch("nightscout_backup_bot.main.logger") as mock_logger,
            patch("nightscout_backup_bot.main.create_bot", return_value=mock_bot),
            patch("nightscout_backup_bot.main.settings") as mock_settings,
        ):
            mock_settings.enable_api_in_bot = True
            mock_settings.node_env = "development"
            mock_settings.discord_token = "test_token"

            # Mock threading.Thread to capture thread creation
            thread_calls: list[dict[str, Any]] = []

            def track_thread(*args: Any, **kwargs: Any) -> MagicMock:
                thread_calls.append(kwargs)
                mock_thread_instance = MagicMock()
                return mock_thread_instance

            with patch("nightscout_backup_bot.main.threading.Thread", side_effect=track_thread):
                # Call main in a way that we can control when bot.run exits
                # We'll use a side_effect to stop the infinite loop
                mock_bot.run.side_effect = SystemExit(0)

                with pytest.raises(SystemExit):
                    main()

            # Verify setup_logging was called
            mock_setup_logging.assert_called_once()

            # Verify logger.info was called for startup
            assert mock_logger.info.call_count >= 1
            startup_call = mock_logger.info.call_args_list[0]
            assert "Starting NightScout Backup Bot" in str(startup_call)

            # Verify API thread was created and started
            assert len(thread_calls) == 1
            assert thread_calls[0]["daemon"] is True
            assert thread_calls[0]["target"] == _run_api_server

            # Verify bot was created and run
            mock_bot.run.assert_called_once_with("test_token")

    def test_main_success_with_api_disabled(self) -> None:
        """Test main function runs successfully with API disabled."""
        mock_bot = MagicMock()
        mock_bot.run = MagicMock(side_effect=SystemExit(0))

        with (
            patch("nightscout_backup_bot.main.setup_logging") as mock_setup_logging,
            patch("nightscout_backup_bot.main.logger") as mock_logger,
            patch("nightscout_backup_bot.main.create_bot", return_value=mock_bot),
            patch("nightscout_backup_bot.main.settings") as mock_settings,
        ):
            mock_settings.enable_api_in_bot = False
            mock_settings.node_env = "development"
            mock_settings.discord_token = "test_token"

            with pytest.raises(SystemExit):
                main()

            # Verify setup_logging was called
            mock_setup_logging.assert_called_once()

            # Verify logger.info was called for startup
            assert mock_logger.info.call_count >= 1

            # Verify bot was created and run
            mock_bot.run.assert_called_once_with("test_token")

    def test_main_keyboard_interrupt(self) -> None:
        """Test main function handles KeyboardInterrupt gracefully."""
        mock_bot = MagicMock()
        mock_bot.run = MagicMock(side_effect=KeyboardInterrupt())

        with (
            patch("nightscout_backup_bot.main.setup_logging"),
            patch("nightscout_backup_bot.main.logger") as mock_logger,
            patch("nightscout_backup_bot.main.create_bot", return_value=mock_bot),
            patch("nightscout_backup_bot.main.settings") as mock_settings,
        ):
            mock_settings.enable_api_in_bot = False
            mock_settings.node_env = "development"
            mock_settings.discord_token = "test_token"

            with pytest.raises(SystemExit) as exc_info:
                main()

            # Verify exit code is 0
            assert exc_info.value.code == 0

            # Verify shutdown message was logged
            mock_logger.info.assert_any_call("Bot shutdown requested by user")

    def test_main_fatal_error(self) -> None:
        """Test main function handles fatal errors gracefully."""
        mock_bot = MagicMock()
        mock_bot.run = MagicMock(side_effect=Exception("Fatal error"))

        with (
            patch("nightscout_backup_bot.main.setup_logging"),
            patch("nightscout_backup_bot.main.logger") as mock_logger,
            patch("nightscout_backup_bot.main.create_bot", return_value=mock_bot),
            patch("nightscout_backup_bot.main.settings") as mock_settings,
        ):
            mock_settings.enable_api_in_bot = False
            mock_settings.node_env = "development"
            mock_settings.discord_token = "test_token"

            with pytest.raises(SystemExit) as exc_info:
                main()

            # Verify exit code is 1
            assert exc_info.value.code == 1

            # Verify error was logged
            mock_logger.critical.assert_called_once()
            critical_call = mock_logger.critical.call_args
            assert "Fatal error during bot startup" in str(critical_call)
            assert "error" in critical_call.kwargs

    def test_main_bot_creation_error(self) -> None:
        """Test main function handles bot creation errors."""
        with (
            patch("nightscout_backup_bot.main.setup_logging"),
            patch("nightscout_backup_bot.main.logger") as mock_logger,
            patch("nightscout_backup_bot.main.create_bot", side_effect=Exception("Bot creation failed")),
            patch("nightscout_backup_bot.main.settings") as mock_settings,
        ):
            mock_settings.enable_api_in_bot = False
            mock_settings.node_env = "development"
            mock_settings.discord_token = "test_token"

            with pytest.raises(SystemExit) as exc_info:
                main()

            # Verify exit code is 1
            assert exc_info.value.code == 1

            # Verify error was logged
            mock_logger.critical.assert_called_once()

    def test_main_api_thread_started(self) -> None:
        """Test that API thread is properly started when enabled."""
        mock_bot = MagicMock()
        mock_bot.run = MagicMock(side_effect=SystemExit(0))

        # Track thread creation
        thread_targets: list[Any] = []
        thread_instances: list[MagicMock] = []

        def track_thread(*args: Any, **kwargs: Any) -> MagicMock:
            thread_targets.append(kwargs.get("target"))
            mock_thread = MagicMock()
            thread_instances.append(mock_thread)
            return mock_thread

        with (
            patch("nightscout_backup_bot.main.setup_logging"),
            patch("nightscout_backup_bot.main.logger") as mock_logger,
            patch("nightscout_backup_bot.main.create_bot", return_value=mock_bot),
            patch("nightscout_backup_bot.main.settings") as mock_settings,
            patch("nightscout_backup_bot.main.threading.Thread", side_effect=track_thread),
        ):
            mock_settings.enable_api_in_bot = True
            mock_settings.node_env = "development"
            mock_settings.discord_token = "test_token"

            with pytest.raises(SystemExit):
                main()

            # Verify API thread was created with correct target
            assert len(thread_targets) == 1
            assert thread_targets[0] == _run_api_server

            # Verify thread was started
            assert len(thread_instances) == 1
            thread_instances[0].start.assert_called_once()

            # Verify API server started message was logged
            api_started_calls = [call for call in mock_logger.info.call_args_list if "API server started" in str(call)]
            assert len(api_started_calls) > 0
