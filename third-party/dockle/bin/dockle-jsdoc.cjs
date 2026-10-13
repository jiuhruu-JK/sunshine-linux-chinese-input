#!/usr/bin/env node
'use strict';

const path = require('node:path');
const { spawnSync } = require('node:child_process');

const jsdoc = require.resolve('jsdoc/jsdoc.js');
const template = path.resolve(__dirname, '..');
const args = process.argv.slice(2);
const configuredTemplate = args.some((argument) => (
  argument === '--template'
  || argument === '-t'
  || argument.startsWith('--template=')
));

if (!configuredTemplate) {
  args.push('--template', template);
}

const result = spawnSync(process.execPath, [jsdoc, ...args], {
  env: process.env,
  stdio: 'inherit',
});

if (result.error) {
  throw result.error;
}
process.exitCode = result.status ?? 1;
