import {
  cp,
  mkdir,
  readFile,
  readdir,
  rm,
  writeFile,
} from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { runInNewContext } from 'node:vm';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const examplesRoot = path.join(root, 'examples');
const stagedExamplesRoot = path.join(root, '.dockle', 'example-sources');
const runtimePath = path.join(
  root,
  'src',
  'dockle',
  'sphinx',
  'themes',
  'dockle',
  'static',
  'highlight.min.js',
);
const fixtureRoot = path.join(
  root,
  'third-party',
  'highlight.js',
  'test',
  'markup',
);
const commonPath = path.join(
  examplesRoot,
  'shared',
  'component-reference.md.inc',
);
const targets = [
  {
    framework: 'sphinx',
    output: 'component-reference.md',
    specific: path.join(examplesRoot, 'sphinx', 'component-reference.md.inc'),
    useNeutralFence: true,
  },
  {
    framework: 'doxygen',
    output: 'component-reference.md',
    specific: path.join(examplesRoot, 'doxygen', 'component-reference.md.inc'),
  },
  {
    framework: 'mkdocs',
    output: 'component-reference.md',
    specific: path.join(examplesRoot, 'mkdocs', 'component-reference.md.inc'),
  },
  {
    framework: 'jsdoc',
    output: path.join('tutorials', 'component-reference.md'),
  },
  {
    framework: 'rustdoc',
    output: 'component-reference.md',
  },
];

const samples = new Map([
  ['bash', '# Build one target.\ntarget=api\npython -m dockle build "$target"'],
  ['c', '/* Build one target. */\nconst char *target = "api";\nreturn target != 0;'],
  ['cpp', '// Build one target.\nconst std::string target{"api"};\nreturn !target.empty();'],
  ['css', '/* Share the project accent. */\n:root {\n  --dockle-primary: #2962ff;\n}'],
  ['diff', '- framework = "native"\n+ framework = "dockle"'],
  ['dockerfile', 'FROM python:3.13\nRUN pip install dockle\nCMD ["dockle", "build"]'],
  ['http', 'GET /api/ HTTP/1.1\nHost: docs.example.com\nAccept: text/html'],
  ['ini', '[project]\nname=dockle\nenabled=true'],
  ['javascript', '// Build one target.\nconst target = "api";\nconst enabled = target !== "disabled";'],
  ['json', '{\n  "target": "api",\n  "enabled": true\n}'],
  ['makefile', 'target := api\n\nbuild:\n\tdockle build $(target)'],
  ['markdown', '# Dockle\n\nBuild **consistent** documentation with `dockle build`.'],
  ['plaintext', 'Dockle syntax preview\ntarget: api\nenabled: true'],
  ['powershell', '# Build one target.\n$target = "api"\ndockle build $target'],
  ['python', '# Build one target.\ntarget = "api"\nenabled = target != "disabled"'],
  ['rust', '// Build one target.\nlet target = "api";\nlet enabled = target != "disabled";'],
  ['scss', '// Share the project accent.\n$dockle-primary: #2962ff;\n.docs { color: $dockle-primary; }'],
  ['sql', '-- Find one target.\nSELECT name, framework\nFROM targets\nWHERE enabled = TRUE;'],
  ['toml', '# Configure one target.\n[[targets]]\nname = "api"\nenabled = true'],
  ['typescript', '// Build one target.\nconst target: string = "api";\nconst enabled: boolean = true;'],
  ['xml', '<!-- Link to generated documentation. -->\n<nav enabled="true">\n  <a href="/api/">API</a>\n</nav>'],
  ['yaml', '# Configure one target.\ntarget:\n  name: api\n  enabled: true'],
]);

const escapeHtml = (value) => value
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;');

