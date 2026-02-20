"""Markdown export command for Parxy document processing."""

from datetime import timedelta
from pathlib import Path
from typing import Optional, List, Annotated

import typer

from parxy_core.facade import Parxy

from parxy_cli.models import Level
from parxy_cli.console.console import Console
from parxy_cli.commands.parse import collect_files, format_timedelta

app = typer.Typer()

console = Console()


@app.command()
def markdown(
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
    output_dir: Annotated[
        Optional[str],
        typer.Option(
            '--output',
            '-o',
            help='Directory to save markdown files. If not specified, files are saved next to the source files.',
            dir_okay=True,
            file_okay=False,
        ),
    ] = None,
    inline: Annotated[
        bool,
        typer.Option(
            '--inline',
            '-i',
            help='Output markdown to stdout with file name as YAML frontmatter. Only valid with a single file.',
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
):
    """Parse documents to Markdown.

    Examples:

        # Parse a single file
        parxy markdown document.pdf

        # Parse with a specific driver and output to a folder
        parxy markdown document.pdf -d pymupdf -o output/

        # Parse all PDFs in a folder (non-recursive by default)
        parxy markdown /path/to/folder

        # Parse recursively with multiple drivers
        parxy markdown /path/to/folder --recursive -d pymupdf -d llamaparse

        # Output to stdout as YAML-frontmattered markdown (single file only)
        parxy markdown document.pdf --inline
    """
    console.action('Markdown export', space_after=False)

    # Collect all files
    files = collect_files(inputs, recursive=recursive, max_depth=max_depth)

    if not files:
        console.warning('No suitable files found to process.', panel=True)
        raise typer.Exit(1)

    if inline and len(files) > 1:
        console.error('--inline can only be used with a single file')
        raise typer.Exit(1)

    # Use default driver if none specified
    if not drivers:
        drivers = [Parxy.default_driver()]

    output_path = Path(output_dir) if output_dir else None

    total_tasks = len(files) * len(drivers)
    error_count = 0

    try:
        with console.shimmer(
            f'Processing {len(files)} file{"s" if len(files) > 1 else ""} with {len(drivers)} driver{"s" if len(drivers) > 1 else ""}...'
        ):
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
                        doc = result.document
                        file_path = (
                            Path(result.file)
                            if isinstance(result.file, str)
                            else Path('document')
                        )

                        content = doc.markdown()

                        if inline:
                            frontmatter = f'---\nfile: "{result.file}"\npages: {len(doc.pages)}\n---\n\n'
                            console.print(frontmatter + content)
                        else:
                            if output_path:
                                output_path.mkdir(parents=True, exist_ok=True)
                                save_dir = output_path
                            else:
                                save_dir = file_path.parent

                            base_name = file_path.stem
                            if result.driver:
                                base_name = f'{result.driver}-{base_name}'

                            out_file = save_dir / f'{base_name}.md'
                            out_file.write_text(content, encoding='utf-8')

                            console.print(
                                f'[faint]⎿ [/faint] {file_name} via {result.driver} to [success]{out_file}[/success] [faint]({len(doc.pages)} pages)[/faint]'
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

    if not inline:
        console.newline()

    if error_count == len(files) * len(drivers):
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

    if not inline:
        console.success(
            f'Processed {len(files)} file{"s" if len(files) > 1 else ""} using {len(drivers)} driver{"s" if len(drivers) > 1 else ""} (took {elapsed_time})'
        )
