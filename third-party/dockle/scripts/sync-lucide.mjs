import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const manifest = JSON.parse(await readFile(path.join(root, 'package.json'), 'utf8'));
const version = manifest.devDependencies.lucide;
const lucideRoot = path.join(root, 'node_modules', 'lucide');
const staticRoot = path.join(
  root,
  'src',
  'dockle',
  'sphinx',
  'themes',
  'dockle',
  'static',
);

const bundle = await readFile(
  path.join(lucideRoot, 'dist', 'umd', 'lucide.min.js'),
  'utf8',
);
const license = await readFile(path.join(lucideRoot, 'LICENSE'), 'utf8');
const banner = `/*! Lucide ${version} | ISC | https://lucide.dev */\n`;

await mkdir(staticRoot, { recursive: true });
await writeFile(
  path.join(staticRoot, 'lucide.min.js'),
  `${banner}${bundle.trimEnd()}\n`,
);
await writeFile(path.join(staticRoot, 'LUCIDE_LICENSE.txt'), license);
