"""Run clang-format across shared C, C++, Objective-C, and CUDA source directories."""

# standard imports
import os
import subprocess

# variables
directories = [
    'examples',
    'src',
    'tests',
    'tools',
]
file_types = [
    'c',
    'cpp',
    'cu',
    'cuh',
    'h',
    'hpp',
    'm',
    'mm',
]


def clang_format(file: str):
    """Run clang-format on a source file.

    Parameters
    ----------
    file : str
        Source file path to format.
    """

    print(f'Formatting {file} ...')
    subprocess.run(['clang-format', '-i', file], check=True)


def main():
    """Format supported source files in configured directories.

    Notes
    -----
    Missing configured directories are ignored by ``os.walk``.
    """

    # walk the directories
    for directory in directories:
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.isfile(file_path) and file.rsplit('.')[-1] in file_types:
                    clang_format(file=file_path)


if __name__ == '__main__':
    main()
