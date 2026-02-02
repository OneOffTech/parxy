"""Test suite for the agents command."""

from pathlib import Path
from unittest.mock import patch

import pytest
from click.utils import strip_ansi
from typer.testing import CliRunner

from parxy_cli.commands.agents import app


@pytest.fixture
def runner():
    """Fixture providing a CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_template_content():
    """Fixture providing mock agents template content."""
    return """<parxy>
<!-- Parxy document processing instructions -->

## Parxy Document Processing

Test content for agents template.

</parxy>"""


def test_agents_command_creates_agents_file(runner, mock_template_content):
    """Test that the agents command creates AGENTS.md when it doesn't exist."""

    with (
        patch('parxy_cli.commands.agents.files') as mock_files,
        runner.isolated_filesystem(),
    ):
        mock_files.return_value.joinpath.return_value.read_text.return_value = (
            mock_template_content
        )

        result = runner.invoke(app)

        assert result.exit_code == 0

        cleaned_output = strip_ansi(result.stdout)
        assert 'Created AGENTS.md with Parxy section' in cleaned_output
        assert 'Agent configuration complete!' in cleaned_output

        agents_file = Path.cwd() / 'AGENTS.md'
        assert agents_file.exists()
        content = agents_file.read_text()
        assert '<parxy>' in content
        assert '</parxy>' in content
        assert 'Test content for agents template' in content


def test_agents_command_appends_to_existing_file_without_parxy_section(
    runner, mock_template_content
):
    """Test that the agents command appends Parxy section to existing AGENTS.md."""

    with (
        patch('parxy_cli.commands.agents.files') as mock_files,
        runner.isolated_filesystem(),
    ):
        existing_content = """# My Project

Custom project documentation.
"""
        agents_file = Path.cwd() / 'AGENTS.md'
        agents_file.write_text(existing_content)

        mock_files.return_value.joinpath.return_value.read_text.return_value = (
            mock_template_content
        )

        result = runner.invoke(app, input='y\n')

        assert result.exit_code == 0

        cleaned_output = strip_ansi(result.stdout)
        assert 'AGENTS.md exists without Parxy section' in cleaned_output
        assert 'Added Parxy section to AGENTS.md' in cleaned_output

        content = agents_file.read_text()
        assert '# My Project' in content
        assert 'Custom project documentation' in content
        assert '<parxy>' in content
        assert '</parxy>' in content


def test_agents_command_updates_existing_parxy_section(runner, mock_template_content):
    """Test that the agents command updates existing Parxy section."""

    with (
        patch('parxy_cli.commands.agents.files') as mock_files,
        runner.isolated_filesystem(),
    ):
        existing_content = """# My Project

Custom documentation.

<parxy>
Old parxy content that should be replaced.
</parxy>

More custom content.
"""
        agents_file = Path.cwd() / 'AGENTS.md'
        agents_file.write_text(existing_content)

        mock_files.return_value.joinpath.return_value.read_text.return_value = (
            mock_template_content
        )

        result = runner.invoke(app, input='y\n')

        assert result.exit_code == 0

        cleaned_output = strip_ansi(result.stdout)
        assert 'AGENTS.md already has a Parxy section' in cleaned_output
        assert 'Updated Parxy section in AGENTS.md' in cleaned_output

        content = agents_file.read_text()
        assert '# My Project' in content
        assert 'Custom documentation' in content
        assert 'More custom content' in content
        assert 'Old parxy content that should be replaced' not in content
        assert 'Test content for agents template' in content


def test_agents_command_respects_no_to_update_prompt(runner, mock_template_content):
    """Test that the agents command respects 'no' answer to update prompt."""

    with (
        patch('parxy_cli.commands.agents.files') as mock_files,
        runner.isolated_filesystem(),
    ):
        existing_content = """<parxy>
Original content.
</parxy>"""
        agents_file = Path.cwd() / 'AGENTS.md'
        agents_file.write_text(existing_content)

        mock_files.return_value.joinpath.return_value.read_text.return_value = (
            mock_template_content
        )

        result = runner.invoke(app, input='n\n')

        assert result.exit_code == 0

        cleaned_output = strip_ansi(result.stdout)
        assert 'Leaving Parxy section as is' in cleaned_output

        content = agents_file.read_text()
        assert 'Original content' in content
        assert 'Test content for agents template' not in content


def test_agents_command_respects_no_to_append_prompt(runner, mock_template_content):
    """Test that the agents command respects 'no' answer to append prompt."""

    with (
        patch('parxy_cli.commands.agents.files') as mock_files,
        runner.isolated_filesystem(),
    ):
        existing_content = '# My Project\n'
        agents_file = Path.cwd() / 'AGENTS.md'
        agents_file.write_text(existing_content)

        mock_files.return_value.joinpath.return_value.read_text.return_value = (
            mock_template_content
        )

        result = runner.invoke(app, input='n\n')

        assert result.exit_code == 0

        cleaned_output = strip_ansi(result.stdout)
        assert 'Leaving AGENTS.md as is' in cleaned_output

        content = agents_file.read_text()
        assert content == existing_content


def test_agents_command_force_flag_skips_prompts(runner, mock_template_content):
    """Test that the --overwrite flag skips confirmation prompts."""

    with (
        patch('parxy_cli.commands.agents.files') as mock_files,
        runner.isolated_filesystem(),
    ):
        existing_content = """<parxy>
Old content.
</parxy>"""
        agents_file = Path.cwd() / 'AGENTS.md'
        agents_file.write_text(existing_content)

        mock_files.return_value.joinpath.return_value.read_text.return_value = (
            mock_template_content
        )

        result = runner.invoke(app, ['--overwrite'])

        assert result.exit_code == 0

        cleaned_output = strip_ansi(result.stdout)
        assert 'Updated Parxy section in AGENTS.md' in cleaned_output

        content = agents_file.read_text()
        assert 'Old content' not in content
        assert 'Test content for agents template' in content


def test_agents_command_output_option(runner, mock_template_content):
    """Test that the --output option creates files in specified directory."""

    with (
        patch('parxy_cli.commands.agents.files') as mock_files,
        runner.isolated_filesystem(),
    ):
        output_dir = Path.cwd() / 'subdir'
        output_dir.mkdir()

        mock_files.return_value.joinpath.return_value.read_text.return_value = (
            mock_template_content
        )

        result = runner.invoke(app, ['--output', str(output_dir)])

        assert result.exit_code == 0

        agents_file = output_dir / 'AGENTS.md'
        assert agents_file.exists()

        root_agents_file = Path.cwd() / 'AGENTS.md'
        assert not root_agents_file.exists()
