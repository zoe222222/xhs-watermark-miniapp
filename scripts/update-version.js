const fs = require('fs')
const path = require('path')
const { execFileSync } = require('child_process')

const ROOT = path.resolve(__dirname, '..')
const VERSION_FILE = path.join(ROOT, 'miniprogram', 'version.local.js')
const VERSION_RELATIVE = 'miniprogram/version.local.js'
const FALLBACK_VERSION_FILE = path.join(ROOT, 'miniprogram', 'version.js')

function runGit(args) {
  return execFileSync('git', args, {
    cwd: ROOT,
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'ignore'],
  }).trim()
}

function readCurrentAppVersion() {
  try {
    delete require.cache[require.resolve(FALLBACK_VERSION_FILE)]
    const current = require(FALLBACK_VERSION_FILE)
    return current.appVersion || 'dev'
  } catch (_err) {
    return 'dev'
  }
}

function isDirtyExceptGeneratedVersion() {
  const status = runGit(['status', '--porcelain'])
  return status
    .split('\n')
    .filter(Boolean)
    .some((line) => !line.endsWith(VERSION_RELATIVE))
}

function buildVersionModule({ appVersion, gitBranch, gitCommit, dirty }) {
  const labelParts = ['miniapp', appVersion, 'git', gitCommit]
  if (dirty) labelParts.push('dirty')

  return [
    'module.exports = {',
    `  appVersion: ${JSON.stringify(appVersion)},`,
    `  gitBranch: ${JSON.stringify(gitBranch)},`,
    `  gitCommit: ${JSON.stringify(gitCommit)},`,
    `  dirty: ${JSON.stringify(dirty)},`,
    `  label: ${JSON.stringify(labelParts.join(' '))},`,
    '}',
    '',
  ].join('\n')
}

function collectVersionInfo() {
  return {
    appVersion: readCurrentAppVersion(),
    gitBranch: runGit(['branch', '--show-current']) || 'detached',
    gitCommit: runGit(['rev-parse', '--short', 'HEAD']),
    dirty: isDirtyExceptGeneratedVersion(),
  }
}

function main() {
  const info = collectVersionInfo()
  fs.writeFileSync(VERSION_FILE, buildVersionModule(info), 'utf8')
  console.log(`wrote ${VERSION_RELATIVE}: ${info.gitCommit}${info.dirty ? ' dirty' : ''}`)
}

if (require.main === module) {
  main()
}

module.exports = {
  buildVersionModule,
  collectVersionInfo,
}
