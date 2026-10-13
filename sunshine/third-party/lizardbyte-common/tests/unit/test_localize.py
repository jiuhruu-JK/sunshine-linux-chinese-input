"""Tests for the shared locale maintenance helper."""

# standard imports
import datetime
import os

# lib imports
import pytest

# local imports
import scripts.localize as localize


@pytest.fixture
def clean_github_environment(monkeypatch):
    """Remove GitHub runner variables that affect locale context defaults."""

    for variable in [
        'GITHUB_REPOSITORY',
        'GITHUB_REPOSITORY_OWNER',
        'GITHUB_SERVER_URL',
    ]:
        monkeypatch.delenv(variable, raising=False)


def parse_args(*args):
    """Parse locale helper arguments for tests.

    Parameters
    ----------
    *args : str
        Command-line arguments to parse.

    Returns
    -------
    argparse.Namespace
        Parsed arguments.
    """

    return localize.build_arg_parser().parse_args(args)


def test_build_context_uses_github_defaults(monkeypatch, tmp_path):
    """Verify context defaults come from GitHub runner environment variables."""

    monkeypatch.setenv('GITHUB_WORKSPACE', str(tmp_path))
    monkeypatch.setenv('GITHUB_REPOSITORY', 'LizardByte/Example-Repo')
    monkeypatch.setenv('GITHUB_REPOSITORY_OWNER', 'LizardByte')
    monkeypatch.setenv('GITHUB_SERVER_URL', 'https://github.example')
    monkeypatch.setenv('GITHUB_REF_NAME', 'master')

    context = localize.build_context(args=parse_args())

    assert context.root_dir == str(tmp_path)
    assert context.locale_dir == os.path.join(str(tmp_path), 'locale')
    assert context.source_directories == ['src']
    assert context.extensions == localize.DEFAULT_EXTENSIONS
    assert context.keywords == localize.DEFAULT_KEYWORDS
    assert context.project_name == 'Example-Repo'
    assert context.project_owner == 'LizardByte'
    assert context.domain == 'example-repo'
    assert context.bugs_address == 'https://github.example/LizardByte/Example-Repo'
    assert context.language_source_url == localize.LANGUAGES_URL
    assert context.target_locales == []


def test_build_context_allows_cli_overrides(monkeypatch, tmp_path):
    """Verify CLI options override GitHub and fallback defaults."""

    monkeypatch.delenv('GITHUB_WORKSPACE', raising=False)
    monkeypatch.delenv('GITHUB_REPOSITORY', raising=False)
    monkeypatch.delenv('GITHUB_REPOSITORY_OWNER', raising=False)
    monkeypatch.delenv('GITHUB_REF_NAME', raising=False)
    args = parse_args(
        '--root-dir',
        str(tmp_path),
        '--locale-dir',
        'i18n',
        '--source-dir',
        'src,lib',
        '--source-dir',
        'tests',
        '--locale',
        'en,de',
        '--locale',
        'fr',
        '--extension',
        '.cpp,hpp',
        '--keyword',
        'gettext:1',
        '--project-name',
        'Shared',
        '--project-owner',
        'Example',
        '--domain',
        'shared-domain',
        '--bugs-address',
        'https://bugs.example/shared',
        '--language-source-url',
        'https://example.invalid/languages.json',
    )

    context = localize.build_context(args=args)

    assert context.root_dir == str(tmp_path)
    assert context.locale_dir == os.path.join(str(tmp_path), 'i18n')
    assert context.source_directories == ['src', 'lib', 'tests']
    assert context.target_locales == ['en', 'de', 'fr']
    assert context.extensions == ['.cpp', 'hpp']
    assert context.keywords == ['gettext:1']
    assert context.project_name == 'Shared'
    assert context.project_owner == 'Example'
    assert context.domain == 'shared-domain'
    assert context.bugs_address == 'https://bugs.example/shared'
    assert context.language_source_url == 'https://example.invalid/languages.json'


