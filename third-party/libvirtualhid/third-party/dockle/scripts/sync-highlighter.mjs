import { mkdir, readFile, readdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const manifest = JSON.parse(await readFile(path.join(root, 'package.json'), 'utf8'));
const version = manifest.devDependencies['@highlightjs/cdn-assets'];
const highlighterRoot = path.join(
  root,
  'node_modules',
  '@highlightjs',
  'cdn-assets',
);
const languagesRoot = path.join(highlighterRoot, 'languages');
const staticRoot = path.join(
  root,
  'src',
  'dockle',
  'sphinx',
  'themes',
  'dockle',
  'static',
);

const core = await readFile(path.join(highlighterRoot, 'highlight.min.js'), 'utf8');
const languageFiles = (await readdir(languagesRoot, { withFileTypes: true }))
  .filter((entry) => entry.isFile() && entry.name.endsWith('.min.js'))
  .map((entry) => entry.name)
  .sort((left, right) => left.localeCompare(right));
const languages = await Promise.all(
  languageFiles.map((filename) => readFile(path.join(languagesRoot, filename), 'utf8')),
);
const license = await readFile(path.join(highlighterRoot, 'LICENSE'), 'utf8');
const banner = `/*! Highlight.js ${version} | BSD-3-Clause | https://highlightjs.org/ */`;

await mkdir(staticRoot, { recursive: true });
await writeFile(
  path.join(staticRoot, 'highlight.min.js'),
  `${[banner, core.trimEnd(), ...languages.map((source) => source.trimEnd())].join('\n')}\n`,
);
await writeFile(path.join(staticRoot, 'HIGHLIGHT_LICENSE.txt'), license);
