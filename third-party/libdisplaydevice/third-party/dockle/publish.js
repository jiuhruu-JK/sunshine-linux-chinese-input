'use strict';

const fs = require('node:fs');
const path = require('node:path');
const env = require('jsdoc/env');

const packageMetadata = require('./package.json');

function repositoryUrl(repository) {
  const value = typeof repository === 'string' ? repository : repository?.url;
  return (value || '').replace(/^git\+/, '').replace(/\.git$/, '');
}

function consumerMetadata() {
  const filename = path.join(env.pwd, 'package.json');
  if (!fs.existsSync(filename)) {
    return {};
  }
  return JSON.parse(fs.readFileSync(filename, 'utf8'));
}

const consumer = consumerMetadata();
env.conf.templates ||= {};
env.conf.templates.dockle ||= {};
const dockle = env.conf.templates.dockle;
dockle.dockleVersion ||= packageMetadata.version;
dockle.projectName ||= consumer.name || 'Documentation';
dockle.projectUrl ||= repositoryUrl(consumer.repository) || 'index.html';
dockle.projectVersion ||= consumer.version || '';
dockle.repositoryUrl ||= repositoryUrl(consumer.repository) || '';
dockle.targetTitle ||= dockle.projectName;

module.exports = require('./src/dockle/jsdoc_template/publish');
