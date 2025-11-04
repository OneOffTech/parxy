"""Command line interface for Parxy document processing."""

from datetime import timedelta
from pathlib import Path
from typing import Optional, List, Annotated

import typer

from parxy_core.facade import Parxy
from parxy_core.models.models import Document

from parxy_cli.models import Level, OutputMode
from parxy_cli.console.console import Console

app = typer.Typer()

console = Console()


def collect_files(inputs: List[str]) -> List[Path]:
    """
    Collect all files from the input list (files and/or folders).

    Args:
        inputs: List of file paths and/or folder paths

    Returns:
        List of Path objects for all PDF files found
    """
    files = []

    for input_path in inputs:
        path = Path(input_path)

        if path.is_file():
            files.append(path)
        elif path.is_dir():
            # Recursively find all PDF files in directory
            files.extend(path.rglob('*.pdf'))
        else:
            console.warning(f'Path not found: {input_path}')

    return files


def get_output_extension(mode: OutputMode) -> str:
    """Get file extension based on output mode."""
    return {
        OutputMode.JSON: '.json',
        OutputMode.PLAIN: '.txt',
        OutputMode.MARKDOWN: '.md',
    }[mode]


def get_content(doc: Document, mode: OutputMode) -> str:
    """Extract content from document based on output mode."""
    if mode == OutputMode.JSON:
        return doc.model_dump_json(indent=2)
    elif mode == OutputMode.MARKDOWN:
        return doc.markdown()
    else:  # OutputMode.PLAIN
        return doc.text()


def process_file_with_driver(
    file_path: Path,
    driver: str,
    level: Level,
    mode: OutputMode,
    output_dir: Optional[Path],
    show: bool,
    use_driver_suffix: bool = False,
) -> tuple[str, int]:
    """
    Process a single file with a single driver.

    Args:
        file_path: Path to file to process
        driver: Driver name to use
        level: Extraction level
        mode: Output mode
        output_dir: Optional output directory
        show: Whether to show content in console
        use_driver_suffix: Whether to append driver name to output filename

    Returns:
        Tuple of (output_path, page_count)
    """
    # Parse the document
    doc = Parxy.parse(
        file=str(file_path),
        level=level.value,
        driver_name=driver,
    )

    # Get content
    content = get_content(doc, mode)

    # Determine output path
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        base_name = file_path.stem
    else:
        # Save in same directory as source file
        output_dir = file_path.parent
        base_name = file_path.stem

    # If multiple drivers, append driver name to filename
    if use_driver_suffix and driver:
        base_name = f'{base_name}-{driver}'

    extension = get_output_extension(mode)
    output_path = output_dir / f'{base_name}{extension}'

    # Save to file
    output_path.write_text(content, encoding='utf-8')

    # Show in console if requested
    if show:
        console.print(content)
        console.newline()

    return str(output_path), len(doc.pages)


def format_timedelta(td):
    days = td.days
    milliseconds = td.microseconds // 1000
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f'{days} day{"s" if days > 1 else ""}')
    if hours > 0:
        parts.append(f'{hours} hour{"s" if hours > 1 else ""}')
    if minutes > 0:
        parts.append(f'{minutes} min')
    if seconds > 0:
        parts.append(f'{seconds} sec')
    if milliseconds > 0:
        parts.append(f'{milliseconds} msec')

    return ', '.join(parts)


