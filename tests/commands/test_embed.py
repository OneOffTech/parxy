"""Test suite for PDF embed commands."""

import pytest
from pathlib import Path
from typer.testing import CliRunner
from click.utils import strip_ansi
import pymupdf
import typer

from parxy_cli.commands.embed import (
    app,
    format_file_size,
    validate_pdf_file,
    is_binary_file,
)


@pytest.fixture
def runner():
    """Fixture providing a CLI runner."""
    return CliRunner()


@pytest.fixture
def sample_pdf_with_embeds(tmp_path):
    """Create a sample PDF with embedded files."""
    # Create the main PDF
    pdf_path = tmp_path / 'document.pdf'
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((100, 100), 'Test document with embeds')
    
    # Create some files to embed
    text_file = tmp_path / 'notes.txt'
    text_file.write_text('This is a text file with some notes.')
    
    csv_file = tmp_path / 'data.csv'
    csv_file.write_text('name,value\nitem1,100\nitem2,200')
    
    binary_file = tmp_path / 'binary.bin'
    binary_file.write_bytes(b'\x00\x01\x02\x03\x04\x05')
    
    # Embed the files
    doc.embfile_add(
        name='notes.txt',
        buffer_=text_file.read_bytes(),
        filename='notes.txt',
        desc='Text notes',
    )
    doc.embfile_add(
        name='data.csv',
        buffer_=csv_file.read_bytes(),
        filename='data.csv',
        desc='Sales data',
    )
    doc.embfile_add(
        name='binary.bin',
        buffer_=binary_file.read_bytes(),
        filename='binary.bin',
        desc='Binary file',
    )
    
    doc.save(str(pdf_path))
    doc.close()
    
    return {
        'pdf': pdf_path,
        'text_file': text_file,
        'csv_file': csv_file,
        'binary_file': binary_file,
        'tmp_path': tmp_path,
    }


@pytest.fixture
def sample_pdf_no_embeds(tmp_path):
    """Create a sample PDF without embedded files."""
    pdf_path = tmp_path / 'empty.pdf'
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((100, 100), 'Test document without embeds')
    doc.save(str(pdf_path))
    doc.close()
    
    return pdf_path


@pytest.fixture
def sample_files_to_embed(tmp_path):
    """Create sample files for embedding."""
    files = {}
    
    # Text file
    text_file = tmp_path / 'file1.txt'
    text_file.write_text('Sample text content')
    files['text'] = text_file
    
    # CSV file
    csv_file = tmp_path / 'file2.csv'
    csv_file.write_text('col1,col2\nval1,val2')
    files['csv'] = csv_file
    
    # Another text file
    text_file2 = tmp_path / 'file3.txt'
    text_file2.write_text('Another text file')
    files['text2'] = text_file2
    
    return files


# Tests for helper functions
class TestHelperFunctions:
    """Tests for helper functions."""
    
    def test_format_file_size_bytes(self):
        """Test formatting bytes."""
        assert format_file_size(100) == '100.0 B'
    
    def test_format_file_size_kilobytes(self):
        """Test formatting kilobytes."""
        assert format_file_size(1024) == '1.0 KB'
        assert format_file_size(1536) == '1.5 KB'
    
    def test_format_file_size_megabytes(self):
        """Test formatting megabytes."""
        assert format_file_size(1048576) == '1.0 MB'
        assert format_file_size(2621440) == '2.5 MB'
    
    def test_format_file_size_gigabytes(self):
        """Test formatting gigabytes."""
        assert format_file_size(1073741824) == '1.0 GB'
    
    def test_validate_pdf_file_success(self, sample_pdf_no_embeds):
        """Test validating a valid PDF file."""
        path = validate_pdf_file(str(sample_pdf_no_embeds))
        assert path == sample_pdf_no_embeds
    
    def test_validate_pdf_file_not_found(self, tmp_path):
        """Test validating a nonexistent file."""
        with pytest.raises(FileNotFoundError):
            validate_pdf_file(str(tmp_path / 'nonexistent.pdf'))

    def test_validate_pdf_file_not_pdf(self, tmp_path):
        """Test validating a non-PDF file."""
        txt_file = tmp_path / 'file.txt'
        txt_file.write_text('not a pdf')
        with pytest.raises(ValueError):
            validate_pdf_file(str(txt_file))
    
    def test_is_binary_file_text(self):
        """Test detecting text content."""
        text_content = b'This is plain text content'
        assert not is_binary_file(text_content)
    
    def test_is_binary_file_binary(self):
        """Test detecting binary content."""
        binary_content = b'\x00\x01\x02\x03'
        assert is_binary_file(binary_content)
    
    def test_is_binary_file_utf8(self):
        """Test detecting UTF-8 encoded text."""
        utf8_content = 'UTF-8 text with special chars: café'.encode('utf-8')
        assert not is_binary_file(utf8_content)


