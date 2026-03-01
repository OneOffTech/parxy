"""Command line interface for Parxy document processing."""

import json
import os
import tomllib
from datetime import timedelta
from pathlib import Path
from typing import Optional, List, Annotated, Dict

import typer

from parxy_core.facade import Parxy
from parxy_core.models import Document, BatchResult

from parxy_cli.models import Level, OutputMode
from parxy_cli.console.console import Console

app = typer.Typer()

console = Console()


DEFAULT_MIDDLEWARE_PROFILES: Dict[str, List[str]] = {
    'default': [],
}


def _load_middleware_profiles(config_path: Optional[Path]) -> Dict[str, List[str]]:
    """Load middleware profiles from optional config file.

    Supports JSON, TOML, YAML and YML. The expected structure is either:
    - ``{"middleware_profiles": {"profile": ["path.to.Middleware"]}}``
    - ``{"profiles": {"profile": ["path.to.Middleware"]}}``
    """
    profiles = dict(DEFAULT_MIDDLEWARE_PROFILES)
    if config_path is None:
        return profiles

    if not config_path.exists():
        raise typer.BadParameter(f'Middleware config file not found: {config_path}')

    suffix = config_path.suffix.lower()
    raw_data = None

    if suffix in {'.json'}:
        raw_data = json.loads(config_path.read_text(encoding='utf-8'))
    elif suffix in {'.toml'}:
        raw_data = tomllib.loads(config_path.read_text(encoding='utf-8'))
    elif suffix in {'.yaml', '.yml'}:
        try:
            import yaml
        except ImportError as exc:
            raise typer.BadParameter(
                'YAML config requires PyYAML. Install pyyaml or use JSON/TOML config.'
            ) from exc
        raw_data = yaml.safe_load(config_path.read_text(encoding='utf-8'))
    else:
        raise typer.BadParameter(
            'Unsupported middleware config format. Use .json, .toml, .yaml or .yml'
        )

    if not isinstance(raw_data, dict):
        raise typer.BadParameter(
            'Middleware config must be an object/map at top level.'
        )

    custom_profiles = raw_data.get('middleware_profiles') or raw_data.get('profiles')
    if custom_profiles is None:
        return profiles

    if not isinstance(custom_profiles, dict):
        raise typer.BadParameter(
            'middleware_profiles must be a map of profile names to middleware paths.'
        )

    for name, middleware_list in custom_profiles.items():
        if not isinstance(name, str) or not isinstance(middleware_list, list):
            raise typer.BadParameter(
                'Each profile must map to a list of middleware class paths.'
            )
        if not all(isinstance(item, str) for item in middleware_list):
            raise typer.BadParameter('Middleware class paths must be strings.')
        profiles[name] = middleware_list

    return profiles


def configure_middleware_profile(
    profile: Optional[str],
    config_path: Optional[Path],
) -> None:
    """Configure global middleware registry from a selected profile."""
    selected_profile = profile or os.getenv('PARXY_MIDDLEWARE_PROFILE')
    if not selected_profile:
        return

    env_config_path = os.getenv('PARXY_MIDDLEWARE_CONFIG')
    effective_config = config_path or (
        Path(env_config_path) if env_config_path else None
    )
    profiles = _load_middleware_profiles(effective_config)

    if selected_profile not in profiles:
        available = ', '.join(sorted(profiles.keys()))
        raise typer.BadParameter(
            f'Unknown middleware profile: {selected_profile}. Available profiles: {available}'
        )

    middleware_paths = profiles[selected_profile]
    Parxy.clear_middleware()
    if middleware_paths:
        Parxy.with_middleware(middleware_paths)

    console.info(
        f"Using middleware profile '{selected_profile}' ({len(middleware_paths)} middleware)."
    )


def collect_files_with_depth(
    directory: Path, pattern: str, max_depth: int, current_depth: int = 0
) -> List[Path]:
    """
    Recursively collect files matching pattern up to max_depth.

    Args:
        directory: Directory to search in
        pattern: File pattern to match (e.g., '*.pdf')
        max_depth: Maximum depth to recurse (0 = no recursion)
        current_depth: Current recursion depth (used internally)

    Returns:
        List of Path objects matching the pattern
    """
    files = []

    # Collect files in current directory
    files.extend(directory.glob(pattern))

    # Recurse into subdirectories if we haven't reached max depth
    if current_depth < max_depth:
        for subdir in directory.iterdir():
            if subdir.is_dir():
                files.extend(
                    collect_files_with_depth(
                        subdir, pattern, max_depth, current_depth + 1
                    )
                )

    return files


def collect_files(
    inputs: List[str], recursive: bool = False, max_depth: Optional[int] = None
) -> List[Path]:
    """
    Collect all files from the input list (files and/or folders).

    Args:
        inputs: List of file paths and/or folder paths
        recursive: Whether to search subdirectories
        max_depth: Maximum depth to recurse (only applies if recursive=True, None=unlimited)

    Returns:
        List of Path objects for all PDF files found
    """
    files = []

    for input_path in inputs:
        path = Path(input_path)

        if path.is_file():
            files.append(path)
        elif path.is_dir():
            if recursive:
                if max_depth is not None:
                    # Use depth-limited recursion
                    files.extend(collect_files_with_depth(path, '*.pdf', max_depth))
                else:
                    # Use unlimited recursion
                    files.extend(path.rglob('*.pdf'))
            else:
                # Non-recursive: only files in the given directory
                files.extend(path.glob('*.pdf'))
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


