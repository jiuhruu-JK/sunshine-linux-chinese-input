'use strict';

const fs = require('node:fs');
const path = require('node:path');
const env = require('jsdoc/env');

const DEFAULT_TOKENS = `:root {
  --dockle-primary: #2962ff;
  --dockle-content: #2e3440;
  --dockle-background: #ffffff;
  --dockle-font: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --dockle-code-font: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace;
}
:root[data-color-scheme="dark"] {
  --dockle-content: #e5e7eb;
  --dockle-background: #131416;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-color-scheme]) {
    --dockle-content: #e5e7eb;
    --dockle-background: #131416;
  }
}
`;

const sharedAssets = path.resolve(
  __dirname,
  '..',
  'sphinx',
  'themes',
  'dockle',
  'static',
);

function assetName(prefix, source) {
  if (/^https?:\/\//i.test(source)) {
    return source;
  }
  return source ? `${prefix}${path.extname(source).toLowerCase()}` : '';
}

function copyConfiguredAsset(source, destination) {
  if (!source || /^https?:\/\//i.test(source)) {
    return;
  }
  fs.copyFileSync(path.resolve(env.pwd, source), destination);
}

function escapeAttribute(value) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('"', '&quot;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');
}

function configuredAssets(dockle, key) {
  const assets = dockle[key] || [];
  if (!Array.isArray(assets) || assets.some((asset) => (
    typeof asset !== 'string' || !asset.trim()
  ))) {
    throw new TypeError(`templates.dockle.${key} must be an array of strings`);
  }
  return assets;
}

function installExtraAssets(root, dockle) {
  const stylesheets = configuredAssets(dockle, 'extraStylesheets');
  const javascript = configuredAssets(dockle, 'extraJavascript');
  const localAssets = new Map();
  for (const asset of [...stylesheets, ...javascript]) {
    if (/^https?:\/\//i.test(asset)) {
      continue;
    }
    const name = path.basename(asset);
    const source = path.resolve(env.pwd, asset);
    const existing = localAssets.get(name);
    if (existing && existing !== source) {
      throw new Error(`extra assets must have unique filenames: ${existing} and ${source}`);
    }
    localAssets.set(name, source);
  }
  for (const [name, source] of localAssets) {
    fs.copyFileSync(source, path.join(root, name));
  }

  for (const filename of htmlFiles(root)) {
    let document = fs.readFileSync(filename, 'utf8');
    const assetUrl = (asset) => {
      if (/^https?:\/\//i.test(asset)) {
        return asset;
      }
      return path.relative(path.dirname(filename), path.join(root, path.basename(asset)))
        .split(path.sep).join('/');
    };
    const tags = [
      ...stylesheets.map((asset, index) => (
        `<link rel="stylesheet" href="${escapeAttribute(assetUrl(asset))}" `
        + `data-dockle-extra-stylesheet="${index}">`
      )),
      ...javascript.map((asset, index) => (
        `<script defer src="${escapeAttribute(assetUrl(asset))}" `
        + `data-dockle-extra-javascript="${index}"></script>`
      )),
    ];
    if (tags.length) {
      document = document.replace('</head>', `${tags.join('\n')}\n</head>`);
      fs.writeFileSync(filename, document, 'utf8');
    }
  }
}

function htmlFiles(directory) {
  const files = [];
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const filename = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      files.push(...htmlFiles(filename));
    } else if (entry.isFile() && entry.name.endsWith('.html')) {
      files.push(filename);
    }
  }
  return files;
}

function siteRoot(destination) {
  const indexes = htmlFiles(destination)
    .filter((filename) => path.basename(filename) === 'index.html')
    .sort((left, right) => left.length - right.length);
  if (!indexes.length) {
    throw new Error(`JSDoc did not generate an index page in ${destination}`);
  }
  return path.dirname(indexes[0]);
}

function decodeEntities(value) {
  const named = {
    amp: '&',
    apos: "'",
    gt: '>',
    lt: '<',
    nbsp: ' ',
    quot: '"',
  };
  return value.replace(/&(#(?:x[\da-f]+|\d+)|[a-z]+);/gi, (match, entity) => {
    if (entity.startsWith('#x')) {
      return String.fromCodePoint(Number.parseInt(entity.slice(2), 16));
    }
    if (entity.startsWith('#')) {
      return String.fromCodePoint(Number.parseInt(entity.slice(1), 10));
    }
    return named[entity.toLowerCase()] ?? match;
  });
}