def test_parse_target_locales_normalizes_i18n_metadata():
    """Verify shared language metadata maps to Sunshine-style locale codes."""

    language_data = {
        'bg': {
            'locale_with_underscore': 'bg_BG',
            'two_letters_code': 'bg',
        },
        'cs': {
            'locale_with_underscore': 'cs_CZ',
            'two_letters_code': 'cs',
        },
        'de': {
            'locale_with_underscore': 'de_DE',
            'two_letters_code': 'de',
        },
        'en-GB': {
            'name': 'English, United Kingdom',
            'locale_with_underscore': 'en_GB',
            'two_letters_code': 'en',
        },
        'en-US': {
            'name': 'English, United States',
            'locale_with_underscore': 'en_US',
            'two_letters_code': 'en',
        },
        'es-ES': {
            'locale_with_underscore': 'es_ES',
            'two_letters_code': 'es',
        },
        'fr': {
            'locale_with_underscore': 'fr_FR',
            'two_letters_code': 'fr',
        },
        'hu': {
            'locale_with_underscore': 'hu_HU',
            'two_letters_code': 'hu',
        },
        'it': {
            'locale_with_underscore': 'it_IT',
            'two_letters_code': 'it',
        },
        'ja': {
            'locale_with_underscore': 'ja_JP',
            'two_letters_code': 'ja',
        },
        'ko': {
            'locale_with_underscore': 'ko_KR',
            'two_letters_code': 'ko',
        },
        'pl': {
            'locale_with_underscore': 'pl_PL',
            'two_letters_code': 'pl',
        },
        'pt-BR': {
            'name': 'Portuguese, Brazilian',
            'locale_with_underscore': 'pt_BR',
            'two_letters_code': 'pt',
        },
        'pt-PT': {
            'name': 'Portuguese',
            'locale_with_underscore': 'pt_PT',
            'two_letters_code': 'pt',
        },
        'ru': {
            'locale_with_underscore': 'ru_RU',
            'two_letters_code': 'ru',
        },
        'sv-SE': {
            'locale_with_underscore': 'sv_SE',
            'two_letters_code': 'sv',
        },
        'tr': {
            'locale_with_underscore': 'tr_TR',
            'two_letters_code': 'tr',
        },
        'uk': {
            'locale_with_underscore': 'uk_UA',
            'two_letters_code': 'uk',
        },
        'vi': {
            'locale_with_underscore': 'vi_VN',
            'two_letters_code': 'vi',
        },
        'zh-CN': {
            'name': 'Chinese Simplified',
            'locale_with_underscore': 'zh_CN',
            'two_letters_code': 'zh',
        },
        'zh-TW': {
            'name': 'Chinese Traditional',
            'locale_with_underscore': 'zh_TW',
            'two_letters_code': 'zh',
        },
    }

    assert localize.parse_target_locales(language_data=language_data) == [
        'bg',
        'cs',
        'de',
        'en',
        'en_GB',
        'en_US',
        'es',
        'fr',
        'hu',
        'it',
        'ja',
        'ko',
        'pl',
        'pt',
        'pt_BR',
        'ru',
        'sv',
        'tr',
        'uk',
        'vi',
        'zh',
        'zh_TW',
    ]


def test_parse_target_locales_handles_missing_optional_metadata():
    """Verify language codes fall back to source keys when metadata is sparse."""

    language_data = {
        'aa-AA': {
            'name': 'Afar, Regional',
        },
        'aa-BB': {
            'name': 'Afar, Alternate',
        },
        'bb': {
            'locale_with_underscore': 'bb',
            'two_letters_code': 'bb',
        },
        'bb-BB': {
            'locale_with_underscore': 'bb_BB',
            'two_letters_code': 'bb',
        },
    }

    assert localize.parse_target_locales(language_data=language_data) == [
        'aa',
        'aa_AA',
        'aa_BB',
        'bb',
        'bb_BB',
    ]


def test_load_target_locales_uses_shared_language_metadata(monkeypatch):
    """Verify target locales load from the shared languages URL."""

    class FakeResponse:
        """Fake urlopen response for language metadata."""

        def __enter__(self):
            """Enter the context manager.

            Returns
            -------
            FakeResponse
                Active fake response.
            """

            return self

        def __exit__(self, exc_type, exc_value, traceback):
            """Exit the context manager."""

        def read(self):
            """Read fake JSON response bytes.

            Returns
            -------
            bytes
                Encoded language metadata.
            """

            return (
                b'{"pt-PT": {"name": "Portuguese", "locale_with_underscore": "pt_PT", '
                b'"two_letters_code": "pt"}, "pt-BR": {"name": "Portuguese, Brazilian", '
                b'"locale_with_underscore": "pt_BR", "two_letters_code": "pt"}}'
            )

    def fake_urlopen(url, timeout):
        """Return fake shared language metadata."""

        assert url == 'https://example.invalid/languages.json'
        assert timeout == 30
        return FakeResponse()

    monkeypatch.setattr(localize.urllib.request, 'urlopen', fake_urlopen)

    assert localize.load_target_locales(
        language_source_url='https://example.invalid/languages.json',
    ) == ['pt', 'pt_BR']