const sampleExcerpt = (source) => {
  const normalized = source.replaceAll('\r\n', '\n').trim();
  if (normalized.length <= 900) {
    return normalized;
  }

  const selected = [];
  let length = 0;
  for (const line of normalized.split('\n')) {
    const addition = line.length + (selected.length ? 1 : 0);
    if (selected.length && (selected.length >= 18 || length + addition > 900)) {
      break;
    }
    selected.push(line.slice(0, 900));
    length += Math.min(addition, 900);
  }
  return selected.join('\n').trimEnd();
};

const fixturePreference = (filename) => ({
  'sample.txt': 4,
  'default.txt': 3,
  'keywords.txt': 2,
  'builtins.txt': 1,
}[filename] || 0);

const selectLanguagePreview = async (highlighter, language) => {
  const directory = path.join(fixtureRoot, language);
  const fixtureFiles = (await readdir(directory, { withFileTypes: true }))
    .filter((entry) => (
      entry.isFile()
      && entry.name.endsWith('.txt')
      && !entry.name.endsWith('.expect.txt')
    ));
  const candidates = await Promise.all(fixtureFiles.map(async (entry) => ({
    filename: entry.name,
    source: sampleExcerpt(await readFile(path.join(directory, entry.name), 'utf8')),
  })));
  const curated = samples.get(language);
  if (curated) {
    candidates.push({ filename: 'dockle.txt', source: curated });
  }

  let selected;
  for (const candidate of candidates) {
    if (!candidate.source) {
      continue;
    }
    const result = highlighter.highlight(candidate.source, {
      language,
      ignoreIllegals: true,
    });
    const tokens = result.value.match(/class="hljs-[^"]+"/g) || [];
    if (language !== 'plaintext' && !tokens.length) {
      continue;
    }
    const distinctTokens = new Set(tokens).size;
    const preference = candidate.filename === 'dockle.txt'
      ? 5
      : fixturePreference(candidate.filename);
    const score = (
      distinctTokens * 10000
      + tokens.length * 100
      + result.relevance * 10
      + preference
    );
    if (!selected || score > selected.score) {
      selected = { ...candidate, score };
    }
  }
  if (!selected) {
    throw new Error(`no highlighting fixture produced tokens for ${language}`);
  }
  return selected.source;
};

const runtime = await readFile(runtimePath, 'utf8');
const context = { console };
context.globalThis = context;
context.window = context;
// The generated asset comes from the pinned dependency, not user input.
runInNewContext(runtime, context); // NOSONAR (javascript:S1523): trusted Highlight.js asset.

const languageCollator = new Intl.Collator('en', {
  ignorePunctuation: true,
  numeric: true,
  sensitivity: 'base',
});
const languageDisplayName = (language) => (
  context.hljs.getLanguage(language).name || language
);
const languages = [...context.hljs.listLanguages()]
  .sort((left, right) => (
    languageCollator.compare(
      languageDisplayName(left),
      languageDisplayName(right),
    ) || languageCollator.compare(left, right)
  ));
