import js from '@eslint/js';
import globals from 'globals';

export default [
  {
    ignores: [
      '.dockle/**',
      '.npm-cache/**',
      '.npm-tmp/**',
      '.package-audit/**',
      '.package-consumer/**',
      '_site/**',
      'coverage/**',
      'node_modules/**',
      'src/dockle/sphinx/themes/dockle/static/lucide.min.js',
    ],
  },
  js.configs.recommended,
  {
    files: [
      '*.js',
      'bin/**/*.cjs',
      'src/dockle/jsdoc_template/**/*.js',
    ],
    languageOptions: {
      globals: globals.node,
      sourceType: 'commonjs',
    },
  },
  {
    files: [
      'scripts/**/*.mjs',
      'tests-js/**/*.mjs',
    ],
    languageOptions: {
      globals: globals.node,
      sourceType: 'module',
    },
  },
  {
    files: ['src/dockle/sphinx/themes/dockle/static/dockle.js'],
    languageOptions: {
      globals: globals.browser,
    },
  },
];
