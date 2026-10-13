import assert from 'node:assert/strict';
import {
  mkdtemp,
  mkdir,
  readFile,
  readdir,
  rm,
  writeFile,
} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { runInNewContext } from 'node:vm';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const executable = path.join(projectRoot, 'bin', 'dockle-jsdoc.cjs');
const packageMetadata = JSON.parse(
  await readFile(path.join(projectRoot, 'package.json'), 'utf8'),
);

test('the packaged highlighter includes every built-in grammar', async () => {
  const source = await readFile(
    path.join(
      projectRoot,
      'src',
      'dockle',
      'sphinx',
      'themes',
      'dockle',
      'static',
      'highlight.min.js',
    ),
    'utf8',
  );
  const context = { console };
  context.globalThis = context;
  context.window = context;
  runInNewContext(source, context);

  const packagedLanguages = (await readdir(path.join(
    projectRoot,
    'node_modules',
    '@highlightjs',
    'cdn-assets',
    'languages',
  ))).filter((filename) => filename.endsWith('.min.js'));
  assert.equal(context.hljs.listLanguages().length, packagedLanguages.length);
  const fixtureLanguages = new Set((await readdir(path.join(
    projectRoot,
    'third-party',
    'highlight.js',
    'test',
    'markup',
  ), { withFileTypes: true }))
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name));
  for (const language of context.hljs.listLanguages()) {
    assert.ok(fixtureLanguages.has(language), language);
  }
  const languageCollator = new Intl.Collator('en', {
    ignorePunctuation: true,
    numeric: true,
    sensitivity: 'base',
  });
  const expectedLanguageOrder = [...context.hljs.listLanguages()]
    .sort((left, right) => (
      languageCollator.compare(
        context.hljs.getLanguage(left).name || left,
        context.hljs.getLanguage(right).name || right,
      ) || languageCollator.compare(left, right)
    ));
  for (const reference of [
    path.join('.dockle', 'example-sources', 'sphinx', 'component-reference.md'),
    path.join('.dockle', 'example-sources', 'sphinx', 'component-reference-rst.rst'),
    path.join('.dockle', 'example-sources', 'doxygen', 'component-reference.md'),
    path.join('.dockle', 'example-sources', 'mkdocs', 'component-reference.md'),
    path.join('.dockle', 'example-sources', 'jsdoc', 'tutorials', 'component-reference.md'),
    path.join('.dockle', 'example-sources', 'rustdoc', 'component-reference.md'),
  ]) {
    const document = await readFile(path.join(projectRoot, reference), 'utf8');
    assert.equal(
      document.match(/class="dockle-language-gallery-header"/g)?.length,
      packagedLanguages.length,
      reference,
    );
    assert.equal(
      document.match(/<h3 id="language-[^"]+" class="dockle-language-gallery-header">/g)?.length,
      packagedLanguages.length,
      reference,
    );
    const renderedLanguageOrder = [...document.matchAll(
      /<h3 id="language-([^"]+)" class="dockle-language-gallery-header">/g,
    )].map((match) => match[1]);
    assert.deepEqual(renderedLanguageOrder, expectedLanguageOrder, reference);
    assert.doesNotMatch(document, /# Dockle \S+ syntax preview/);
  }
  for (const language of [
    'cmake',
    'console',
    'dockerfile',
    'markdown',
    'powershell',
    'rust',
    'shell',
    'toml',
    'typescript',
    'yaml',
  ]) {
    assert.ok(context.hljs.getLanguage(language), language);
  }
});

