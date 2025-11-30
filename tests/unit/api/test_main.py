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

    def test_main_with_sentry_enabled(self) -> None:
        """Test main function initializes Sentry when DSN is configured."""
        mock_app = MagicMock()
        mock_uvicorn = MagicMock()
        mock_uvicorn.run = MagicMock()
        mock_sentry_sdk = MagicMock()
        mock_fastapi_integration = MagicMock()
        mock_uvicorn_integration = MagicMock()

        with (
            patch("nightscout_backup_bot.api.main.setup_logging"),
            patch("nightscout_backup_bot.api.main.logger") as mock_logger,
            patch("nightscout_backup_bot.api.main.app", mock_app),
            patch("nightscout_backup_bot.api.main.uvicorn", mock_uvicorn),
            patch("nightscout_backup_bot.api.main.settings") as mock_settings,
            patch.dict(
                "sys.modules",
                {
                    "sentry_sdk": mock_sentry_sdk,
                    "sentry_sdk.integrations.fastapi": MagicMock(FastApiIntegration=mock_fastapi_integration),
                    "sentry_sdk.integrations.uvicorn": MagicMock(UvicornIntegration=mock_uvicorn_integration),
                },
            ),
        ):
            mock_settings.sentry_dsn = "https://test@sentry.io/123"
            mock_settings.node_env = "development"
            mock_settings.is_production = False

            main()

            # Verify Sentry was initialized
            mock_sentry_sdk.init.assert_called_once()
            init_call = mock_sentry_sdk.init.call_args
            assert init_call[1]["dsn"] == "https://test@sentry.io/123"
            assert init_call[1]["environment"] == "development"
            assert init_call[1]["traces_sample_rate"] == 1.0

            # Verify Sentry initialized message was logged
            sentry_calls = [call for call in mock_logger.info.call_args_list if "Sentry initialized" in str(call)]
            assert len(sentry_calls) > 0

    def test_main_with_sentry_disabled(self) -> None:
        """Test main function skips Sentry when DSN is None."""
        mock_app = MagicMock()
        mock_uvicorn = MagicMock()
        mock_uvicorn.run = MagicMock()
        mock_sentry_sdk = MagicMock()

        with (
            patch("nightscout_backup_bot.api.main.setup_logging"),
            patch("nightscout_backup_bot.api.main.logger"),
            patch("nightscout_backup_bot.api.main.app", mock_app),
            patch("nightscout_backup_bot.api.main.uvicorn", mock_uvicorn),
            patch("nightscout_backup_bot.api.main.settings") as mock_settings,
            patch.dict("sys.modules", {"sentry_sdk": mock_sentry_sdk}),
        ):
            mock_settings.sentry_dsn = None
            mock_settings.node_env = "development"

            main()

            # Verify Sentry was not initialized
            mock_sentry_sdk.init.assert_not_called()

    def test_main_with_sentry_production_trace_rate(self) -> None:
        """Test main function uses lower trace sample rate in production."""
        mock_app = MagicMock()
        mock_uvicorn = MagicMock()
        mock_uvicorn.run = MagicMock()
        mock_sentry_sdk = MagicMock()
        mock_fastapi_integration = MagicMock()
        mock_uvicorn_integration = MagicMock()

        with (
            patch("nightscout_backup_bot.api.main.setup_logging"),
            patch("nightscout_backup_bot.api.main.logger"),
            patch("nightscout_backup_bot.api.main.app", mock_app),
            patch("nightscout_backup_bot.api.main.uvicorn", mock_uvicorn),
            patch("nightscout_backup_bot.api.main.settings") as mock_settings,
            patch.dict(
                "sys.modules",
                {
                    "sentry_sdk": mock_sentry_sdk,
                    "sentry_sdk.integrations.fastapi": MagicMock(FastApiIntegration=mock_fastapi_integration),
                    "sentry_sdk.integrations.uvicorn": MagicMock(UvicornIntegration=mock_uvicorn_integration),
                },
            ),
        ):
            mock_settings.sentry_dsn = "https://test@sentry.io/123"
            mock_settings.node_env = "production"
            mock_settings.is_production = True

            main()

            # Verify Sentry was initialized with production trace rate
            mock_sentry_sdk.init.assert_called_once()
            init_call = mock_sentry_sdk.init.call_args
            assert init_call[1]["traces_sample_rate"] == 0.1

    def test_main_with_sentry_initialization_error(self) -> None:
        """Test main function handles Sentry initialization errors gracefully."""
        mock_app = MagicMock()
        mock_uvicorn = MagicMock()
        mock_uvicorn.run = MagicMock()
        mock_sentry_sdk = MagicMock()
        mock_sentry_sdk.init.side_effect = Exception("Sentry init failed")

        with (
            patch("nightscout_backup_bot.api.main.setup_logging"),
            patch("nightscout_backup_bot.api.main.logger") as mock_logger,
            patch("nightscout_backup_bot.api.main.app", mock_app),
            patch("nightscout_backup_bot.api.main.uvicorn", mock_uvicorn),
            patch("nightscout_backup_bot.api.main.settings") as mock_settings,
            patch.dict("sys.modules", {"sentry_sdk": mock_sentry_sdk}),
        ):
            mock_settings.sentry_dsn = "https://test@sentry.io/123"
            mock_settings.node_env = "development"

            main()

            # Verify warning was logged
            warning_calls = [
                call for call in mock_logger.warning.call_args_list if "Failed to initialize Sentry" in str(call)
            ]
            assert len(warning_calls) > 0

            # Verify uvicorn still ran despite Sentry error
            mock_uvicorn.run.assert_called_once()
