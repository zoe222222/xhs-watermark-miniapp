const assert = require('assert')
const { buildVersionModule } = require('../scripts/update-version')

const output = buildVersionModule({
  appVersion: '2026.08.14.3',
  gitBranch: 'main',
  gitCommit: 'abcdef1',
  dirty: true,
})

const sandbox = { module: { exports: {} } }
Function('module', output)(sandbox.module)
const version = sandbox.module.exports

assert.strictEqual(version.appVersion, '2026.08.14.3')
assert.strictEqual(version.gitBranch, 'main')
assert.strictEqual(version.gitCommit, 'abcdef1')
assert.strictEqual(version.dirty, true)
assert.strictEqual(version.label, 'miniapp 2026.08.14.3 git abcdef1 dirty')