function searchableText(document) {
  return decodeEntities(
    document
      .replace(/<(script|style|svg)\b[^>]*>[\s\S]*?<\/\1>/gi, ' ')
      .replace(/<[^<>]*>/g, ' '),
  ).replace(/\s+/g, ' ').trim();
}

function searchDocument(filename, root) {
  const document = fs.readFileSync(filename, 'utf8');
  const title = /<h1\b[^>]*class="page-title"[^>]*>([\s\S]*?)<\/h1>/i.exec(document)?.[1]
    || /<title[^>]*>([^<]*)<\/title>/i.exec(document)?.[1]
    || path.basename(filename, '.html');
  const content = /<div id="main">([\s\S]*?)<footer\b/i.exec(document)?.[1]
    || document;
  const body = content
    .replace(/<div class="dockle-page-actions"[\s\S]*?<\/div>/i, ' ')
    .replace(/<h1\b[^>]*>[\s\S]*?<\/h1>/i, ' ');
  return {
    location: path.relative(root, filename).split(path.sep).join('/'),
    text: searchableText(body).slice(0, 4000),
    title: decodeEntities(title).trim().split(' — ')[0].split(' – ')[0],
  };
}

function finishSite(destination, dockle) {
  const root = siteRoot(destination);
  const stylesheet = dockle.stylesheet
    ? fs.readFileSync(path.resolve(env.pwd, dockle.stylesheet), 'utf8')
    : DEFAULT_TOKENS + fs.readFileSync(path.join(sharedAssets, 'dockle.css'), 'utf8');
  fs.writeFileSync(path.join(root, 'dockle.css'), stylesheet, 'utf8');
  copyConfiguredAsset(dockle.logo, path.join(root, dockle.logoFile));
  copyConfiguredAsset(dockle.favicon, path.join(root, dockle.faviconFile));
  const searchPage = fs.readFileSync(path.join(__dirname, 'tmpl', 'dockle-search.html'), 'utf8')
    .replaceAll('{{FRAMEWORK}}', 'jsdoc')
    .replaceAll('{{PROJECT}}', escapeAttribute(dockle.projectName))
    .replaceAll('{{ASSETS}}', '')
    .replaceAll('{{INDEX}}', 'search.json')
    .replaceAll('{{LOGO}}', escapeAttribute(dockle.logoFile))
    .replaceAll('{{FAVICON_LINK}}', dockle.faviconFile
      ? `<link rel="icon" href="${escapeAttribute(dockle.faviconFile)}" data-dockle-favicon>`
      : '');
  fs.writeFileSync(path.join(root, 'dockle-search.html'), searchPage, 'utf8');
  installExtraAssets(root, dockle);
  const docs = htmlFiles(root)
    .filter((filename) => path.basename(filename) !== 'dockle-search.html')
    .map((filename) => searchDocument(filename, root));
  fs.writeFileSync(
    path.join(root, 'search.json'),
    JSON.stringify({ docs }),
    'utf8',
  );
}

exports.publish = (taffyData, opts, tutorials) => {
  env.conf.templates ||= {};
  env.conf.templates.default ||= {};
  env.conf.templates.dockle ||= {};
  const defaults = env.conf.templates.default;
  const dockle = env.conf.templates.dockle;
  dockle.dockleVersion ||= '0.0.0';
  dockle.faviconFile = assetName('dockle-favicon', dockle.favicon);
  dockle.logoFile = assetName('dockle-logo', dockle.logo);
  dockle.projectName ||= 'Documentation';
  dockle.projectUrl ||= dockle.portalUrl || 'index.html';
  dockle.repositoryUrl ||= '';
  dockle.targetTitle ||= dockle.projectName;

  defaults.includeDate = false;
  defaults.layoutFile = path.join(__dirname, 'tmpl', 'layout.tmpl');
  defaults.staticFiles ||= {};
  defaults.staticFiles.include ||= [];
  if (!defaults.staticFiles.include.includes(sharedAssets)) {
    defaults.staticFiles.include.push(sharedAssets);
  }

  const defaultTemplate = path.join(env.dirname, 'templates', 'default');
  const defaultPublisher = require(path.join(defaultTemplate, 'publish'));
  opts.template = defaultTemplate;
  const result = defaultPublisher.publish(taffyData, opts, tutorials);
  finishSite(path.resolve(opts.destination), dockle);
  return result;
};