const previews = new Map(await Promise.all(languages.map(async (language) => [
  language,
  await selectLanguagePreview(context.hljs, language),
])));
const languagePreview = (language) => previews.get(language);
const markdownLanguageEntries = (useNeutralFence) => languages.map((language) => {
  const definition = context.hljs.getLanguage(language);
  const aliases = definition.aliases || [];
  const preview = languagePreview(language);
  const backtickRuns = preview.match(/`+/g) || [];
  const fenceLength = Math.max(
    3,
    ...backtickRuns.map((run) => run.length + 1),
  );
  const fence = '`'.repeat(fenceLength);
  const aliasMarkup = aliases.length
    ? `<span>Aliases: ${aliases.map(escapeHtml).join(', ')}</span>`
    : '';
  return [
    `<h3 id="language-${escapeHtml(language)}" class="dockle-language-gallery-header">`,
    `<strong>${escapeHtml(definition.name || language)}</strong>`,
    `<code>${escapeHtml(language)}</code>`,
    ...(aliasMarkup ? [aliasMarkup] : []),
    '</h3>',
    '',
    `${fence}${useNeutralFence ? 'text' : language}`,
    preview,
    fence,
  ].join('\n');
});

const markdownLanguageReference = (useNeutralFence) => [
  '## Language highlighting',
  '',
  'Every entry below is an actual fenced code block processed by this documentation',
  'framework before Dockle applies the shared highlighter. The list contains every',
  'canonical grammar bundled by the pinned Highlight.js dependency; aliases are',
  'shown beside the authoring identifier and are included by the filter. Each snippet',
  'is selected from that version\'s matching Highlight.js test fixtures.',
  '',
  '<div class="dockle-language-gallery"></div>',
  '',
  ...markdownLanguageEntries(useNeutralFence)
    .flatMap((entry) => [entry, '']),
  '<div class="dockle-language-gallery-end"></div>',
].join('\n');

const rstLanguageEntries = languages.map((language) => {
  const definition = context.hljs.getLanguage(language);
  const aliases = definition.aliases || [];
  const aliasesText = aliases.length
    ? ` <span>Aliases: ${aliases.map(escapeHtml).join(', ')}</span>`
    : '';
  const header = [
    `<h3 id="language-${escapeHtml(language)}" class="dockle-language-gallery-header">`,
    `<strong>${escapeHtml(definition.name || language)}</strong> `,
    `<code>${escapeHtml(language)}</code>`,
    aliasesText,
    '</h3>',
  ].join('');
  const preview = languagePreview(language)
    .split('\n')
    .map((line) => `   ${line}`)
    .join('\n');
  return [
    '.. raw:: html',
    '',
    `   ${header}`,
    '',
    '.. code-block:: text',
    `   :class: language-${language}`,
    '',
    preview,
  ].join('\n');
});

const rstLanguageReference = [
  'Language highlighting',
  '---------------------',
  '',
  'Every entry below is an actual reStructuredText code block processed by Sphinx before Dockle applies the shared',
  'highlighter. The list contains every canonical grammar bundled by the pinned Highlight.js dependency; aliases are',
  'shown beside the authoring identifier and are included by the filter. Each snippet is selected from that version\'s',
  'matching Highlight.js test fixtures.',
  '',
  '.. raw:: html',
  '',
  '   <div class="dockle-language-gallery"></div>',
  '',
  ...rstLanguageEntries.flatMap((entry) => [entry, '']),
  '.. raw:: html',
  '',
  '   <div class="dockle-language-gallery-end"></div>',
].join('\n');

const common = (await readFile(commonPath, 'utf8')).trim();
const banner = '<!-- Generated by npm run stage:examples; edit the .md.inc sources instead. -->';

await rm(stagedExamplesRoot, { force: true, recursive: true });
await mkdir(stagedExamplesRoot, { recursive: true });

for (const target of targets) {
  const stagedFrameworkRoot = path.join(
    stagedExamplesRoot,
    target.framework,
  );
  await cp(
    path.join(examplesRoot, target.framework),
    stagedFrameworkRoot,
    { recursive: true },
  );
  const sections = [banner, common];
  if (target.specific) {
    sections.push((await readFile(target.specific, 'utf8')).trim());
  }
  sections.push(
    markdownLanguageReference(target.useNeutralFence || false),
  );
  await writeFile(
    path.join(stagedFrameworkRoot, target.output),
    `${sections.join('\n\n')}\n`,
  );
}

const rstBasePath = path.join(
  examplesRoot,
  'sphinx',
  'component-reference-rst.rst.inc',
);
const rstOutputPath = path.join(
  stagedExamplesRoot,
  'sphinx',
  'component-reference-rst.rst',
);
const rstBase = (await readFile(rstBasePath, 'utf8')).trim();
await writeFile(
  rstOutputPath,
  `.. Generated by npm run stage:examples; edit the .rst.inc source instead.\n\n${rstBase}\n\n${rstLanguageReference}\n`,
);
