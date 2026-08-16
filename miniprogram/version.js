module.exports = {
  appVersion: '2026.08.14.2',
  gitBranch: 'unknown',
  gitCommit: 'unknown',
  dirty: true,
  label: 'miniapp 2026.08.14.2 git unknown dirty',
}

try {
  module.exports = require('./version.local')
} catch (_err) {
  // version.local.js is generated before preview/upload.
}
