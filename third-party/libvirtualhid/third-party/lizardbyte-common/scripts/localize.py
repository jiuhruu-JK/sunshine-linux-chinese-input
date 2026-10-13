"""Locale maintenance helpers for gettext and Babel workflows."""

# standard imports
import argparse
import datetime
import json
import os
import subprocess
import urllib.request
from dataclasses import dataclass

LANGUAGES_URL = (
    'https://raw.githubusercontent.com/LizardByte/i18n/refs/heads/dist/'
    '458f881791aebba1d4dde491bw4/languages.json'
)
DEFAULT_EXTENSIONS = [
    'c',
    'cc',
    'cpp',
    'cxx',
    'h',
    'hh',
    'hpp',
    'hxx',
    'm',
    'mm',
]
DEFAULT_KEYWORDS = [
    'translate:1,1t',
    'translate:1c,2,2t',
    'translate:1,2,3t',
    'translate:1c,2,3,4t',
    'gettext:1',
    'pgettext:1c,2',
    'ngettext:1,2',
    'npgettext:1c,2,3',
]
DEFAULT_SOURCE_DIRECTORIES = [
    'src',
]


@dataclass
class LocaleContext:
    """Resolved locale maintenance settings.

    Attributes
    ----------
    root_dir : str
        Repository root directory.
    locale_dir : str
        Directory containing gettext and Babel locale files.
    source_directories : list[str]
        Source directories to scan for translatable strings.
    extensions : list[str]
        File extensions to include during source scanning.
    keywords : list[str]
        xgettext keyword expressions to extract.
    project_name : str
        Project or package name used in generated metadata.
    project_owner : str
        Project owner used in generated metadata.
    domain : str
        gettext domain name.
    bugs_address : str
        Address recorded in generated files for translation bugs.
    language_source_url : str
        URL to the shared languages metadata file.
    target_locales : list[str]
        Locale codes to initialize.
    """

    root_dir: str
    locale_dir: str
    source_directories: list[str]
    extensions: list[str]
    keywords: list[str]
    project_name: str
    project_owner: str
    domain: str
    bugs_address: str
    language_source_url: str
    target_locales: list[str]


def split_values(values: list[str] | None) -> list[str]:
    """Split comma-separated CLI values into a flat list.

    Parameters
    ----------
    values : list[str] | None
        Values collected by ``argparse`` from repeatable options.

    Returns
    -------
    list[str]
        Non-empty, stripped values in input order.
    """

    if values is None:
        return []

    split_items = []
    for value in values:
        for item in value.split(','):
            item = item.strip()
            if item:
                split_items.append(item)

    return split_items


