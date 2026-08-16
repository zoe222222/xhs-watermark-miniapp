// pages/gallery/gallery.js
const app = getApp()

Page({
  data: {
    images: [],        // [{ url, proxyUrl, width, height, downloading, saved }]
    total: 0,
    sourceUrl: '',
    downloadingAll: false,
    savedCount: 0,
    allSaved: false,
    toastMsg: '',
    toastVisible: false,
  },

  _toastTimer: null,
  _nextTimer: null,
  _pageActive: false,

  // ── 生命周期 ─────────────────────────────────────────────────────────
  onLoad() {
    this._pageActive = true
    const images     = app.globalData.galleryImages    || []
    const sourceUrl  = app.globalData.gallerySourceUrl || ''

    app.globalData.galleryImages    = null
    app.globalData.galleryTotal     = 0
    app.globalData.gallerySourceUrl = ''

    const BACKEND = app.globalData.BACKEND_URL
    const enriched = images.map(function(img) {
      const base = BACKEND + '/api/proxy-image?url=' + encodeURIComponent(img.url)
      return {
        url: img.url,
        width: img.width || 0,
        height: img.height || 0,
        displayUrl: base + '&thumb=1',  // 缩略图：800px JPEG，加载更快
        proxyUrl:   base + '&fmt=jpeg', // 下载用 JPEG/PNG 兼容格式，保存更快
        downloading: false,
        saved: false,
      }
    })

    this.setData({ images: enriched, total: enriched.length, sourceUrl })
  },

  onUnload() {
    this._pageActive = false
    clearTimeout(this._toastTimer)
    clearTimeout(this._nextTimer)
    this._toastTimer = null
    this._nextTimer = null
  },

  onHide() {
    clearTimeout(this._toastTimer)
  },

  // ── 图片加载失败降级 ───────────────────────────────────────────────
  onImgError(e) {
    const index = e.currentTarget.dataset.index
    const img = this.data.images[index]
    if (img && img.displayUrl !== img.proxyUrl) {
      this._setImageState(index, { displayUrl: img.proxyUrl })
    }
  },

  // ── 预览图片 ─────────────────────────────────────────────────────────
  onPreview(e) {
    const index = e.currentTarget.dataset.index
    const urls = this.data.images.map(img => img.proxyUrl)
    wx.previewImage({
      current: urls[index],
      urls,
    })
  },

  // ── 下载单张 ─────────────────────────────────────────────────────────
  onDownloadOne(e) {
    const index = e.currentTarget.dataset.index
    const img = this.data.images[index]
    if (img.downloading || img.saved) return
    this._downloadImage(index)
  },

  _downloadImage(index) {
    const img = this.data.images[index]
    const proxyUrl = img.proxyUrl

    this._setImageState(index, { downloading: true })

    wx.downloadFile({
      url: proxyUrl,
      timeout: 30000,
      success: (res) => {
        if (res.statusCode === 200) {
          wx.saveImageToPhotosAlbum({
            filePath: res.tempFilePath,
            success: () => {
              this._setImageState(index, { downloading: false, saved: true })
              this.showToast('第 ' + (index + 1) + ' 张已保存到相册')
            },
            fail: (err) => {
              console.log('saveImageToPhotosAlbum fail:', JSON.stringify(err))
              this._setImageState(index, { downloading: false })
              this._handleSaveFail(err)
            }
          })
        } else {
          this._setImageState(index, { downloading: false })
          this.showToast('图片获取失败，请稍后重试')
        }
      },
      fail: (err) => {
        console.log('downloadFile fail:', JSON.stringify(err))
        this._setImageState(index, { downloading: false })
        this.showToast('网络异常，请检查网络后重试')
      }
    })
  },

  _handleSaveFail(err, next) {
    const errMsg = err && err.errMsg ? err.errMsg : ''
    if (
      errMsg.includes('auth deny') ||
      errMsg.includes('auth denied') ||
      errMsg.includes('authorize no response') ||
      errMsg.includes('not authorized')
    ) {
      this.showToast('请在手机设置 → 微信 → 照片中开启权限')
      return
    }
    if (errMsg.includes('cancel')) {
      this.showToast('已取消保存')
      if (next) next()
      return
    }
    if (errMsg.includes('no such file')) {
      this.showToast('模拟器不支持保存，请用真机测试')
      return
    }
    this.showToast('保存失败，请重试')
    if (next) next()
  },

  _setImageState(index, patch) {
    if (!this._pageActive) return
    const images = this.data.images.slice()
    images[index] = Object.assign({}, images[index], patch)
    this.setData({ images: images })
  },

  // ── 全部下载 ─────────────────────────────────────────────────────────
  onDownloadAll() {
    if (this.data.downloadingAll || this.data.allSaved) return
    this.setData({ downloadingAll: true, savedCount: 0 })
    this._downloadSequential(0)
  },

  _downloadSequential(index) {
    const images = this.data.images
    if (index >= images.length) {
      const savedCount = this.data.savedCount
      const allOk = savedCount === images.length
      this.setData({ downloadingAll: false, allSaved: allOk })
      if (allOk) {
        this.showToast('全部 ' + images.length + ' 张已保存到相册')
      } else {
        const failed = images.length - savedCount
        this.showToast('已保存 ' + savedCount + ' 张，' + failed + ' 张失败，可重试')
      }
      return
    }

    if (images[index].saved) {
      this.setData({ savedCount: this.data.savedCount + 1 })
      this._queueNext(index + 1, 100)
      return
    }

    const img = images[index]
    const proxyUrl = img.proxyUrl

    this._setImageState(index, { downloading: true })

    wx.downloadFile({
      url: proxyUrl,
      timeout: 30000,
      success: (res) => {
        if (res.statusCode !== 200) {
          this._setImageState(index, { downloading: false })
          this._queueNext(index + 1, 300)
          return
        }
        wx.saveImageToPhotosAlbum({
          filePath: res.tempFilePath,
          success: () => {
            this._setImageState(index, { downloading: false, saved: true })
            if (this._pageActive) {
              this.setData({ savedCount: this.data.savedCount + 1 })
            }
            this._queueNext(index + 1, 300)
          },
          fail: (err) => {
            this._setImageState(index, { downloading: false })
            const errMsg = err && err.errMsg ? err.errMsg : ''
            if (
              errMsg.includes('auth deny') ||
              errMsg.includes('auth denied') ||
              errMsg.includes('authorize no response')
            ) {
              if (this._pageActive) {
                this.setData({ downloadingAll: false })
              }
              this._handleSaveFail(err)
              return
            }
            this._queueNext(index + 1, 300)
          }
        })
      },
      fail: () => {
        this._setImageState(index, { downloading: false })
        this._queueNext(index + 1, 300)
      }
    })
  },

  _queueNext(index, delay) {
    clearTimeout(this._nextTimer)
    if (!this._pageActive) return
    this._nextTimer = setTimeout(() => {
      if (!this._pageActive) return
      this._downloadSequential(index)
    }, delay)
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