def save_batch_result(
    result: BatchResult,
    mode: OutputMode,
    output_dir: Optional[Path],
    show: bool,
    use_driver_prefix: bool = True,
) -> tuple[str, int]:
    """
    Save a BatchResult to file.

    Args:
        result: BatchResult containing the parsed document
        mode: Output mode
        output_dir: Optional output directory
        show: Whether to show content in console
        use_driver_prefix: Whether to prepend driver name to output filename

    Returns:
        Tuple of (output_path, page_count)
    """
    doc = result.document
    file_path = Path(result.file) if isinstance(result.file, str) else Path('document')

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
    if use_driver_prefix and result.driver:
        base_name = f'{result.driver}-{base_name}'

    extension = get_output_extension(mode)
    output_path = output_dir / f'{base_name}{extension}'

    # Save to file
    output_path.write_text(content, encoding='utf-8')

    # Show in console if requested
    if show:
        console.print(content)
        console.newline()

    return str(output_path), len(doc.pages)


@app.command()
def parse(
    inputs: Annotated[
        List[str],
        typer.Argument(
            help='One or more files or folders to parse. Use --recursive to search subdirectories.',
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
    ] = Level.BLOCK,
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
    recursive: Annotated[
        bool,
        typer.Option(
            '--recursive',
            '-r',
            help='Recursively search subdirectories when processing folders',
        ),
    ] = False,
    max_depth: Annotated[
        Optional[int],
        typer.Option(
            '--max-depth',
            help='Maximum depth to recurse into subdirectories (only applies with --recursive). 0 = current directory only, 1 = one level down, etc.',
            min=0,
        ),
    ] = None,
    stop_on_failure: Annotated[
        bool,
        typer.Option(
            '--stop-on-failure',
            help='Stop processing files immediately if an error occurs with any file',
        ),
    ] = False,
    workers: Annotated[
        int,
        typer.Option(
            '--workers',
            '-w',
            help='Number of parallel workers to use. Defaults to cpu count.',
            min=1,
        ),
    ] = None,
    middleware_profile: Annotated[
        Optional[str],
        typer.Option(
            '--middleware-profile',
            envvar='PARXY_MIDDLEWARE_PROFILE',
            help='Middleware profile name to activate. Built-in: default. Additional profiles can be loaded via --middleware-config.',
        ),
    ] = None,
    middleware_config: Annotated[
        Optional[str],
        typer.Option(
            '--middleware-config',
            envvar='PARXY_MIDDLEWARE_CONFIG',
            help='Path to a .json/.toml/.yaml config file defining custom middleware profiles.',
        ),
    ] = None,
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

        # Parse all PDFs in a folder (non-recursive by default)
        parxy parse /path/to/folder

        # Parse all PDFs in a folder and subdirectories (recursive)
        parxy parse /path/to/folder --recursive

        # Parse with limited recursion depth (max 2 levels deep)
        parxy parse /path/to/folder --recursive --max-depth 2

        # Use multiple drivers
        parxy parse document.pdf -d pymupdf -d llamaparse

        # Output as JSON and show in console
        parxy parse document.pdf -m json --show

        # Process files with 4 workers
        parxy parse /path/to/folder --workers 4
    """
    console.action('Parse files', space_after=False)
    # Collect all files
    files = collect_files(inputs, recursive=recursive, max_depth=max_depth)

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


    configure_middleware_profile(
        profile=middleware_profile,
        config_path=Path(middleware_config) if middleware_config else None,
    )

    error_count = 0

    # Show info
    try:
        with console.shimmer(
            f'Processing {len(files)} file{"s" if len(files) > 1 else ""} with {len(drivers)} driver{"s" if len(drivers) > 1 else ""}...'
        ):
            # Process files with progress bar
            with console.progress('Processing documents') as progress:
                task = progress.add_task('', total=total_tasks)

                batch_tasks = [str(f) for f in files]

                for result in Parxy.batch_iter(
                    tasks=batch_tasks,
                    drivers=drivers,
                    level=level.value,
                    workers=workers,
                ):
                    file_name = (
                        Path(result.file).name
                        if isinstance(result.file, str)
                        else 'document'
                    )

                    if result.success:
                        output_file, page_count = save_batch_result(
                            result=result,
                            mode=mode,
                            output_dir=output_path,
                            show=show,
                        )
                        console.print(
                            f'[faint]⎿ [/faint] {file_name} via {result.driver} to [success]{output_file}[/success] [faint]({page_count} pages)[/faint]'
                        )
                    else:
                        console.print(
                            f'[faint]⎿ [/faint] {file_name} via {result.driver} error. [error]{result.error}[/error]'
                        )
                        error_count += 1

                        if stop_on_failure:
                            console.newline()
                            console.info(
                                'Stopping due to error (--stop-on-failure flag is set)'
                            )
                            raise typer.Exit(1)

                    progress.update(task, advance=1)

                elapsed_time = format_timedelta(
                    timedelta(seconds=max(0, progress.tasks[0].elapsed))
                )
    except KeyboardInterrupt:
        console.newline()
        console.warning('Interrupted by user')
        raise typer.Exit(130)

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
