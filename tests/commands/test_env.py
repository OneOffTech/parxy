"""Test suite for the env command."""

from unittest.mock import patch, MagicMock
import pytest
from pathlib import Path
from typer.testing import CliRunner
from click.utils import strip_ansi

from parxy_cli.commands.env import app


@pytest.fixture
def runner():
    """Fixture providing a CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_env_content():
    """Fixture providing mock env file content."""
    return """PARXY_DEFAULT_DRIVER=pymupdf
PARXY_LOGGING_LEVEL=INFO
"""


@pytest.fixture
def mock_resources():
    """Fixture providing a mock for importlib.resources."""
    with patch('importlib.resources.files') as mock_files:
        mock_path = MagicMock()
        mock_path.read_text.return_value = None
        mock_files.return_value.joinpath.return_value = mock_path
        yield mock_files


def test_env_command_creates_env_file(runner, mock_env_content, mock_resources):
    """Test that the env command creates a .env file when it doesn't exist."""

    with runner.isolated_filesystem():
        mock_resources.return_value.joinpath.return_value.read_text.return_value = (
            mock_env_content
        )

        result = runner.invoke(app)

        assert result.exit_code == 0

        cleaned_output = strip_ansi(result.stdout)

        assert 'Created .env file' in cleaned_output
        assert 'with default configuration' in cleaned_output

        env_file: Path = Path.cwd() / '.env'
        assert env_file.exists()
        assert env_file.read_text() == mock_env_content


def test_env_command_asks_for_confirmation_when_env_exists(
    runner, mock_env_content, mock_resources
):
    """Test that the env command asks for confirmation when .env already exists."""

    with runner.isolated_filesystem():
        # Create existing .env file
        env_file: Path = Path.cwd() / '.env'
        env_file.write_text('EXISTING=true')

        # Setup mock for both command invocations
        mock_resources.return_value.joinpath.return_value.read_text.return_value = (
            mock_env_content
        )

        # Run command and simulate "no" to overwrite prompt
        result = runner.invoke(app, input='n\n')

        # Clean ANSI codes and verify warning and abort messages
        cleaned_output = strip_ansi(result.stdout)
        assert '.env file already exists' in cleaned_output
        assert 'Do you want to overwrite it?' in cleaned_output
        assert 'Leaving your file as is' in cleaned_output

        # Verify original file was not modified
        assert env_file.read_text() == 'EXISTING=true'

        # Run command again and simulate "yes" to overwrite prompt
        result = runner.invoke(app, input='y\n')

        # Verify file was overwritten with new content
        assert env_file.read_text() == mock_env_content


def test_env_command_handles_errors(runner, mock_resources):
    """Test that the env command properly handles and displays errors."""

    # Setup mock to raise an exception
    mock_resources.return_value.joinpath.return_value.read_text.side_effect = Exception(
        'Test error'
    )

    # Run the command
    result = runner.invoke(app)

    # Command should exit with non-zero status
    assert result.exit_code == 1

    # Clean ANSI codes and verify error message
    cleaned_output = strip_ansi(result.stdout)
    assert 'Error creating .env file' in cleaned_output
    assert 'Test error' in cleaned_output
