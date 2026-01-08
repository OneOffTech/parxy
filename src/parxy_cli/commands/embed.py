"""PDF embedded file commands."""

from pathlib import Path
from typing import List, Annotated, Optional
import sys

import typer
import pymupdf

from parxy_cli.console.console import Console

app = typer.Typer()
console = Console()


# ============================================================================
# Helper Functions
# ============================================================================


def format_file_size(size_bytes: int) -> str:
    """
    Convert bytes to human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string like "1.5 MB"
    """
    size = float(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f'{size:.1f} {unit}'
        size /= 1024.0
    return f'{size:.1f} TB'


def validate_pdf_file(file_path: str) -> Path:
    """
    Validate PDF file exists and has .pdf extension.

    Args:
        file_path: Path to PDF file

    Returns:
        Path object

    Raises:
        FileNotFoundError: if file not found
        ValueError: if file is not a PDF
    """
    path = Path(file_path)
    if not path.is_file():
        console.error(f'Input file not found: {file_path}', panel=True)
        raise FileNotFoundError(f'Input file not found: {file_path}')
    if path.suffix.lower() != '.pdf':
        console.error(f'Input file must be a PDF: {file_path}', panel=True)
        raise ValueError(f'Input file must be a PDF: {file_path}')
    return path


def is_binary_file(content: bytes) -> bool:
    """
    Detect if content is binary by checking for null bytes.

    Checks first 8KB of content for null bytes which typically
    indicate binary data.

    Args:
        content: File content as bytes

    Returns:
        True if binary, False if likely text
    """
    check_bytes = content[:8192]
    return b'\x00' in check_bytes


def prompt_overwrite(file_path: Path) -> bool:
    """
    Prompt user to confirm overwriting existing file.

    Args:
        file_path: Path to file that would be overwritten

    Returns:
        True if user confirms, False otherwise
    """
    console.newline()
    return typer.confirm(
        f"Output file '{file_path.name}' already exists. Overwrite?",
        default=False,
    )


# ============================================================================
# Commands
# ============================================================================


@app.command(name='embed:list', help='List embedded files in a PDF')
def list_embeds(
    input_file: Annotated[
        str,
        typer.Argument(help='PDF file to inspect'),
    ],
    verbose: Annotated[
        bool,
        typer.Option('--verbose', '-v', help='Show detailed information'),
    ] = False,
):
    """
    List all embedded files in a PDF.

    Displays a list of all files embedded in the specified PDF document.
    In verbose mode, shows additional metadata including file size,
    description, and modification date.

    Examples:

        # List embeds
        parxy embed:list document.pdf

        # List with detailed information
        parxy embed:list document.pdf --verbose
        parxy embed:list document.pdf -v
    """
    console.action('List embedded files', space_after=False)

    try:
        # Validate input file
        input_path = validate_pdf_file(input_file)

        # Open PDF
        doc = pymupdf.open(input_path)

        # Get list of embedded files
        embed_names = doc.embfile_names()

        if not embed_names:
            console.newline()
            console.info(f'No embedded files found in {input_path.name}')
            doc.close()
            return

        # Display count
        count = len(embed_names)
        console.newline()
        console.info(
            f'Found {count} embedded file{"s" if count != 1 else ""} in {input_path.name}:'
        )
        console.newline()

        # Display each embed
        for name in embed_names:
            if verbose:
                # Get metadata
                info = doc.embfile_info(name)
                size = info.get('size', 0)
                size_str = format_file_size(size)
                desc = info.get('description', '')

                # Build output string
                output_parts = [f'[faint]⎿ [/faint]{name} ({size_str})']

                if desc:
                    output_parts.append(f' - {desc}')

                console.print(''.join(output_parts))
            else:
                console.print(f'[faint]⎿ [/faint]{name}')

        doc.close()

    except (FileNotFoundError, ValueError):
        raise typer.Exit(1)
    except Exception as e:
        console.error(f'Error reading PDF: {str(e)}')
        raise typer.Exit(1)


@app.command(name='embed:remove', help='Remove embedded files from a PDF')
def remove_embed(
    input_file: Annotated[
        str,
        typer.Argument(help='PDF file to process'),
    ],
    names: Annotated[
        Optional[List[str]],
        typer.Argument(help='Names of embeds to remove'),
    ] = None,
    output: Annotated[
        Optional[str],
        typer.Option(
            '--output',
            '-o',
            help='Output file path. If not specified, creates {input}_no_embeds.pdf',
        ),
    ] = None,
    all: Annotated[
        bool,
        typer.Option('--all', help='Remove all embedded files'),
    ] = False,
):
    """
    Remove embedded files from a PDF.

    Creates a new PDF with specified embedded files removed. The original
    file is never modified.

    You must specify either embed names to remove OR use --all to remove
    all embeds (not both).

    When using --all, you'll be prompted to confirm the operation.

    Examples:

        # Remove specific embed
        parxy embed:remove document.pdf data.csv

        # Remove multiple embeds
        parxy embed:remove document.pdf data.csv report.docx

        # Remove with custom output path
        parxy embed:remove document.pdf data.csv -o clean.pdf

        # Remove all embeds (will prompt for confirmation)
        parxy embed:remove document.pdf --all
    """
    console.action('Remove embedded files', space_after=False)

    try:
        # Validate arguments
        if not names and not all:
            console.error(
                'You must specify either embed names to remove or use --all flag',
                panel=True,
            )
            raise ValueError('You must specify either embed names to remove or use --all flag')

        if names and all:
            console.error('Cannot specify both embed names and --all flag', panel=True)
            raise ValueError('Cannot specify both embed names and --all flag')

        # Validate input file
        input_path = validate_pdf_file(input_file)
        # Open PDF
        doc = pymupdf.open(input_path)

        # Get list of all embeds
        all_embeds = doc.embfile_names()

        if not all_embeds:
            console.newline()
            console.error(f'No embedded files found in {input_path.name}', panel=True)
            doc.close()
            raise ValueError(f'No embedded files found in {input_path.name}')

        # Determine which embeds to remove
        if all:
            embeds_to_remove = all_embeds

            # Show confirmation prompt
            console.newline()
            count = len(embeds_to_remove)

            if count <= 2:
                # Show all embeds
                console.print(
                    f'This will remove the following embedded file{"s" if count != 1 else ""} from {input_path.name}:'
                )
                for name in embeds_to_remove:
                    console.print(f'[faint]⎿ [/faint]{name}')
            else:
                # Show first + count
                console.print(
                    f'This will remove the following embedded file{"s" if count != 1 else ""} from {input_path.name}:'
                )
                console.print(f'[faint]⎿ [/faint]{embeds_to_remove[0]} and {count - 1} more')

            console.newline()
            confirm = typer.prompt('Continue? [y/N]', default='n')

            if confirm.lower() not in ['y', 'yes']:
                console.info('Operation cancelled')
                doc.close()
                raise typer.Exit(0)
        else:
            embeds_to_remove = names if names else []

            # Validate each embed exists
            for name in embeds_to_remove:
                if name not in all_embeds:
                    console.newline()
                    console.error(
                        f"Embed '{name}' not found in {input_path.name}", panel=True
                    )
                    console.newline()
                    console.print('Available embeds:')
                    for available in all_embeds:
                        console.print(f'[faint]⎿ [/faint]{available}')
                    doc.close()
                    raise ValueError(f"Embed '{name}' not found in {input_path.name}")

        # Determine output path
        if output is None:
            output_path = input_path.parent / f'{input_path.stem}_no_embeds.pdf'
        else:
            output_path = Path(output)

        # Make absolute if relative
        if not output_path.is_absolute():
            output_path = input_path.parent / output_path

        # Ensure .pdf extension
        if output_path.suffix.lower() != '.pdf':
            output_path = output_path.with_suffix('.pdf')

        # Check if output exists
        if output_path.exists():
            if not prompt_overwrite(output_path):
                console.info('Operation cancelled')
                doc.close()
                raise typer.Exit(0)

        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        console.newline()
        with console.shimmer(f'Removing {len(embeds_to_remove)} embed(s)...'):
            # Remove each embed
            for name in embeds_to_remove:
                doc.embfile_del(name)
                console.print(f'[faint]⎿ [/faint]Removed {name}')

            # Save the modified PDF
            doc.save(str(output_path))

        doc.close()

        console.newline()
        console.success(
            f'Successfully removed {len(embeds_to_remove)} embed{"s" if len(embeds_to_remove) != 1 else ""} from {output_path}'
        )

    except typer.Exit:
        raise
    except (FileNotFoundError, ValueError):
        raise typer.Exit(1)
    except Exception as e:
        console.error(f'Error processing PDF: {str(e)}')
        raise typer.Exit(1)


@app.command(name='embed:add', help='Add files as embeds to a PDF')
def add_embed(
    input_file: Annotated[
        str,
        typer.Argument(help='PDF file to add embeds to'),
    ],
    files: Annotated[
        List[str],
        typer.Argument(help='One or more files to embed'),
    ],
    output: Annotated[
        Optional[str],
        typer.Option(
            '--output',
            '-o',
            help='Output file path. If not specified, creates {input}_with_embeds.pdf',
        ),
    ] = None,
    description: Annotated[
        Optional[List[str]],
        typer.Option(
            '--description',
            '-d',
            help='Description for embedded file(s). Matched by position to files.',
        ),
    ] = None,
    name: Annotated[
        Optional[List[str]],
        typer.Option(
            '--name',
            '-n',
            help='Custom name(s) for embedded file(s). Matched by position to files.',
        ),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option('--overwrite', help='Overwrite existing embeds with same name'),
    ] = False,
):
    """
    Add files as embeds to a PDF.

    Creates a new PDF with the specified files embedded. The original
    file is never modified.

    Custom names and descriptions are matched by position to the files.
    If you provide fewer names/descriptions than files, the remaining
    files use their original names/no description.

    By default, attempting to add an embed with a name that already exists
    will result in an error. Use --overwrite to replace existing embeds.

    Examples:

        # Embed a single file
        parxy embed:add document.pdf data.csv

        # Embed multiple files
        parxy embed:add document.pdf data.csv report.docx chart.png

        # Embed with custom output path
        parxy embed:add document.pdf data.csv -o enhanced.pdf

        # Embed with description
        parxy embed:add document.pdf data.csv -d "Q4 Sales Data"

        # Embed with custom name
        parxy embed:add document.pdf data.csv -n "quarterly_sales.csv"

        # Embed multiple files with descriptions
        parxy embed:add document.pdf file1.csv file2.csv -d "Sales" -d "Revenue"

        # Overwrite existing embed
        parxy embed:add document.pdf data.csv --overwrite
    """
    console.action('Add embedded files', space_after=False)

    try:
        # Validate input file
        input_path = validate_pdf_file(input_file)

        # Validate all files to embed exist
        file_paths = []
        for file_str in files:
            file_path = Path(file_str)
            if not file_path.is_file():
                console.newline()
                console.error(f'File not found: {file_str}', panel=True)
                raise FileNotFoundError(f'File not found: {file_str}')
            file_paths.append(file_path)
        # Open PDF
        doc = pymupdf.open(input_path)

        # Get existing embeds
        existing_embeds = doc.embfile_names()

        console.newline()
        console.info(f'Embedding {len(file_paths)} file{"s" if len(file_paths) != 1 else ""}...')
        console.newline()

        # Process each file to embed
        with console.shimmer('Adding embeds...'):
            for idx, file_path in enumerate(file_paths):
                # Determine embed name
                embed_name = file_path.name
                if name is not None and idx < len(name):
                    embed_name = name[idx]

                # Check if embed already exists
                if embed_name in existing_embeds:
                    if not overwrite:
                        console.newline()
                        console.error(
                            f"Embed '{embed_name}' already exists in {input_path.name}",
                            panel=True,
                        )
                        console.newline()
                        console.print('Use --overwrite to replace it')
                        doc.close()
                        raise ValueError(f"Embed '{embed_name}' already exists. Use --overwrite to replace it")
                    else:
                        # Delete existing embed before adding new one
                        doc.embfile_del(embed_name)

                # Get description
                embed_desc = ''
                if description is not None and idx < len(description):
                    embed_desc = description[idx]

                # Read file content
                with open(file_path, 'rb') as f:
                    file_content = f.read()

                # Add embed
                doc.embfile_add(
                    name=embed_name,
                    buffer_=file_content,
                    filename=file_path.name,
                    desc=embed_desc,
                )

                # Build output message
                size_str = format_file_size(len(file_content))
                msg_parts = [f'[faint]⎿ [/faint]Added {embed_name} ({size_str})']
                if embed_desc:
                    msg_parts.append(f' - {embed_desc}')

                console.print(''.join(msg_parts))

        # Determine output path
        if output is None:
            output_path = input_path.parent / f'{input_path.stem}_with_embeds.pdf'
        else:
            output_path = Path(output)

        # Make absolute if relative
        if not output_path.is_absolute():
            output_path = input_path.parent / output_path

        # Ensure .pdf extension
        if output_path.suffix.lower() != '.pdf':
            output_path = output_path.with_suffix('.pdf')

        # Check if output exists
        if output_path.exists():
            if not prompt_overwrite(output_path):
                console.info('Operation cancelled')
                doc.close()
                raise typer.Exit(0)

        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save the PDF
        doc.save(str(output_path))
        doc.close()

        console.newline()
        console.success(
            f'Successfully added {len(file_paths)} embed{"s" if len(file_paths) != 1 else ""} to {output_path}'
        )

    except typer.Exit:
        raise
    except (FileNotFoundError, ValueError):
        raise typer.Exit(1)
    except Exception as e:
        console.error(f'Error processing PDF: {str(e)}')
        raise typer.Exit(1)


@app.command(name='embed', help='Extract an embedded file from a PDF')
def read_embed(
    input_file: Annotated[
        str,
        typer.Argument(help='PDF file containing the embed'),
    ],
    name: Annotated[
        str,
        typer.Argument(help='Name of embedded file to extract'),
    ],
    output: Annotated[
        Optional[str],
        typer.Option(
            '--output',
            '-o',
            help='Output file path. If not specified, saves to current directory with original name.',
        ),
    ] = None,
    stdout: Annotated[
        bool,
        typer.Option('--stdout', help='Output content to stdout (text files only)'),
    ] = False,
):
    """
    Extract an embedded file from a PDF.

    Extracts the specified embedded file from the PDF. By default, saves
    to the current directory with the original filename.

    Use -o to specify a custom output path, or --stdout to output text
    files directly to stdout (binary files cannot be output to stdout).

    Examples:

        # Extract to current directory
        parxy embed document.pdf data.csv

        # Extract to specific path
        parxy embed document.pdf data.csv -o /path/to/output.csv

        # Output text file to stdout
        parxy embed document.pdf notes.txt --stdout
    """
    console.action('Extract embedded file', space_after=False)

    try:
        # Validate input file
        input_path = validate_pdf_file(input_file)

        # Open PDF
        doc = pymupdf.open(input_path)

        # Get list of embeds
        embed_names = doc.embfile_names()

        # Validate embed exists
        if name not in embed_names:
            console.newline()
            console.error(f"Embed '{name}' not found in {input_path.name}", panel=True)

            if embed_names:
                console.newline()
                console.print('Available embeds:')
                for available in embed_names:
                    console.print(f'[faint]⎿ [/faint]{available}')
            else:
                console.newline()
                console.print('No embedded files found in this PDF')

            doc.close()
            raise ValueError(f"Embed '{name}' not found in {input_path.name}")

        # Extract content
        content = doc.embfile_get(name)

        # Handle stdout mode
        if stdout:
            # Check if binary
            if is_binary_file(content):
                console.newline()
                console.error(
                    f"Cannot output binary file to stdout.\nFile '{name}' appears to be binary.\nUse -o to save to a file instead.",
                    panel=True,
                )
                doc.close()
                raise ValueError(f"Cannot output binary file '{name}' to stdout")

            # Output to stdout
            sys.stdout.buffer.write(content)
            doc.close()
            return

        # Determine output path
        if output is None:
            output_path = Path.cwd() / name
        else:
            output_path = Path(output)

        # Check if output exists
        if output_path.exists():
            if not prompt_overwrite(output_path):
                console.info('Operation cancelled')
                doc.close()
                raise typer.Exit(0)

        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write content to file
        with open(output_path, 'wb') as f:
            f.write(content)

        doc.close()

        console.newline()
        size_str = format_file_size(len(content))
        console.success(f"Successfully extracted '{name}' ({size_str}) to {output_path}")

    except typer.Exit:
        raise
    except (FileNotFoundError, ValueError):
        raise typer.Exit(1)
    except Exception as e:
        console.error(f'Error extracting embed: {str(e)}')
        raise typer.Exit(1)


@app.command(name='embed:read', help='Extract an embedded file from a PDF', hidden=True)
def read_embed_alias(
    input_file: Annotated[
        str,
        typer.Argument(help='PDF file containing the embed'),
    ],
    name: Annotated[
        str,
        typer.Argument(help='Name of embedded file to extract'),
    ],
    output: Annotated[
        Optional[str],
        typer.Option(
            '--output',
            '-o',
            help='Output file path. If not specified, saves to current directory with original name.',
        ),
    ] = None,
    stdout: Annotated[
        bool,
        typer.Option('--stdout', help='Output content to stdout (text files only)'),
    ] = False,
):
    """Alias for embed command."""
    return read_embed(input_file, name, output, stdout)