# Tests for embed:list command
class TestListCommand:
    """Tests for the embed:list command."""
    
    def test_list_embeds_with_files(self, runner, sample_pdf_with_embeds):
        """Test listing embeds from PDF with embedded files."""
        result = runner.invoke(
            app,
            ['embed:list', str(sample_pdf_with_embeds['pdf'])],
        )
        
        assert result.exit_code == 0
        assert 'Found 3 embedded file' in result.stdout
        assert 'notes.txt' in result.stdout
        assert 'data.csv' in result.stdout
        assert 'binary.bin' in result.stdout
    
    def test_list_embeds_verbose(self, runner, sample_pdf_with_embeds):
        """Test listing embeds with verbose flag."""
        result = runner.invoke(
            app,
            ['embed:list', str(sample_pdf_with_embeds['pdf']), '--verbose'],
        )
        
        assert result.exit_code == 0
        assert 'Found 3 embedded file' in result.stdout
        # Should show descriptions
        assert 'Text notes' in result.stdout
        assert 'Sales data' in result.stdout
        # Should show file sizes
        assert 'B' in result.stdout or 'KB' in result.stdout
    
    def test_list_embeds_no_files(self, runner, sample_pdf_no_embeds):
        """Test listing embeds from PDF without embedded files."""
        result = runner.invoke(
            app,
            ['embed:list', str(sample_pdf_no_embeds)],
        )
        
        assert result.exit_code == 0
        assert 'No embedded files found' in result.stdout
    
    def test_list_embeds_nonexistent_pdf(self, runner, tmp_path):
        """Test listing embeds from nonexistent PDF."""
        result = runner.invoke(
            app,
            ['embed:list', str(tmp_path / 'nonexistent.pdf')],
        )
        
        assert result.exit_code == 1
        assert 'not found' in result.stdout.lower()
    
    def test_list_embeds_non_pdf_file(self, runner, tmp_path):
        """Test listing embeds from non-PDF file."""
        txt_file = tmp_path / 'file.txt'
        txt_file.write_text('not a pdf')
        
        result = runner.invoke(
            app,
            ['embed:list', str(txt_file)],
        )
        
        assert result.exit_code == 1
        assert 'must be a pdf' in result.stdout.lower()


