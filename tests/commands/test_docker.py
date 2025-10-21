"""Test suite for the docker command."""

from unittest.mock import patch
from pathlib import Path
import pytest
from typer.testing import CliRunner
from click.utils import strip_ansi

from parxy_cli.commands.docker import app


@pytest.fixture
def runner():
    """Fixture providing a CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_compose_content():
    """Fixture providing mock docker-compose file content."""
    return """version: '3'
services:
  pdfact:
    image: oneofftech/pdfact:latest
"""


def test_docker_command_creates_compose_file(runner, mock_compose_content):
    """Test that the docker command creates a compose.yaml file when it doesn't exist."""

    with patch('importlib.resources.files') as mock_files, runner.isolated_filesystem():
        # Setup mock to return our example content
        mock_files.return_value.joinpath.return_value.read_text.return_value = (
            mock_compose_content
        )

        # Run the command
        result = runner.invoke(app)

        # Assert command executed successfully
        assert result.exit_code == 0

        # Clean ANSI codes and verify success message
        cleaned_output = strip_ansi(result.stdout)
        assert 'Created compose.yaml file with default configuration' in cleaned_output
        assert 'Execute docker compose pull' in cleaned_output

        # Verify file was created with correct content
        compose_file = Path.cwd() / 'compose.yaml'
        assert compose_file.exists()
        assert compose_file.read_text() == mock_compose_content

        # Verify file was created with correct content
        otel_file = Path.cwd() / 'otel-collector-config.yaml'
        assert otel_file.exists()


def test_docker_command_asks_for_confirmation_when_compose_exists(
    runner, mock_compose_content
):
    """Test that the docker command asks for confirmation when compose.yaml already exists."""

    with patch('importlib.resources.files') as mock_files, runner.isolated_filesystem():
        # Create existing compose.yaml file
        compose_file = Path.cwd() / 'compose.yaml'
        compose_file.write_text("version: '3'\nservices: {}")

        mock_files.return_value.joinpath.return_value.read_text.return_value = (
            mock_compose_content
        )

        # Run command and simulate "no" to overwrite prompt
        result = runner.invoke(app, input='n\n')

        # Clean ANSI codes and verify warning and abort messages
        cleaned_output = strip_ansi(result.stdout)
        assert 'compose.yaml file already exists' in cleaned_output
        assert 'Leaving compose.yaml as is' in cleaned_output

        # Verify original file was not modified
        assert compose_file.read_text() == "version: '3'\nservices: {}"

        # Run command again and simulate "yes" to overwrite prompt
        result = runner.invoke(app, input='y\n')

        # Verify file was overwritten with new content
        assert compose_file.read_text() == mock_compose_content


def test_docker_command_handles_errors(runner):
    """Test that the docker command properly handles and displays errors."""

    with patch('importlib.resources.files') as mock_files:
        # Setup mock to raise an exception
        mock_files.return_value.joinpath.return_value.read_text.side_effect = Exception(
            'Test error'
        )

        # Run the command
        result = runner.invoke(app)

        # Command should exit with non-zero status
        assert result.exit_code == 1

        # Clean ANSI codes and verify error message
        cleaned_output = strip_ansi(result.stdout)
        assert 'Error creating compose.yaml file' in cleaned_output
        assert 'Test error' in cleaned_output