@app.command()
def parse(
    inputs: Annotated[
        List[str],
        typer.Argument(
            help='One or more files or folders to parse. Folders will be searched recursively for PDF files.',
        ),
    ],
    drivers: Annotated[
        Optional[List[str]],
        typer.Option(
            '--driver',
            '-d',
            help='Driver(s) to use for parsing. Can be specified multiple times. (default: pymupdf or PARXY_DEFAULT_DRIVER)',
        ),
    ] = None,
    level: Annotated[
        Level,
        typer.Option(
            '--level',
            '-l',
            help='Extraction level',
        ),
    ] = Level.PAGE,
    mode: Annotated[
        OutputMode,
        typer.Option(
            '--mode',
            '-m',
            help='Output mode: json (JSON serialization), plain (plain text), or markdown (markdown format)',
        ),
    ] = OutputMode.JSON,
    output_dir: Annotated[
        Optional[str],
        typer.Option(
            '--output',
            '-o',
            help='Directory to save output files. If not specified, files will be saved in the same directory as the source files.',
        ),
    ] = None,
    show: Annotated[
        bool,
        typer.Option(
            '--show',
            '-s',
            help='Show document content in console in addition to saving to files',
        ),
    ] = False,
):
    """
    Parse documents using one or more drivers.

    This command processes PDF documents and extracts their content in various formats.
    You can specify individual files or entire folders to process.

    Examples:

        # Parse a single file
        parxy parse document.pdf

        # Parse multiple files with specific driver
        parxy parse doc1.pdf doc2.pdf -d pymupdf

        # Parse all PDFs in a folder
        parxy parse /path/to/folder

        # Use multiple drivers
        parxy parse document.pdf -d pymupdf -d llamaparse

        # Output as JSON and show in console
        parxy parse document.pdf -m json --show
    """

    console.action('Parse files', space_after=False)

    # Collect all files
    files = collect_files(inputs)

    if not files:
        console.warning('No suitable files found to process.', panel=True)
        raise typer.Exit(1)

    # Use default driver if none specified
    if not drivers:
        drivers = [Parxy.default_driver()]  # Will use default driver

    # Convert output_dir to Path if specified
    output_path = Path(output_dir) if output_dir else None

    # Calculate total tasks
    total_tasks = len(files) * len(drivers)

    # Determine if we should use driver suffix (when multiple drivers are used)
    use_driver_suffix = len(drivers) > 1

    if use_driver_suffix:
        console.info(
            'You have specified more than one driver. Driver name will be added as suffix to the file name while saving.'
        )

    error_count = 0

    # Show info
    with console.shimmer(
        f'Processing {len(files)} file{"s" if len(files) > 1 else ""} with {len(drivers)} driver{"s" if len(drivers) > 1 else ""}...'
    ):
        # Process files with progress bar
        with console.progress('Processing documents') as progress:
            task = progress.add_task('', total=total_tasks)

            for file_path in files:
                for driver in drivers:
                    try:
                        output_file, page_count = process_file_with_driver(
                            file_path=file_path,
                            driver=driver,
                            level=level,
                            mode=mode,
                            output_dir=output_path,
                            show=show,
                            use_driver_suffix=use_driver_suffix,
                        )

                        # Update progress
                        console.print(
                            f'[faint]⎿ [/faint] {file_path.name} via {driver} to [success]{output_file}[/success] [faint]({page_count} pages)[/faint]'
                        )
                        progress.update(task, advance=1)

                    except Exception as e:
                        console.print(
                            f'[faint]⎿ [/faint] {file_path.name} via {driver} error. [error]{str(e)}[/error]'
                        )
                        progress.update(task, advance=1)
                        error_count += 1
                        continue

            elapsed_time = format_timedelta(
                timedelta(seconds=max(0, progress.tasks[0].elapsed))
            )

    console.newline()
    if error_count == len(files):
        console.error('All files were not processed due to errors')
        return

    if error_count > 0:
        console.warning(
            f'Processed {len(files)} file{"s" if len(files) > 1 else ""} with warnings using {len(drivers)} driver{"s" if len(drivers) > 1 else ""}'
        )
        console.print(
            f'[faint]⎿ [/faint] [highlight]{error_count} files errored[/highlight]'
        )
        return

    console.success(
        f'Processed {len(files)} file{"s" if len(files) > 1 else ""} using {len(drivers)} driver{"s" if len(drivers) > 1 else ""} (took {elapsed_time})'
    )