# Tests for embed:add command
class TestAddCommand:
    """Tests for the embed:add command."""
    
    def test_add_single_embed(self, runner, sample_pdf_no_embeds, sample_files_to_embed, tmp_path):
        """Test adding a single embed to PDF."""
        output = tmp_path / 'output.pdf'
        result = runner.invoke(
            app,
            [
                'embed:add',
                str(sample_pdf_no_embeds),
                str(sample_files_to_embed['text']),
                '--output',
                str(output),
            ],
        )
        
        assert result.exit_code == 0
        assert output.exists()
        
        # Verify embed was added
        doc = pymupdf.open(str(output))
        embeds = doc.embfile_names()
        assert len(embeds) == 1
        assert 'file1.txt' in embeds
        doc.close()
    
    def test_add_multiple_embeds(self, runner, sample_pdf_no_embeds, sample_files_to_embed, tmp_path):
        """Test adding multiple embeds to PDF."""
        output = tmp_path / 'output.pdf'
        result = runner.invoke(
            app,
            [
                'embed:add',
                str(sample_pdf_no_embeds),
                str(sample_files_to_embed['text']),
                str(sample_files_to_embed['csv']),
                '--output',
                str(output),
            ],
        )
        
        assert result.exit_code == 0
        assert output.exists()
        
        # Verify embeds were added
        doc = pymupdf.open(str(output))
        embeds = doc.embfile_names()
        assert len(embeds) == 2
        assert 'file1.txt' in embeds
        assert 'file2.csv' in embeds
        doc.close()
    
    def test_add_embed_with_description(self, runner, sample_pdf_no_embeds, sample_files_to_embed, tmp_path):
        """Test adding embed with custom description."""
        output = tmp_path / 'output.pdf'
        result = runner.invoke(
            app,
            [
                'embed:add',
                str(sample_pdf_no_embeds),
                str(sample_files_to_embed['text']),
                '--description',
                'Custom description',
                '--output',
                str(output),
            ],
        )
        
        assert result.exit_code == 0
        assert output.exists()
        
        # Verify description
        doc = pymupdf.open(str(output))
        info = doc.embfile_info('file1.txt')
        assert info['description'] == 'Custom description'
        doc.close()
    
    def test_add_embed_with_custom_name(self, runner, sample_pdf_no_embeds, sample_files_to_embed, tmp_path):
        """Test adding embed with custom name."""
        output = tmp_path / 'output.pdf'
        result = runner.invoke(
            app,
            [
                'embed:add',
                str(sample_pdf_no_embeds),
                str(sample_files_to_embed['text']),
                '--name',
                'custom_name.txt',
                '--output',
                str(output),
            ],
        )
        
        assert result.exit_code == 0
        assert output.exists()
        
        # Verify custom name
        doc = pymupdf.open(str(output))
        embeds = doc.embfile_names()
        assert 'custom_name.txt' in embeds
        assert 'file1.txt' not in embeds
        doc.close()
    
    def test_add_embed_duplicate_without_overwrite(self, runner, sample_pdf_with_embeds, sample_files_to_embed, tmp_path):
        """Test adding duplicate embed without overwrite flag fails."""
        # Create a file with the same name as an existing embed
        duplicate_file = tmp_path / 'notes.txt'
        duplicate_file.write_text('Different content')
        
        output = tmp_path / 'output.pdf'
        result = runner.invoke(
            app,
            [
                'embed:add',
                str(sample_pdf_with_embeds['pdf']),
                str(duplicate_file),
                '--output',
                str(output),
            ],
        )
        
        assert result.exit_code == 1
        assert 'already exists' in result.stdout.lower()
        assert '--overwrite' in result.stdout.lower()
    
    def test_add_embed_duplicate_with_overwrite(self, runner, sample_pdf_with_embeds, tmp_path):
        """Test adding duplicate embed with overwrite flag succeeds."""
        # Create a NEW file (not overwriting the fixture's notes.txt)
        new_notes_path = tmp_path / 'new_notes.txt'
        new_content = 'New content for notes'
        new_notes_path.write_text(new_content)

        output = tmp_path / 'output.pdf'
        result = runner.invoke(
            app,
            [
                'embed:add',
                str(sample_pdf_with_embeds['pdf']),
                str(new_notes_path),
                '--name',  # Use the same name as existing embed
                'notes.txt',
                '--overwrite',
                '--output',
                str(output),
            ],
        )

        assert result.exit_code == 0
        assert output.exists()

        # Verify content was replaced
        doc = pymupdf.open(str(output))
        content = doc.embfile_get('notes.txt')
        assert content.decode('utf-8') == new_content
        doc.close()
    
    def test_add_embed_default_output_path(self, runner, sample_pdf_no_embeds, sample_files_to_embed):
        """Test that default output path is created correctly."""
        result = runner.invoke(
            app,
            [
                'embed:add',
                str(sample_pdf_no_embeds),
                str(sample_files_to_embed['text']),
            ],
        )
        
        assert result.exit_code == 0
        
        # Default output should be {input_stem}_with_embeds.pdf
        expected_output = sample_pdf_no_embeds.parent / 'empty_with_embeds.pdf'
        assert expected_output.exists()
    
    def test_add_embed_file_not_found(self, runner, sample_pdf_no_embeds, tmp_path):
        """Test adding nonexistent file fails."""
        output = tmp_path / 'output.pdf'
        result = runner.invoke(
            app,
            [
                'embed:add',
                str(sample_pdf_no_embeds),
                str(tmp_path / 'nonexistent.txt'),
                '--output',
                str(output),
            ],
        )
        
        assert result.exit_code == 1
        assert 'not found' in result.stdout.lower()
    
    def test_add_embed_multiple_descriptions(self, runner, sample_pdf_no_embeds, sample_files_to_embed, tmp_path):
        """Test adding multiple embeds with descriptions."""
        output = tmp_path / 'output.pdf'
        result = runner.invoke(
            app,
            [
                'embed:add',
                str(sample_pdf_no_embeds),
                str(sample_files_to_embed['text']),
                str(sample_files_to_embed['csv']),
                '--description',
                'First file',
                '--description',
                'Second file',
                '--output',
                str(output),
            ],
        )
        
        assert result.exit_code == 0
        assert output.exists()
        
        # Verify descriptions
        doc = pymupdf.open(str(output))
        info1 = doc.embfile_info('file1.txt')
        info2 = doc.embfile_info('file2.csv')
        assert info1['description'] == 'First file'
        assert info2['description'] == 'Second file'
        doc.close()
    
    def test_add_embed_fewer_descriptions_than_files(self, runner, sample_pdf_no_embeds, sample_files_to_embed, tmp_path):
        """Test adding files with fewer descriptions than files."""
        output = tmp_path / 'output.pdf'
        result = runner.invoke(
            app,
            [
                'embed:add',
                str(sample_pdf_no_embeds),
                str(sample_files_to_embed['text']),
                str(sample_files_to_embed['csv']),
                str(sample_files_to_embed['text2']),
                '--description',
                'Only first',
                '--output',
                str(output),
            ],
        )
        
        assert result.exit_code == 0
        assert output.exists()
        
        # Verify first has description, others don't
        doc = pymupdf.open(str(output))
        info1 = doc.embfile_info('file1.txt')
        info2 = doc.embfile_info('file2.csv')
        assert info1['description'] == 'Only first'
        assert info2['description'] == ''
        doc.close()


