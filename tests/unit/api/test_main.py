"""Tests for API main entry point."""

from unittest.mock import MagicMock, patch

from nightscout_backup_bot.api.main import main


class TestMain:
    """Test main function."""

    def test_main_success(self) -> None:
        """Test main function runs successfully."""
        mock_app = MagicMock()
        mock_uvicorn = MagicMock()
        mock_uvicorn.run = MagicMock()

        with (
            patch("nightscout_backup_bot.api.main.setup_logging") as mock_setup_logging,
            patch("nightscout_backup_bot.api.main.logger") as mock_logger,
            patch("nightscout_backup_bot.api.main.app", mock_app),
            patch("nightscout_backup_bot.api.main.uvicorn", mock_uvicorn),
            patch("nightscout_backup_bot.api.main.settings") as mock_settings,
        ):
            mock_settings.node_env = "development"

            main()

            # Verify setup_logging was called
            mock_setup_logging.assert_called_once()

            # Verify logger.info was called with correct parameters
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert "Starting NightScout Backup API server" in call_args[0][0]
            assert call_args[1]["host"] == "0.0.0.0"
            assert call_args[1]["port"] == 8000
            assert call_args[1]["environment"] == "development"

            # Verify uvicorn.run was called with correct parameters
            mock_uvicorn.run.assert_called_once_with(
                mock_app,
                host="0.0.0.0",
                port=8000,
                log_level="info",
            )

    def test_main_with_production_environment(self) -> None:
        """Test main function with production environment."""
        mock_app = MagicMock()
        mock_uvicorn = MagicMock()
        mock_uvicorn.run = MagicMock()

        with (
            patch("nightscout_backup_bot.api.main.setup_logging") as mock_setup_logging,
            patch("nightscout_backup_bot.api.main.logger") as mock_logger,
            patch("nightscout_backup_bot.api.main.app", mock_app),
            patch("nightscout_backup_bot.api.main.uvicorn", mock_uvicorn),
            patch("nightscout_backup_bot.api.main.settings") as mock_settings,
        ):
            mock_settings.node_env = "production"

            main()

            # Verify setup_logging was called
            mock_setup_logging.assert_called_once()

            # Verify logger.info was called with production environment
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert call_args[1]["environment"] == "production"

            # Verify uvicorn.run was called
            mock_uvicorn.run.assert_called_once()

    def test_main_uvicorn_run_parameters(self) -> None:
        """Test that uvicorn.run is called with exact parameters."""
        mock_app = MagicMock()
        mock_uvicorn = MagicMock()
        mock_uvicorn.run = MagicMock()

        with (
            patch("nightscout_backup_bot.api.main.setup_logging"),
            patch("nightscout_backup_bot.api.main.logger"),
            patch("nightscout_backup_bot.api.main.app", mock_app),
            patch("nightscout_backup_bot.api.main.uvicorn", mock_uvicorn),
            patch("nightscout_backup_bot.api.main.settings") as mock_settings,
        ):
            mock_settings.node_env = "development"

            main()

            # Verify uvicorn.run was called with exact parameters
            mock_uvicorn.run.assert_called_once()
            call_kwargs = mock_uvicorn.run.call_args[1]
            assert call_kwargs["host"] == "0.0.0.0"
            assert call_kwargs["port"] == 8000
            assert call_kwargs["log_level"] == "info"
            assert mock_uvicorn.run.call_args[0][0] == mock_app

    def test_main_logging_setup_called(self) -> None:
        """Test that setup_logging is called before uvicorn.run."""
        mock_app = MagicMock()
        mock_uvicorn = MagicMock()
        mock_uvicorn.run = MagicMock()

        call_order: list[str] = []

        def track_setup_logging() -> None:
            call_order.append("setup_logging")

        def track_uvicorn_run(*args: object, **kwargs: object) -> None:
            call_order.append("uvicorn_run")

        with (
            patch("nightscout_backup_bot.api.main.setup_logging", side_effect=track_setup_logging),
            patch("nightscout_backup_bot.api.main.logger"),
            patch("nightscout_backup_bot.api.main.app", mock_app),
            patch("nightscout_backup_bot.api.main.uvicorn", mock_uvicorn),
            patch("nightscout_backup_bot.api.main.settings") as mock_settings,
        ):
            mock_settings.node_env = "development"
            mock_uvicorn.run.side_effect = track_uvicorn_run

            main()

            # Verify setup_logging is called before uvicorn.run
            assert len(call_order) == 2
            assert call_order[0] == "setup_logging"
            assert call_order[1] == "uvicorn_run"