def test_load_target_locales_propagates_source_errors(monkeypatch):
    """Verify failed language metadata loads raise the source error."""

    def fake_urlopen(url, timeout):
        """Raise an error while loading language metadata."""

        raise OSError('offline')

    monkeypatch.setattr(localize.urllib.request, 'urlopen', fake_urlopen)

    try:
        localize.load_target_locales(language_source_url='https://example.invalid/languages.json')
    except OSError as err:
        assert str(err) == 'offline'
    else:
        raise AssertionError('Expected language metadata source errors to propagate')


def test_resolve_path_handles_absolute_and_relative_paths(tmp_path):
    """Verify path resolution handles absolute and relative paths."""

    assert localize.resolve_path(root_dir=str(tmp_path), path='locale') == os.path.join(str(tmp_path), 'locale')
    assert localize.resolve_path(root_dir='ignored', path=str(tmp_path)) == str(tmp_path)


def test_discover_locale_codes_returns_sorted_directories(tmp_path):
    """Verify locale discovery returns sorted directory names only."""

    os.makedirs(os.path.join(str(tmp_path), 'fr'))
    os.makedirs(os.path.join(str(tmp_path), 'en'))
    with open(os.path.join(str(tmp_path), 'README.md'), mode='w', encoding='utf-8') as file:
        file.write('not a locale directory')

    assert localize.discover_locale_codes(locale_dir=str(tmp_path)) == ['en', 'fr']
    assert localize.discover_locale_codes(locale_dir=os.path.join(str(tmp_path), 'missing')) == []


def test_collect_source_files_scans_existing_source_directories(tmp_path):
    """Verify source discovery filters files by configured roots and extensions."""

    root_dir = str(tmp_path)
    files = [
        os.path.join(root_dir, 'src', 'main.cpp'),
        os.path.join(root_dir, 'src', 'include', 'app.hpp'),
        os.path.join(root_dir, 'lib', 'ignored.cpp'),
        os.path.join(root_dir, 'src', 'notes.txt'),
    ]
    for file in files:
        os.makedirs(os.path.dirname(file), exist_ok=True)
        with open(file, mode='w', encoding='utf-8') as file_handle:
            file_handle.write('// test\n')

    assert localize.collect_source_files(
        root_dir=root_dir,
        source_directories=['src', 'missing'],
        extensions=['cpp', '.hpp'],
    ) == [
        os.path.join('src', 'include', 'app.hpp'),
        os.path.join('src', 'main.cpp'),
    ]


def test_x_extract_builds_command_and_rewrites_header(clean_github_environment, monkeypatch, tmp_path):
    """Verify xgettext extraction builds command arguments and rewrites headers."""

    root_dir = str(tmp_path)
    os.makedirs(os.path.join(root_dir, 'src', 'nested'))
    with open(os.path.join(root_dir, 'src', 'main.cpp'), mode='w', encoding='utf-8') as file:
        file.write('translate("Hello")\n')
    with open(os.path.join(root_dir, 'src', 'nested', 'helper.hpp'), mode='w', encoding='utf-8') as file:
        file.write('gettext("World")\n')

    context = localize.build_context(args=parse_args('--root-dir', root_dir, '--project-name', 'Example'))
    calls = []

    def fake_check_output(args, cwd):
        """Record xgettext calls and write a temporary template."""

        calls.append({
            'args': args,
            'cwd': cwd,
        })
        with open(os.path.join(context.locale_dir, 'example.po'), mode='w', encoding='utf-8') as file:
            file.write('# SOME DESCRIPTIVE TITLE.\n')
            file.write('# Copyright (C) YEAR PACKAGE\n')
            file.write('"Language: \\n"\n')
            file.write('msgid ""\n')

    monkeypatch.setattr(localize.subprocess, 'check_output', fake_check_output)

    localize.x_extract(context=context)

    current_year = str(datetime.datetime.now().year)
    assert calls == [
        {
            'args': [
                'xgettext',
                *[f'--keyword={keyword}' for keyword in localize.DEFAULT_KEYWORDS],
                '--default-domain=example',
                f'--output={os.path.join(context.locale_dir, "example.po")}',
                '--language=C++',
                '--boost',
                '--from-code=utf-8',
                '-F',
                '--msgid-bugs-address=https://github.com/Example/Example',
                '--copyright-holder=Example',
                '--package-name=Example',
                '--package-version=v0',
                os.path.join('src', 'main.cpp'),
                os.path.join('src', 'nested', 'helper.hpp'),
            ],
            'cwd': root_dir,
        },
    ]
    with open(os.path.join(context.locale_dir, 'example.po'), mode='r', encoding='utf-8') as file:
        assert file.read() == (
            '# Translations template for Example.\n'
            f'# Copyright (C) {current_year} Example\n'
            'msgid ""\n'
        )