# Tests for embed:remove command
class TestRemoveCommand:
    """Tests for the embed:remove command."""
    
    def test_remove_single_embed(self, runner, sample_pdf_with_embeds, tmp_path):
        """Test removing a single embed."""
        output = tmp_path / 'output.pdf'
        result = runner.invoke(
            app,
            [
                'embed:remove',
                str(sample_pdf_with_embeds['pdf']),
                'notes.txt',
                '--output',
                str(output),
            ],
        )
        
        assert result.exit_code == 0
        assert output.exists()
        
        # Verify embed was removed
        doc = pymupdf.open(str(output))
        embeds = doc.embfile_names()
        assert 'notes.txt' not in embeds
        assert 'data.csv' in embeds
        assert 'binary.bin' in embeds
        doc.close()
    
    def test_remove_multiple_embeds(self, runner, sample_pdf_with_embeds, tmp_path):
        """Test removing multiple embeds."""
        output = tmp_path / 'output.pdf'
        result = runner.invoke(
            app,
            [
                'embed:remove',
                str(sample_pdf_with_embeds['pdf']),
                'notes.txt',
                'data.csv',
                '--output',
                str(output),
            ],
        )
        
        assert result.exit_code == 0
        assert output.exists()
        
        # Verify embeds were removed
        doc = pymupdf.open(str(output))
        embeds = doc.embfile_names()
        assert 'notes.txt' not in embeds
        assert 'data.csv' not in embeds
        assert 'binary.bin' in embeds
        doc.close()
    
    def test_remove_all_embeds_with_confirmation(self, runner, sample_pdf_with_embeds, tmp_path):
        """Test removing all embeds with confirmation."""
        output = tmp_path / 'output.pdf'
        result = runner.invoke(
            app,
            [
                'embed:remove',
                str(sample_pdf_with_embeds['pdf']),
                '--all',
                '--output',
                str(output),
            ],
            input='y\n',  # Confirm
        )
        
        assert result.exit_code == 0
        assert output.exists()
        assert 'Continue? [y/N]' in result.stdout
        
        # Verify all embeds were removed
        doc = pymupdf.open(str(output))
        embeds = doc.embfile_names()
        assert len(embeds) == 0
        doc.close()
    
    def test_remove_all_embeds_cancel_confirmation(self, runner, sample_pdf_with_embeds, tmp_path):
        """Test cancelling removal of all embeds."""
        output = tmp_path / 'output.pdf'
        result = runner.invoke(
            app,
            [
                'embed:remove',
                str(sample_pdf_with_embeds['pdf']),
                '--all',
                '--output',
                str(output),
            ],
            input='n\n',  # Cancel
        )
        
        assert result.exit_code == 0
        assert 'cancelled' in result.stdout.lower()
        assert not output.exists()
    
    def test_remove_all_shows_embed_list_small(self, runner, sample_pdf_with_embeds, tmp_path):
        """Test that removing all embeds shows list when ≤2 embeds."""
        # Create PDF with only 2 embeds
        pdf_path = tmp_path / 'two_embeds.pdf'
        doc = pymupdf.open()
        page = doc.new_page(width=612, height=792)
        page.insert_text((100, 100), 'Test')
        doc.embfile_add(name='file1.txt', buffer_=b'content1', filename='file1.txt')
        doc.embfile_add(name='file2.txt', buffer_=b'content2', filename='file2.txt')
        doc.save(str(pdf_path))
        doc.close()
        
        output = tmp_path / 'output.pdf'
        result = runner.invoke(
            app,
            [
                'embed:remove',
                str(pdf_path),
                '--all',
                '--output',
                str(output),
            ],
            input='n\n',
        )
        
        assert result.exit_code == 0
        # Should list both files
        assert 'file1.txt' in result.stdout
        assert 'file2.txt' in result.stdout
    
    def test_remove_all_shows_count_large(self, runner, tmp_path):
        """Test that removing all embeds shows count when >2 embeds."""
        # Create PDF with 4 embeds
        pdf_path = tmp_path / 'many_embeds.pdf'
        doc = pymupdf.open()
        page = doc.new_page(width=612, height=792)
        page.insert_text((100, 100), 'Test')
        for i in range(4):
            doc.embfile_add(name=f'file{i}.txt', buffer_=b'content', filename=f'file{i}.txt')
        doc.save(str(pdf_path))
        doc.close()
        
        output = tmp_path / 'output.pdf'
        result = runner.invoke(
            app,
            [
                'embed:remove',
                str(pdf_path),
                '--all',
                '--output',
                str(output),
            ],
            input='n\n',
        )
        
        assert result.exit_code == 0

        cleaned_output = strip_ansi(result.stdout)

        # Should show first file and count
        assert 'file0.txt' in cleaned_output
        assert '3 more' in cleaned_output
    
    def test_remove_nonexistent_embed(self, runner, sample_pdf_with_embeds, tmp_path):
        """Test removing nonexistent embed fails."""
        output = tmp_path / 'output.pdf'
        result = runner.invoke(
            app,
            [
                'embed:remove',
                str(sample_pdf_with_embeds['pdf']),
                'nonexistent.txt',
                '--output',
                str(output),
            ],
        )
        
        assert result.exit_code == 1

        cleaned_output = strip_ansi(result.stdout)

        assert 'not found' in cleaned_output.lower()
        assert 'Available embeds:' in cleaned_output
    
    def test_remove_from_pdf_without_embeds(self, runner, sample_pdf_no_embeds, tmp_path):
        """Test removing from PDF without embeds fails."""
        output = tmp_path / 'output.pdf'
        result = runner.invoke(
            app,
            [
                'embed:remove',
                str(sample_pdf_no_embeds),
                'any.txt',
                '--output',
                str(output),
            ],
        )
        
        assert result.exit_code == 1
        assert 'no embedded files found' in strip_ansi(result.stdout).lower()
    
    def test_remove_default_output_path(self, runner, sample_pdf_with_embeds):
        """Test that default output path is created correctly."""
        result = runner.invoke(
            app,
            [
                'embed:remove',
                str(sample_pdf_with_embeds['pdf']),
                'notes.txt',
            ],
        )
        
        assert result.exit_code == 0
        
        # Default output should be {input_stem}_no_embeds.pdf
        expected_output = sample_pdf_with_embeds['pdf'].parent / 'document_no_embeds.pdf'
        assert expected_output.exists()
    
    def test_remove_neither_names_nor_all(self, runner, sample_pdf_with_embeds, tmp_path):
        """Test that providing neither names nor --all fails."""
        output = tmp_path / 'output.pdf'
        result = runner.invoke(
            app,
            [
                'embed:remove',
                str(sample_pdf_with_embeds['pdf']),
                '--output',
                str(output),
            ],
        )
        
        assert result.exit_code == 1
        assert 'must specify' in strip_ansi(result.stdout).lower()
    
    def test_remove_both_names_and_all(self, runner, sample_pdf_with_embeds, tmp_path):
        """Test that providing both names and --all fails."""
        output = tmp_path / 'output.pdf'
        result = runner.invoke(
            app,
            [
                'embed:remove',
                str(sample_pdf_with_embeds['pdf']),
                'notes.txt',
                '--all',
                '--output',
                str(output),
            ],
        )
        
        assert result.exit_code == 1
        assert 'cannot' in result.stdout.lower()