test('the npm command builds a self-contained native JSDoc site', async (context) => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'dockle-jsdoc-'));
  context.after(() => rm(root, { force: true, recursive: true }));
  const source = path.join(root, 'src');
  const output = path.join(root, 'site');
  const tutorials = path.join(root, 'tutorials');
  await mkdir(source);
  await mkdir(tutorials);
  await writeFile(path.join(root, 'package.json'), JSON.stringify({
    name: 'native-jsdoc-example',
    repository: 'https://example.invalid/native-jsdoc-example',
    version: '1.2.3',
  }));
  await writeFile(path.join(root, 'logo.svg'), '<svg xmlns="http://www.w3.org/2000/svg"/>');
  await writeFile(path.join(root, 'favicon.svg'), '<svg xmlns="http://www.w3.org/2000/svg"/>');
  await writeFile(path.join(root, 'project.css'), 'body {}');
  await writeFile(path.join(root, 'project.js'), 'void 0;');
  await writeFile(
    path.join(tutorials, 'component-reference.md'),
    '# Component reference\n',
  );
  await writeFile(path.join(tutorials, 'tutorials.json'), JSON.stringify({
    'component-reference': { title: 'Component reference' },
  }));
  await writeFile(path.join(source, 'example.js'), `/**
 * Add two values.
 * @param {number} left Left value.
 * @param {number} right Right value.
 * @returns {number} Their sum.
 */
export function add(left, right) { return left + right; }
`);
  const configuration = path.join(root, 'jsdoc.json');
  await writeFile(configuration, JSON.stringify({
    opts: {
      destination: output,
      recurse: true,
      tutorials,
    },
    source: {
      include: [source],
    },
    templates: {
      dockle: {
        favicon: 'favicon.svg',
        extraJavascript: [
          'project.js',
          'https://example.invalid/widget.js',
        ],
        extraStylesheets: [
          'project.css',
          'https://example.invalid/widget.css',
        ],
        logo: 'logo.svg',
        targetTitle: 'Native JSDoc example',
      },
    },
  }));

  const result = spawnSync(
    process.execPath,
    [executable, '--configure', configuration, '--pedantic'],
    { cwd: root, encoding: 'utf8' },
  );
  assert.equal(result.status, 0, result.stderr || result.stdout);

  const document = await readFile(path.join(output, 'index.html'), 'utf8');
  const search = JSON.parse(await readFile(path.join(output, 'search.json'), 'utf8'));
  const searchPage = await readFile(path.join(output, 'dockle-search.html'), 'utf8');
  assert.match(document, /data-dockle-framework="jsdoc"/);
  assert.match(document, /data-dockle-theme="jsdoc"/);
  assert.match(document, /native-jsdoc-example/);
  assert.match(document, /https:\/\/example\.invalid\/native-jsdoc-example/);
  assert.match(document, /data-dockle-repository-action/);
  assert.match(document, /data-dockle-repository-service="generic"/);
  assert.match(document, /data-lucide="sun-moon"/);
  assert.ok(
    document.indexOf('dockle-repository-link')
      < document.indexOf('data-dockle-theme-toggle'),
  );
  assert.match(document, /target="_blank"/);
  assert.match(document, /rel="noopener noreferrer"/);
  assert.ok(document.includes(`Dockle ${packageMetadata.version}`));
  assert.match(document, /JSDoc 4\.0\.5/);
  assert.match(document, /dockle-logo\.svg/);
  assert.match(document, /dockle-favicon\.svg/);
  assert.match(
    document,
    /href="project\.css" data-dockle-extra-stylesheet="0"/,
  );
  assert.match(document, /href="https:\/\/example\.invalid\/widget\.css"/);
  assert.match(
    document,
    /src="project\.js" data-dockle-extra-javascript="0"/,
  );
  assert.match(document, /src="https:\/\/example\.invalid\/widget\.js"/);
  assert.match(document, />Component reference<\/a>/);
  assert.doesNotMatch(document, />component-reference<\/a>/);
  assert.match(
    document,
    /pre\.prettyprint:not\(\.source\.linenums\)/,
  );
  assert.match(document, /classList\.remove\("prettyprint", "source"\)/);
  assert.doesNotMatch(document, /data-dockle-home/);
  assert.ok(search.docs.some((entry) => entry.text.includes('Add two values')));
  assert.ok(!search.docs.some((entry) => entry.location === 'dockle-search.html'));
  assert.ok(search.docs.every((entry) => !entry.text.includes('Search documentation')));
  assert.ok(search.docs.every((entry) => !entry.text.includes('Generated by')));
  assert.match(document, /action="dockle-search\.html" method="get"/);
  assert.match(document, /name="readthedocs-addons-api-version"/);
  assert.match(searchPage, /data-dockle-search-page/);
  assert.match(searchPage, /data-dockle-search="search\.json"/);
  assert.match(searchPage, /data-dockle-logo-url="dockle-logo\.svg"/);
  assert.match(searchPage, /rel="icon" href="dockle-favicon\.svg" data-dockle-favicon/);
  assert.match(searchPage, /href="project\.css" data-dockle-extra-stylesheet="0"/);
  assert.match(searchPage, /src="project\.js" data-dockle-extra-javascript="0"/);
  await readFile(path.join(output, 'dockle.css'), 'utf8');
  await readFile(path.join(output, 'dockle.js'), 'utf8');
  await readFile(path.join(output, 'highlight.min.js'), 'utf8');
  await readFile(path.join(output, 'lucide.min.js'), 'utf8');
  assert.equal(await readFile(path.join(output, 'project.css'), 'utf8'), 'body {}');
  assert.equal(await readFile(path.join(output, 'project.js'), 'utf8'), 'void 0;');
});