def test_x_extract_allows_empty_extraction(clean_github_environment, monkeypatch, tmp_path):
    """Verify extraction succeeds when xgettext has no messages to write."""

    root_dir = str(tmp_path)
    os.makedirs(os.path.join(root_dir, 'src'))
    with open(os.path.join(root_dir, 'src', 'main.cpp'), mode='w', encoding='utf-8') as file:
        file.write('int main() { return 0; }\n')

    context = localize.build_context(args=parse_args('--root-dir', root_dir, '--project-name', 'Example'))
    calls = []

    def fake_check_output(args, cwd):
        """Record xgettext calls without creating a template file."""

        calls.append({
            'args': args,
            'cwd': cwd,
        })

    monkeypatch.setattr(localize.subprocess, 'check_output', fake_check_output)

    localize.x_extract(context=context)

    assert calls == [
        {
            'args': [
                'xgettext',
                *[f'--keyword={keyword}' for keyword in localize.DEFAULT_KEYWORDS],
                '--default-domain=example',
                f'--output={os.path.join(context.locale_dir, "example.po")}',
                '--language=C++',
                '--boost',
                '--from-code=utf-8',
                '-F',
                '--msgid-bugs-address=https://github.com/Example/Example',
                '--copyright-holder=Example',
                '--package-name=Example',
                '--package-version=v0',
                os.path.join('src', 'main.cpp'),
            ],
            'cwd': root_dir,
        },
    ]
    assert os.path.isdir(context.locale_dir)
    assert not os.path.exists(os.path.join(context.locale_dir, 'example.po'))


def test_x_extract_requires_source_files(tmp_path):
    """Verify extraction fails clearly when no source files are found."""

    context = localize.build_context(args=parse_args('--root-dir', str(tmp_path)))

    try:
        localize.x_extract(context=context)
    except RuntimeError as err:
        assert str(err) == 'No source files found for locale extraction.'
    else:
        raise AssertionError('Expected locale extraction to require source files')


def test_babel_commands(monkeypatch, tmp_path):
    """Verify pybabel commands use the resolved locale context."""

    context = localize.build_context(args=parse_args('--root-dir', str(tmp_path), '--project-name', 'Example'))
    calls = []

    def fake_check_output(args, cwd):
        """Record pybabel calls."""

        calls.append({
            'args': args,
            'cwd': cwd,
        })

    monkeypatch.setattr(localize.subprocess, 'check_output', fake_check_output)

    localize.babel_init(context=context, locale_code='fr')
    localize.babel_update(context=context)
    localize.babel_compile(context=context)

    assert calls == [
        {
            'args': [
                'pybabel',
                'init',
                '-i',
                os.path.join(context.locale_dir, 'example.po'),
                '-d',
                context.locale_dir,
                '-D',
                'example',
                '-l',
                'fr',
            ],
            'cwd': str(tmp_path),
        },
        {
            'args': [
                'pybabel',
                'update',
                '-i',
                os.path.join(context.locale_dir, 'example.po'),
                '-d',
                context.locale_dir,
                '-D',
                'example',
                '--update-header-comment',
            ],
            'cwd': str(tmp_path),
        },
        {
            'args': [
                'pybabel',
                'compile',
                '-d',
                context.locale_dir,
                '-D',
                'example',
            ],
            'cwd': str(tmp_path),
        },
    ]


def test_init_missing_locales_only_initializes_missing_targets(monkeypatch, tmp_path):
    """Verify locale initialization skips existing targets."""

    context = localize.build_context(args=parse_args('--root-dir', str(tmp_path), '--locale', 'en,fr'))
    os.makedirs(os.path.join(context.locale_dir, 'en'))
    initialized_locales = []

    def fake_babel_init(context, locale_code):
        """Record initialized locale codes."""

        initialized_locales.append(locale_code)

    monkeypatch.setattr(localize, 'babel_init', fake_babel_init)

    localize.init_missing_locales(context=context)

    assert initialized_locales == ['fr']


def test_init_missing_locales_loads_shared_targets(monkeypatch, tmp_path):
    """Verify locale initialization loads shared targets when none are explicit."""

    context = localize.build_context(args=parse_args('--root-dir', str(tmp_path)))
    os.makedirs(os.path.join(context.locale_dir, 'en'))
    initialized_locales = []

    def fake_load_target_locales(language_source_url):
        """Return fake shared target locales."""

        assert language_source_url == localize.LANGUAGES_URL
        return ['en', 'vi']

    def fake_babel_init(context, locale_code):
        """Record initialized locale codes."""

        initialized_locales.append(locale_code)

    monkeypatch.setattr(localize, 'load_target_locales', fake_load_target_locales)
    monkeypatch.setattr(localize, 'babel_init', fake_babel_init)

    localize.init_missing_locales(context=context)

    assert initialized_locales == ['vi']