# Tests for embed and embed:read commands
class TestReadCommand:
    """Tests for the embed and embed:read commands."""
    
    def test_read_embed_to_current_directory(self, runner, sample_pdf_with_embeds, tmp_path):
        """Test extracting embed to current directory."""
        # Create a subdirectory to avoid file conflicts with fixture files
        import os
        extract_dir = tmp_path / 'extract'
        extract_dir.mkdir()
        original_cwd = os.getcwd()
        os.chdir(extract_dir)

        try:
            result = runner.invoke(
                app,
                [
                    'embed',
                    str(sample_pdf_with_embeds['pdf']),
                    'notes.txt',
                ],
            )

            assert result.exit_code == 0
            assert (extract_dir / 'notes.txt').exists()

            # Verify content
            content = (extract_dir / 'notes.txt').read_text()
            assert 'text file with some notes' in content
        finally:
            os.chdir(original_cwd)
    
    def test_read_embed_with_output_path(self, runner, sample_pdf_with_embeds, tmp_path):
        """Test extracting embed to specific path."""
        output = tmp_path / 'extracted.txt'
        result = runner.invoke(
            app,
            [
                'embed',
                str(sample_pdf_with_embeds['pdf']),
                'notes.txt',
                '--output',
                str(output),
            ],
        )
        
        assert result.exit_code == 0
        assert output.exists()
        
        # Verify content
        content = output.read_text()
        assert 'text file with some notes' in content
    
    def test_read_embed_to_stdout(self, runner, sample_pdf_with_embeds):
        """Test extracting text embed to stdout."""
        result = runner.invoke(
            app,
            [
                'embed',
                str(sample_pdf_with_embeds['pdf']),
                'notes.txt',
                '--stdout',
            ],
        )
        
        assert result.exit_code == 0
        assert 'text file with some notes' in result.stdout
    
    def test_read_binary_to_stdout_fails(self, runner, sample_pdf_with_embeds):
        """Test extracting binary embed to stdout fails."""
        result = runner.invoke(
            app,
            [
                'embed',
                str(sample_pdf_with_embeds['pdf']),
                'binary.bin',
                '--stdout',
            ],
        )
        
        assert result.exit_code == 1
        assert 'cannot output binary' in result.stdout.lower()
        assert 'use -o' in result.stdout.lower()
    
    def test_read_nonexistent_embed(self, runner, sample_pdf_with_embeds, tmp_path):
        """Test extracting nonexistent embed fails."""
        output = tmp_path / 'output.txt'
        result = runner.invoke(
            app,
            [
                'embed',
                str(sample_pdf_with_embeds['pdf']),
                'nonexistent.txt',
                '--output',
                str(output),
            ],
        )
        
        assert result.exit_code == 1
        assert 'not found' in result.stdout.lower()
        assert 'Available embeds:' in result.stdout
    
    def test_read_from_pdf_without_embeds(self, runner, sample_pdf_no_embeds, tmp_path):
        """Test extracting from PDF without embeds fails."""
        output = tmp_path / 'output.txt'
        result = runner.invoke(
            app,
            [
                'embed',
                str(sample_pdf_no_embeds),
                'any.txt',
                '--output',
                str(output),
            ],
        )
        
        assert result.exit_code == 1

        cleaned_output = strip_ansi(result.stdout)
        
        assert 'not found' in cleaned_output.lower()
        assert 'no embedded files found' in cleaned_output.lower()
    
    def test_read_embed_alias(self, runner, sample_pdf_with_embeds, tmp_path):
        """Test that embed:read alias works."""
        output = tmp_path / 'output.txt'
        result = runner.invoke(
            app,
            [
                'embed:read',
                str(sample_pdf_with_embeds['pdf']),
                'notes.txt',
                '--output',
                str(output),
            ],
        )
        
        assert result.exit_code == 0
        assert output.exists()
    
    def test_read_embed_multiple_files(self, runner, sample_pdf_with_embeds, tmp_path):
        """Test extracting multiple embeds one by one."""
        # Extract first file (use different name to avoid conflict with fixture files)
        output1 = tmp_path / 'extracted_notes.txt'
        result1 = runner.invoke(
            app,
            [
                'embed',
                str(sample_pdf_with_embeds['pdf']),
                'notes.txt',
                '--output',
                str(output1),
            ],
        )

        assert result1.exit_code == 0
        assert output1.exists()

        # Extract second file (use different name to avoid conflict with fixture files)
        output2 = tmp_path / 'extracted_data.csv'
        result2 = runner.invoke(
            app,
            [
                'embed',
                str(sample_pdf_with_embeds['pdf']),
                'data.csv',
                '--output',
                str(output2),
            ],
        )

        assert result2.exit_code == 0
        assert output2.exists()

        # Verify both have correct content
        assert 'notes' in output1.read_text()
        assert 'name,value' in output2.read_text()
    
    def test_read_embed_csv_content(self, runner, sample_pdf_with_embeds, tmp_path):
        """Test extracting and verifying CSV content."""
        output = tmp_path / 'extracted_data.csv'  # Use different name to avoid conflict
        result = runner.invoke(
            app,
            [
                'embed',
                str(sample_pdf_with_embeds['pdf']),
                'data.csv',
                '--output',
                str(output),
            ],
        )

        assert result.exit_code == 0
        assert output.exists()

        # Verify CSV content
        content = output.read_text()
        assert 'name,value' in content
        assert 'item1,100' in content
        assert 'item2,200' in content

    def test_read_embed_from_fixture_pdf(self, runner, tmp_path):
        """Test extracting embed from fixture PDF file."""
        fixture_pdf = Path(__file__).parent.parent / 'fixtures' / 'pdf-with-embed.pdf'
        output = tmp_path / 'extracted_experiment.csv'

        result = runner.invoke(
            app,
            [
                'embed',
                str(fixture_pdf),
                'experiment.csv',
                '--output',
                str(output),
            ],
        )

        assert result.exit_code == 0
        assert output.exists()

        # Verify CSV content
        content = output.read_text()
        assert 'date;value;' in content
        assert '2026-01-07;10' in content
