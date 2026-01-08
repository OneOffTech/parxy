"""PDF attached file commands."""

from pathlib import Path
from typing import List, Annotated, Optional
import sys

import typer

from parxy_cli.console.console import Console
from parxy_cli.services import (
    PdfService,
    format_file_size,
    validate_pdf_file,
    is_binary_file,
)

app = typer.Typer()
console = Console()


# ============================================================================
# Helper Functions
# ============================================================================


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


@app.command(name='attach:list', help='List attached files in a PDF')
def list_attachments(
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
    List all attached files in a PDF.

    Displays a list of all files attached to the specified PDF document.
    In verbose mode, shows additional metadata including file size,
    description, and modification date.

    Examples:

        # List attachments
        parxy attach:list document.pdf

        # List with detailed information
        parxy attach:list document.pdf --verbose
        parxy attach:list document.pdf -v
    """
    console.action('List attached files', space_after=False)

    try:
        # Validate input file
        try:
            input_path = validate_pdf_file(input_file)
        except FileNotFoundError as e:
            console.error(str(e), panel=True)
            raise
        except ValueError as e:
            console.error(str(e), panel=True)
            raise

        # Use service to list attachments
        with PdfService(input_path) as pdf:
            embed_names = pdf.list_attachments()

            if not embed_names:
                console.newline()
                console.info(f'No attached files found in {input_path.name}')
                return

            # Display count
            count = len(embed_names)
            console.newline()
            console.info(
                f'Found {count} attached file{"s" if count != 1 else ""} in {input_path.name}:'
            )
            console.newline()

            # Display each embed
            for name in embed_names:
                if verbose:
                    # Get metadata
                    info = pdf.get_attachment_info(name)
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

    except (FileNotFoundError, ValueError):
        raise typer.Exit(1)
    except Exception as e:
        console.error(f'Error reading PDF: {str(e)}')
        raise typer.Exit(1)


@app.command(name='attach:remove', help='Remove attached files from a PDF')
def remove_attachment(
    input_file: Annotated[
        str,
        typer.Argument(help='PDF file to process'),
    ],
    names: Annotated[
        Optional[List[str]],
        typer.Argument(help='Names of attachments to remove'),
    ] = None,
    output: Annotated[
        Optional[str],
        typer.Option(
            '--output',
            '-o',
            help='Output file path. If not specified, creates {input}_no_attachments.pdf',
        ),
    ] = None,
    all: Annotated[
        bool,
        typer.Option('--all', help='Remove all attached files'),
    ] = False,
):
    """
    Remove attached files from a PDF.

    Creates a new PDF with specified attached files removed. The original
    file is never modified.

    You must specify either attachment names to remove OR use --all to remove
    all attachments (not both).

    When using --all, you'll be prompted to confirm the operation.

    Examples:

        # Remove specific attachment
        parxy attach:remove document.pdf data.csv

        # Remove multiple attachments
        parxy attach:remove document.pdf data.csv report.docx

        # Remove with custom output path
        parxy attach:remove document.pdf data.csv -o clean.pdf

        # Remove all attachments (will prompt for confirmation)
        parxy attach:remove document.pdf --all
    """
    console.action('Remove attached files', space_after=False)

    try:
        # Validate arguments
        if not names and not all:
            console.error(
                'You must specify either attachment names to remove or use --all flag',
                panel=True,
            )
            raise ValueError(
                'You must specify either attachment names to remove or use --all flag'
            )

        if names and all:
            console.error(
                'Cannot specify both attachment names and --all flag', panel=True
            )
            raise ValueError('Cannot specify both attachment names and --all flag')

        # Validate input file
        try:
            input_path = validate_pdf_file(input_file)
        except FileNotFoundError as e:
            console.error(str(e), panel=True)
            raise
        except ValueError as e:
            console.error(str(e), panel=True)
            raise

        # Use service to handle attachments
        with PdfService(input_path) as pdf:
            # Get list of all embeds
            all_embeds = pdf.list_attachments()

            if not all_embeds:
                console.newline()
                console.error(
                    f'No attached files found in {input_path.name}', panel=True
                )
                raise ValueError(f'No attached files found in {input_path.name}')

            # Determine which embeds to remove
            if all:
                embeds_to_remove = all_embeds

                # Show confirmation prompt
                console.newline()
                count = len(embeds_to_remove)

                if count <= 2:
                    # Show all embeds
                    console.print(
                        f'This will remove the following attached file{"s" if count != 1 else ""} from {input_path.name}:'
                    )
                    for name in embeds_to_remove:
                        console.print(f'[faint]⎿ [/faint]{name}')
                else:
                    # Show first + count
                    console.print(
                        f'This will remove the following attached file{"s" if count != 1 else ""} from {input_path.name}:'
                    )
                    console.print(
                        f'[faint]⎿ [/faint]{embeds_to_remove[0]} and {count - 1} more'
                    )

                console.newline()
                confirm = typer.prompt('Continue? [y/N]', default='n')

                if confirm.lower() not in ['y', 'yes']:
                    console.info('Operation cancelled')
                    raise typer.Exit(0)
            else:
                embeds_to_remove = names if names else []

                # Validate each embed exists
                for name in embeds_to_remove:
                    if name not in all_embeds:
                        console.newline()
                        console.error(
                            f"Attachment '{name}' not found in {input_path.name}",
                            panel=True,
                        )
                        console.newline()
                        console.print('Available attachments:')
                        for available in all_embeds:
                            console.print(f'[faint]⎿ [/faint]{available}')
                        raise ValueError(
                            f"Attachment '{name}' not found in {input_path.name}"
                        )

            # Determine output path
            if output is None:
                output_path = (
                    input_path.parent / f'{input_path.stem}_no_attachments.pdf'
                )
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
                    raise typer.Exit(0)

            console.newline()
            with console.shimmer(f'Removing {len(embeds_to_remove)} attachment(s)...'):
                # Remove each attachment
                for name in embeds_to_remove:
                    pdf.remove_attachment(name)
                    console.print(f'[faint]⎿ [/faint]Removed {name}')

                # Save the modified PDF
                pdf.save(output_path)

            console.newline()
            console.success(
                f'Successfully removed {len(embeds_to_remove)} attachment{"s" if len(embeds_to_remove) != 1 else ""} from {output_path}'
            )

    except typer.Exit:
        raise
    except (FileNotFoundError, ValueError, KeyError):
        raise typer.Exit(1)
    except Exception as e:
        console.error(f'Error processing PDF: {str(e)}')
        raise typer.Exit(1)


@app.command(name='attach:add', help='Add files as attachments to a PDF')
def add_attachment(
    input_file: Annotated[
        str,
        typer.Argument(help='PDF file to add attachments to'),
    ],
    files: Annotated[
        List[str],
        typer.Argument(help='One or more files to attach'),
    ],
    output: Annotated[
        Optional[str],
        typer.Option(
            '--output',
            '-o',
            help='Output file path. If not specified, creates {input}_with_attachments.pdf',
        ),
    ] = None,
    description: Annotated[
        Optional[List[str]],
        typer.Option(
            '--description',
            '-d',
            help='Description for attached file(s). Matched by position to files.',
        ),
    ] = None,
    name: Annotated[
        Optional[List[str]],
        typer.Option(
            '--name',
            '-n',
            help='Custom name(s) for attached file(s). Matched by position to files.',
        ),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option(
            '--overwrite', help='Overwrite existing attachments with same name'
        ),
    ] = False,
):
    """
    Add files as attachments to a PDF.

    Creates a new PDF with the specified files attached. The original
    file is never modified.

    Custom names and descriptions are matched by position to the files.
    If you provide fewer names/descriptions than files, the remaining
    files use their original names/no description.

    By default, attempting to add an attachment with a name that already exists
    will result in an error. Use --overwrite to replace existing attachments.

    Examples:

        # Attach a single file
        parxy attach:add document.pdf data.csv

        # Attach multiple files
        parxy attach:add document.pdf data.csv report.docx chart.png

        # Attach with custom output path
        parxy attach:add document.pdf data.csv -o enhanced.pdf

        # Attach with description
        parxy attach:add document.pdf data.csv -d "Q4 Sales Data"

        # Attach with custom name
        parxy attach:add document.pdf data.csv -n "quarterly_sales.csv"

        # Attach multiple files with descriptions
        parxy attach:add document.pdf file1.csv file2.csv -d "Sales" -d "Revenue"

        # Overwrite existing attachment
        parxy attach:add document.pdf data.csv --overwrite
    """
    console.action('Add attached files', space_after=False)

    try:
        # Validate input file
        try:
            input_path = validate_pdf_file(input_file)
        except FileNotFoundError as e:
            console.error(str(e), panel=True)
            raise
        except ValueError as e:
            console.error(str(e), panel=True)
            raise

        # Validate all files to attach exist
        file_paths = []
        for file_str in files:
            file_path = Path(file_str)
            if not file_path.is_file():
                console.newline()
                console.error(f'File not found: {file_str}', panel=True)
                raise FileNotFoundError(f'File not found: {file_str}')
            file_paths.append(file_path)

        console.newline()
        console.info(
            f'Attaching {len(file_paths)} file{"s" if len(file_paths) != 1 else ""}...'
        )
        console.newline()

        # Use service to handle attachments
        with PdfService(input_path) as pdf:
            # Get existing attachments
            existing_embeds = pdf.list_attachments()

            # Process each file to attach
            with console.shimmer('Adding attachments...'):
                for idx, file_path in enumerate(file_paths):
                    # Determine attachment name
                    embed_name = file_path.name
                    if name is not None and idx < len(name):
                        embed_name = name[idx]

                    # Check if attachment already exists
                    if embed_name in existing_embeds:
                        if not overwrite:
                            console.newline()
                            console.error(
                                f"Attachment '{embed_name}' already exists in {input_path.name}",
                                panel=True,
                            )
                            console.newline()
                            console.print('Use --overwrite to replace it')
                            raise ValueError(
                                f"Attachment '{embed_name}' already exists. Use --overwrite to replace it"
                            )
                        else:
                            # Delete existing attachment before adding new one
                            pdf.remove_attachment(embed_name)

                    # Get description
                    embed_desc = ''
                    if description is not None and idx < len(description):
                        embed_desc = description[idx]

                    # Add attachment using service
                    pdf.add_attachment(file_path, name=embed_name, desc=embed_desc)

                    # Get file size for display
                    file_size = file_path.stat().st_size
                    size_str = format_file_size(file_size)

                    # Build output message
                    msg_parts = [f'[faint]⎿ [/faint]Added {embed_name} ({size_str})']
                    if embed_desc:
                        msg_parts.append(f' - {embed_desc}')

                    console.print(''.join(msg_parts))

            # Determine output path
            if output is None:
                output_path = (
                    input_path.parent / f'{input_path.stem}_with_attachments.pdf'
                )
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
                    raise typer.Exit(0)

            # Save the PDF
            pdf.save(output_path)

        console.newline()
        console.success(
            f'Successfully added {len(file_paths)} attachment{"s" if len(file_paths) != 1 else ""} to {output_path}'
        )

    except typer.Exit:
        raise
    except (FileNotFoundError, ValueError, KeyError):
        raise typer.Exit(1)
    except Exception as e:
        console.error(f'Error processing PDF: {str(e)}')
        raise typer.Exit(1)


@app.command(name='attach', help='Extract an attached file from a PDF')
def read_attachment(
    input_file: Annotated[
        str,
        typer.Argument(help='PDF file containing the attachment'),
    ],
    name: Annotated[
        str,
        typer.Argument(help='Name of attached file to extract'),
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
    Extract an attached file from a PDF.

    Extracts the specified attached file from the PDF. By default, saves
    to the current directory with the original filename.

    Use -o to specify a custom output path, or --stdout to output text
    files directly to stdout (binary files cannot be output to stdout).

    Examples:

        # Extract to current directory
        parxy attach document.pdf data.csv

        # Extract to specific path
        parxy attach document.pdf data.csv -o /path/to/output.csv

        # Output text file to stdout
        parxy attach document.pdf notes.txt --stdout
    """
    console.action('Extract attached file', space_after=False)

    try:
        # Validate input file
        try:
            input_path = validate_pdf_file(input_file)
        except FileNotFoundError as e:
            console.error(str(e), panel=True)
            raise
        except ValueError as e:
            console.error(str(e), panel=True)
            raise

        # Use service to extract attachment
        with PdfService(input_path) as pdf:
            # Get list of attachments
            embed_names = pdf.list_attachments()

            # Validate attachment exists
            if name not in embed_names:
                console.newline()
                console.error(
                    f"Attachment '{name}' not found in {input_path.name}", panel=True
                )

                if embed_names:
                    console.newline()
                    console.print('Available attachments:')
                    for available in embed_names:
                        console.print(f'[faint]⎿ [/faint]{available}')
                else:
                    console.newline()
                    console.print('No attached files found in this PDF')

                raise ValueError(f"Attachment '{name}' not found in {input_path.name}")

            # Extract content
            content = pdf.extract_attachment(name)

        # Handle stdout mode
        if stdout:
            # Check if binary
            if is_binary_file(content):
                console.newline()
                console.error(
                    f"Cannot output binary file to stdout.\nFile '{name}' appears to be binary.\nUse -o to save to a file instead.",
                    panel=True,
                )
                raise ValueError(f"Cannot output binary file '{name}' to stdout")

            # Output to stdout
            sys.stdout.buffer.write(content)
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
                raise typer.Exit(0)

        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write content to file
        with open(output_path, 'wb') as f:
            f.write(content)

        console.newline()
        size_str = format_file_size(len(content))
        console.success(
            f"Successfully extracted '{name}' ({size_str}) to {output_path}"
        )

    except typer.Exit:
        raise
    except (FileNotFoundError, ValueError, KeyError):
        raise typer.Exit(1)
    except Exception as e:
        console.error(f'Error extracting attachment: {str(e)}')
        raise typer.Exit(1)


@app.command(
    name='attach:read', help='Extract an attached file from a PDF', hidden=True
)
def read_attachment_alias(
    input_file: Annotated[
        str,
        typer.Argument(help='PDF file containing the attachment'),
    ],
    name: Annotated[
        str,
        typer.Argument(help='Name of attached file to extract'),
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
    """Alias for attach command."""
    return read_attachment(input_file, name, output, stdout)
