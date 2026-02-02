"""Command to set up AI agent configuration files for Parxy projects."""

import re
from importlib.resources import files
from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

from parxy_cli.console.console import Console

app = typer.Typer()

console = Console()

# Tags used to identify Parxy section in AGENTS.md
PARXY_START_TAG = '<parxy>'
PARXY_END_TAG = '</parxy>'

NEW_AGENTS_MD_TEMPLATE = """# AI Agent Guide

Welcome, AI Assistant! This guide provides context for working with this project.

{parxy_section}
"""


def _get_parxy_section_template() -> str:
    """Load the Parxy section template for AGENTS.md."""
    return files('parxy_cli').joinpath('agents.template.md').read_text()


def _has_parxy_section(content: str) -> bool:
    """Check if content already has a Parxy section."""
    return PARXY_START_TAG in content and PARXY_END_TAG in content


def _update_parxy_section(content: str, parxy_section: str) -> str:
    """Replace existing Parxy section with new content."""
    pattern = re.compile(
        rf'{re.escape(PARXY_START_TAG)}.*?{re.escape(PARXY_END_TAG)}',
        re.DOTALL,
    )
    return pattern.sub(parxy_section, content)


def _append_parxy_section(content: str, parxy_section: str) -> str:
    """Append Parxy section to existing content."""
    # Ensure there's proper spacing
    if not content.endswith('\n'):
        content += '\n'
    if not content.endswith('\n\n'):
        content += '\n'
    return content + parxy_section


@app.command()
def agents(
    output_dir: Annotated[
        Optional[Path],
        typer.Option(
            '--output',
            '-o',
            help='Output directory for agent files. Defaults to current directory.',
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            '--overwrite',
            '-f',
            help='Overwrite existing Parxy section without prompting.',
        ),
    ] = False,
):
    """Set up AI agent configuration files for Parxy projects.

    Creates or updates an AGENTS.md file with Parxy usage documentation.
    If AGENTS.md exists, the Parxy section (marked with <parxy> tags) is
    added or updated while preserving other content.

    Optionally creates Claude Code skill files for common operations.
    """
    output_path = output_dir or Path.cwd()

    console.print('[bold]Setting up Parxy agent configuration[/bold]')
    console.newline()

    # Handle AGENTS.md
    agents_file = output_path / 'AGENTS.md'

    if agents_file.exists():
        existing_content = agents_file.read_text(encoding='utf-8')

        if _has_parxy_section(existing_content):
            # Update existing Parxy section
            console.print('[yellow]AGENTS.md already has a Parxy section[/yellow]')

            if not force:
                update = typer.confirm(
                    'Do you want to update the Parxy section?', default=True
                )
                if not update:
                    console.print('[dim]Leaving Parxy section as is.[/dim]')
                else:
                    new_content = _update_parxy_section(
                        existing_content, _get_parxy_section_template()
                    )
                    agents_file.write_text(new_content, encoding='utf-8')
                    console.print('[green]Updated[/green] Parxy section in AGENTS.md')
            else:
                new_content = _update_parxy_section(
                    existing_content, _get_parxy_section_template()
                )
                agents_file.write_text(new_content, encoding='utf-8')
                console.print('[green]Updated[/green] Parxy section in AGENTS.md')
        else:
            # Append Parxy section to existing file
            console.print('[yellow]AGENTS.md exists without Parxy section[/yellow]')

            if not force:
                append = typer.confirm(
                    'Do you want to add the Parxy section?', default=True
                )
                if not append:
                    console.print('[dim]Leaving AGENTS.md as is.[/dim]')
                else:
                    new_content = _append_parxy_section(
                        existing_content, _get_parxy_section_template()
                    )
                    agents_file.write_text(new_content, encoding='utf-8')
                    console.print('[green]Added[/green] Parxy section to AGENTS.md')
            else:
                new_content = _append_parxy_section(
                    existing_content, _get_parxy_section_template()
                )
                agents_file.write_text(new_content, encoding='utf-8')
                console.print('[green]Added[/green] Parxy section to AGENTS.md')
    else:
        # Create new AGENTS.md with Parxy section
        new_content = NEW_AGENTS_MD_TEMPLATE.format(
            parxy_section=_get_parxy_section_template()
        )
        agents_file.write_text(new_content, encoding='utf-8')
        console.print('[green]Created[/green] AGENTS.md with Parxy section')

    console.newline()
    console.print('[green]Agent configuration complete![/green]')
    console.newline()
    console.print(
        'Your project is now configured for AI assistants. '
        'The AGENTS.md file provides context about Parxy usage.'
    )
    console.newline()
    console.print(
        '[dim]Tip: Run `parxy agents` again to update the Parxy section '
        'when new features are available.[/dim]'
    )
