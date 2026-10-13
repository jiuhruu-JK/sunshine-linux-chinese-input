"""Tests for the clang-format helper."""

# standard imports
import os

# local imports
import scripts.update_clang_format as update_clang_format


def test_directories_include_expected_roots():
    """Verify the formatter scans the expected shared source roots."""

    assert update_clang_format.directories == [
        'examples',
        'src',
        'tests',
        'tools',
    ]


def test_file_types_include_shared_extensions():
    """Verify the formatter includes shared source extensions."""

    assert update_clang_format.file_types == [
        'c',
        'cpp',
        'cu',
        'cuh',
        'h',
        'hpp',
        'm',
        'mm',
    ]


def test_clang_format_invokes_clang_format(capsys, monkeypatch):
    """Verify the formatter delegates to clang-format with the target file."""

    calls = []

    def fake_run(command, check):
        """Record clang-format subprocess calls."""

        calls.append({
            'check': check,
            'command': command,
        })

    monkeypatch.setattr(update_clang_format.subprocess, 'run', fake_run)

    update_clang_format.clang_format(file='src/example.cpp')

    assert calls == [
        {
            'check': True,
            'command': ['clang-format', '-i', 'src/example.cpp'],
        },
    ]
    assert capsys.readouterr().out == 'Formatting src/example.cpp ...\n'


def test_main_formats_supported_files_only(monkeypatch, tmp_path):
    """Verify the main scan formats supported files only."""

    tmp_root = str(tmp_path)
    files = [
        os.path.join(tmp_root, 'src', 'main.cpp'),
        os.path.join(tmp_root, 'src', 'nested', 'kernel.cu'),
        os.path.join(tmp_root, 'src', 'nested', 'kernel.cuh'),
        os.path.join(tmp_root, 'tests', 'test_helper.mm'),
        os.path.join(tmp_root, 'tools', 'tool.h'),
        os.path.join(tmp_root, 'tools', 'notes.txt'),
        os.path.join(tmp_root, 'docs', 'ignored.cpp'),
    ]
    for file in files:
        os.makedirs(os.path.dirname(file), exist_ok=True)
        with open(file, 'w', encoding='utf-8') as file_handle:
            file_handle.write('// test\n')

    formatted_files = []

    def fake_clang_format(file):
        """Record files selected for formatting."""

        formatted_files.append(file.replace(os.sep, '/'))

    monkeypatch.chdir(tmp_root)
    monkeypatch.setattr(update_clang_format, 'clang_format', fake_clang_format)

    update_clang_format.main()

    assert set(formatted_files) == {
        'src/main.cpp',
        'src/nested/kernel.cu',
        'src/nested/kernel.cuh',
        'tests/test_helper.mm',
        'tools/tool.h',
    }
