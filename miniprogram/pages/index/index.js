// pages/index/index.js
const app = getApp()

Page({
  data: {
    linkText: '',
    fetching: false,
    versionText: app.globalData.VERSION.label,
    backendVersionText: 'backend 检查中',
    toastMsg: '',
    toastVisible: false,
  },

  _toastTimer: null,
  _pageActive: false,

  onLoad() {
    this._pageActive = true
    this.loadBackendVersion()
  },
  onUnload() {
    this._pageActive = false
    clearTimeout(this._toastTimer)
    this._toastTimer = null
  },

  // ── 输入 ────────────────────────────────────────────────────────────
  onLinkInput(e) {
    this.setData({ linkText: e.detail.value })
  },

  onClear() {
    this.setData({ linkText: '' })
  },

  // ── 版本诊断 ──────────────────────────────────────────────────────────
  loadBackendVersion() {
    wx.request({
      url: `${app.globalData.BACKEND_URL}/api/version`,
      method: 'GET',
      timeout: 5000,
      success: (res) => {
        const data = res.data || {}
        if (res.statusCode === 200 && data.ok) {
          const commit = data.gitCommit || 'unknown'
          this.setData({ backendVersionText: `backend ${commit}` })
          return
        }
        this.setData({ backendVersionText: `backend HTTP ${res.statusCode}` })
      },
      fail: () => {
        this.setData({ backendVersionText: 'backend 不可达' })
      }
    })
  },

  // ── 粘贴 ────────────────────────────────────────────────────────────
  onPaste() {
    if (this._pasting) return
    this._pasting = true
    wx.getClipboardData({
      success: ({ data }) => {
        const text = (data || '').trim()
        if (!text) {
          this.showToast('剪贴板为空')
        } else {
          this.setData({ linkText: text })
        }
      },
      fail: (err) => {
        console.error('getClipboardData fail:', JSON.stringify(err))
        this.showToast('获取剪贴板失败，请手动粘贴')
      },
      complete: () => {
        setTimeout(() => { this._pasting = false }, 1000)
      }
    })
  },

  // ── 获取原图 ─────────────────────────────────────────────────────────
  onFetch() {
    const link = this.data.linkText.trim()
    if (!link) { this.showToast('请先粘贴小红书链接'); return }
    if (this.data.fetching) return

    this.setData({ fetching: true })
    wx.showLoading({ title: '解析中…', mask: true })

    wx.request({
      url: `${app.globalData.BACKEND_URL}/api/fetch-xhs`,
      method: 'POST',
      header: { 'Content-Type': 'application/json' },
      timeout: 20000,
      data: { link },
      success: (res) => {
        const data = res.data
        if (res.statusCode === 404) {
          this.showToast('后端接口未部署，请更新后端')
          return
        }
        if (res.statusCode !== 200 || !data.ok) {
          this.showToast(data.error || '解析失败，请检查链接')
          return
        }
        const images = data.images || []
        if (!images.length) {
          this.showToast('未找到图片，请换一个帖子试试')
          return
        }
        app.globalData.galleryImages = images
        app.globalData.galleryTotal = data.total
        app.globalData.gallerySourceUrl = data.sourceUrl || ''
        wx.navigateTo({
          url: `/pages/gallery/gallery`
        })
      },
      fail: (err) => {
        this.showToast(err.errMsg === 'request:fail timeout' ? '请求超时，请重试' : '网络错误，请重试')
      },
      complete: () => {
        wx.hideLoading()
        this.setData({ fetching: false })
      }
    })
  },

  // ── 转发 ────────────────────────────────────────────────────────────
  onShareAppMessage() {
    return {
      title: '一键获取小红书原图，无水印下载',
      path: '/pages/index/index',
    }
  },

  // ── Toast ────────────────────────────────────────────────────────────
  showToast(msg) {
    if (!this._pageActive) return
    clearTimeout(this._toastTimer)
    this.setData({ toastMsg: msg, toastVisible: true })
    this._toastTimer = setTimeout(() => {
      if (!this._pageActive) return
      this.setData({ toastVisible: false })
    }, 2600)
  }
})