def resolve_path(root_dir: str, path: str) -> str:
    """Resolve a path relative to a repository root.

    Parameters
    ----------
    root_dir : str
        Repository root directory.
    path : str
        Absolute path or path relative to ``root_dir``.

    Returns
    -------
    str
        Absolute path.
    """

    if os.path.isabs(path):
        return os.path.abspath(path)

    return os.path.abspath(os.path.join(root_dir, path))


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the locale helper argument parser.

    Returns
    -------
    argparse.ArgumentParser
        Parser configured with locale maintenance actions and options.
    """

    parser = argparse.ArgumentParser(
        description='Update gettext and Babel locale files for a repository.',
    )

    parser.add_argument('--extract', action='store_true', help='Extract messages from source files.')
    parser.add_argument('--init', action='store_true', help='Initialize missing locale directories.')
    parser.add_argument('--update', action='store_true', help='Update existing locales.')
    parser.add_argument('--compile', action='store_true', help='Compile translated locales.')
    parser.add_argument(
        '--root-dir',
        help='Repository root. Defaults to GITHUB_WORKSPACE or the parent directory of this script.',
    )
    parser.add_argument('--locale-dir', default='locale', help='Locale directory, relative to root unless absolute.')
    parser.add_argument(
        '--source-dir',
        action='append',
        help='Source directory to scan. May be repeated or comma-separated. Defaults to src.',
    )
    parser.add_argument(
        '--locale',
        action='append',
        help='Locale to initialize. May be repeated or comma-separated.',
    )
    parser.add_argument(
        '--extension',
        action='append',
        help='Source file extension to scan. May be repeated or comma-separated.',
    )
    parser.add_argument(
        '--keyword',
        action='append',
        help='xgettext keyword expression. May be repeated or comma-separated.',
    )
    parser.add_argument('--project-name', help='Package/project name. Defaults to the GITHUB_REPOSITORY repo name.')
    parser.add_argument('--project-owner', help='Project owner. Defaults to GITHUB_REPOSITORY_OWNER.')
    parser.add_argument('--domain', help='Gettext domain. Defaults to the lower-case project name.')
    parser.add_argument('--bugs-address', help='msgid bugs address. Defaults to GITHUB_SERVER_URL/GITHUB_REPOSITORY.')
    parser.add_argument(
        '--language-source-url',
        default=LANGUAGES_URL,
        help='Shared languages metadata URL used by --init when --locale is not provided.',
    )

    return parser


def build_context(args: argparse.Namespace) -> LocaleContext:
    """Build a locale context from CLI arguments and GitHub runner variables.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments.

    Returns
    -------
    LocaleContext
        Resolved locale settings.
    """

    root_dir = os.path.abspath(
        args.root_dir
        or os.environ.get('GITHUB_WORKSPACE')
        or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    repository = os.environ.get('GITHUB_REPOSITORY', '')
    repository_owner = repository.split('/', 1)[0] if '/' in repository else ''
    repository_name = repository.rsplit('/', 1)[-1] if repository else os.path.basename(root_dir)

    project_name = args.project_name or repository_name
    project_owner = args.project_owner or os.environ.get('GITHUB_REPOSITORY_OWNER') or repository_owner or project_name
    domain = args.domain or project_name.lower()
    server_url = os.environ.get('GITHUB_SERVER_URL', 'https://github.com').rstrip('/')
    bugs_repository = repository or f'{project_owner}/{project_name}'
    bugs_address = args.bugs_address or f'{server_url}/{bugs_repository}'

    return LocaleContext(
        root_dir=root_dir,
        locale_dir=resolve_path(root_dir=root_dir, path=args.locale_dir),
        source_directories=split_values(args.source_dir) or DEFAULT_SOURCE_DIRECTORIES,
        extensions=split_values(args.extension) or DEFAULT_EXTENSIONS,
        keywords=split_values(args.keyword) or DEFAULT_KEYWORDS,
        project_name=project_name,
        project_owner=project_owner,
        domain=domain,
        bugs_address=bugs_address,
        language_source_url=args.language_source_url,
        target_locales=split_values(args.locale),
    )


def get_two_letter_code(language_code: str, language_info: dict[str, str]) -> str:
    """Get the two-letter code for a language metadata entry.

    Parameters
    ----------
    language_code : str
        Language key from the shared languages metadata.
    language_info : dict[str, str]
        Language metadata entry.

    Returns
    -------
    str
        Two-letter language code.
    """

    return language_info.get('two_letters_code') or language_code.split('-', 1)[0]


def get_locale_code(language_code: str, language_info: dict[str, str]) -> str:
    """Get the locale code for a language metadata entry.

    Parameters
    ----------
    language_code : str
        Language key from the shared languages metadata.
    language_info : dict[str, str]
        Language metadata entry.

    Returns
    -------
    str
        Locale code with underscores.
    """

    return language_info.get('locale_with_underscore') or language_code.replace('-', '_')


def select_default_language_index(language_entries: list[tuple[str, dict[str, str]]]) -> int | None:
    """Select the default variant for a two-letter language group.

    Parameters
    ----------
    language_entries : list[tuple[str, dict[str, str]]]
        Language metadata entries that share a two-letter code.

    Returns
    -------
    int | None
        Index of the default entry. ``None`` means the metadata has no obvious
        default variant and every entry should keep its regional code.
    """

    if len(language_entries) == 1:
        return 0

    base_indexes = [
        index
        for index, (language_code, language_info) in enumerate(language_entries)
        if get_locale_code(language_code=language_code, language_info=language_info) == (
            get_two_letter_code(language_code=language_code, language_info=language_info)
        )
    ]
    if base_indexes:
        return base_indexes[0]

    generic_indexes = [
        index
        for index, (language_code, language_info) in enumerate(language_entries)
        if ',' not in language_info.get('name', '')
    ]
    if len(generic_indexes) == 1:
        return generic_indexes[0]
    if not generic_indexes:
        return None

    return generic_indexes[0]


def parse_target_locales(language_data: dict[str, dict[str, str]]) -> list[str]:
    """Parse target locale codes from shared language metadata.

    Parameters
    ----------
    language_data : dict[str, dict[str, str]]
        Shared language metadata keyed by Crowdin language code.

    Returns
    -------
    list[str]
        Sorted locale codes parsed from shared language metadata.
    """

    language_groups = {}
    for language_code, language_info in language_data.items():
        two_letter_code = get_two_letter_code(language_code=language_code, language_info=language_info)
        language_groups.setdefault(two_letter_code, []).append((language_code, language_info))

    discovered_locales = set()
    for two_letter_code, language_entries in language_groups.items():
        default_index = select_default_language_index(language_entries=language_entries)
        discovered_locales.add(two_letter_code)
        for index, (language_code, language_info) in enumerate(language_entries):
            if index != default_index and len(language_entries) > 1:
                discovered_locales.add(get_locale_code(language_code=language_code, language_info=language_info))

    return sorted(discovered_locales)


def load_target_locales(language_source_url: str) -> list[str]:
    """Load target locales from shared language metadata.

    Parameters
    ----------
    language_source_url : str
        URL to the shared languages metadata file.

    Returns
    -------
    list[str]
        Target locale codes parsed from shared language metadata.
    """

    with urllib.request.urlopen(language_source_url, timeout=30) as response:
        language_data = json.load(response)

    return parse_target_locales(language_data=language_data)


def discover_locale_codes(locale_dir: str) -> list[str]:
    """Discover existing locale directory names.

    Parameters
    ----------
    locale_dir : str
        Directory containing locale subdirectories.

    Returns
    -------
    list[str]
        Sorted locale directory names.
    """

    if not os.path.isdir(locale_dir):
        return []

    return sorted(
        name
        for name in os.listdir(locale_dir)
        if os.path.isdir(os.path.join(locale_dir, name))
    )


def collect_source_files(root_dir: str, source_directories: list[str], extensions: list[str]) -> list[str]:
    """Collect source files that should be scanned by xgettext.

    Parameters
    ----------
    root_dir : str
        Repository root directory.
    source_directories : list[str]
        Directories to scan, relative to ``root_dir`` unless absolute.
    extensions : list[str]
        File extensions to include. Leading dots are optional.

    Returns
    -------
    list[str]
        Sorted source file paths relative to ``root_dir``.
    """

    extension_set = {extension.lstrip('.').lower() for extension in extensions}
    source_files = []

    for source_directory in source_directories:
        scan_dir = resolve_path(root_dir=root_dir, path=source_directory)
        if not os.path.isdir(scan_dir):
            continue

        for current_root, dirs, files in os.walk(scan_dir):
            dirs.sort()
            for filename in sorted(files):
                extension = filename.rsplit('.', 1)[-1].lower()
                if extension in extension_set:
                    file_path = os.path.join(current_root, filename)
                    source_files.append(os.path.relpath(file_path, root_dir))

    return sorted(source_files)


def run_command(command: list[str], root_dir: str):
    """Run a locale maintenance command from the repository root.

    Parameters
    ----------
    command : list[str]
        Command and arguments to execute.
    root_dir : str
        Working directory for the command.
    """

    print(command)
    subprocess.check_output(args=command, cwd=root_dir)


def rewrite_pot_header(context: LocaleContext, pot_filepath: str):
    """Rewrite the generated gettext template header.

    Parameters
    ----------
    context : LocaleContext
        Resolved locale settings.
    pot_filepath : str
        Path to the generated gettext template.
    """

    year = str(datetime.datetime.now().year)
    body = ''

    with open(file=pot_filepath, mode='r', encoding='utf-8') as file:
        for line in file.readlines():
            if line == '"Language: \\n"\n':
                continue

            if line == '# SOME DESCRIPTIVE TITLE.\n':
                body += f'# Translations template for {context.project_name}.\n'
            elif line.startswith('#') and ('YEAR' in line or 'PACKAGE' in line):
                body += line.replace('YEAR', year).replace('PACKAGE', context.project_name)
            else:
                body += line

    with open(file=pot_filepath, mode='w', encoding='utf-8') as file:
        file.write(body)


def x_extract(context: LocaleContext):
    """Extract gettext messages from configured source files.

    Parameters
    ----------
    context : LocaleContext
        Resolved locale settings.

    Raises
    ------
    RuntimeError
        Raised when no source files match the configured source directories
        and extensions.
    """

    pot_filepath = os.path.join(context.locale_dir, f'{context.domain}.po')
    source_files = collect_source_files(
        root_dir=context.root_dir,
        source_directories=context.source_directories,
        extensions=context.extensions,
    )
    if not source_files:
        raise RuntimeError('No source files found for locale extraction.')

    os.makedirs(context.locale_dir, exist_ok=True)
    command = [
        'xgettext',
        *[f'--keyword={keyword}' for keyword in context.keywords],
        f'--default-domain={context.domain}',
        f'--output={pot_filepath}',
        '--language=C++',
        '--boost',
        '--from-code=utf-8',
        '-F',
        f'--msgid-bugs-address={context.bugs_address}',
        f'--copyright-holder={context.project_owner}',
        f'--package-name={context.project_name}',
        '--package-version=v0',
        *source_files,
    ]

    run_command(command=command, root_dir=context.root_dir)
    if not os.path.exists(pot_filepath):
        print(f'No gettext messages found; {pot_filepath} was not generated.')
        return

    rewrite_pot_header(context=context, pot_filepath=pot_filepath)


def babel_init(context: LocaleContext, locale_code: str):
    """Initialize a locale with pybabel.

    Parameters
    ----------
    context : LocaleContext
        Resolved locale settings.
    locale_code : str
        Locale code to initialize.
    """

    command = [
        'pybabel',
        'init',
        '-i',
        os.path.join(context.locale_dir, f'{context.domain}.po'),
        '-d',
        context.locale_dir,
        '-D',
        context.domain,
        '-l',
        locale_code,
    ]
    run_command(command=command, root_dir=context.root_dir)


def babel_update(context: LocaleContext):
    """Update existing locales with pybabel.

    Parameters
    ----------
    context : LocaleContext
        Resolved locale settings.
    """

    command = [
        'pybabel',
        'update',
        '-i',
        os.path.join(context.locale_dir, f'{context.domain}.po'),
        '-d',
        context.locale_dir,
        '-D',
        context.domain,
        '--update-header-comment',
    ]
    run_command(command=command, root_dir=context.root_dir)


def babel_compile(context: LocaleContext):
    """Compile translated locales with pybabel.

    Parameters
    ----------
    context : LocaleContext
        Resolved locale settings.
    """

    command = [
        'pybabel',
        'compile',
        '-d',
        context.locale_dir,
        '-D',
        context.domain,
    ]
    run_command(command=command, root_dir=context.root_dir)


def init_missing_locales(context: LocaleContext):
    """Initialize configured locales that do not already exist.

    Parameters
    ----------
    context : LocaleContext
        Resolved locale settings.
    """

    locales = context.target_locales or load_target_locales(language_source_url=context.language_source_url)
    for locale_code in locales:
        if not os.path.isdir(os.path.join(context.locale_dir, locale_code)):
            babel_init(context=context, locale_code=locale_code)


def main(argv: list[str] | None = None):  # pragma: no cover
    """Run locale maintenance actions from the command line.

    Parameters
    ----------
    argv : list[str] | None, optional
        Command-line arguments. When omitted, ``argparse`` reads from
        ``sys.argv``.
    """

    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if not any([args.extract, args.init, args.update, args.compile]):
        parser.error('Specify at least one action: --extract, --init, --update, or --compile.')

    context = build_context(args=args)
    if args.extract:
        x_extract(context=context)
    if args.init:
        init_missing_locales(context=context)
    if args.update:
        babel_update(context=context)
    if args.compile:
        babel_compile(context=context)


if __name__ == '__main__':
    main()
