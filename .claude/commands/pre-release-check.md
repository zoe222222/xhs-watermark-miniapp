# 发布前检查

你是一个微信小程序发布前的质量检查员。请自动读取项目文件，逐项核查以下清单，并输出一份结构化的检查报告。

## 执行步骤

### 1. 读取所有需要检查的文件

依次读取以下文件：
- `miniprogram/app.json`
- `miniprogram/app.js`
- `miniprogram/pages/index/index.js`
- `miniprogram/pages/index/index.wxml`
- `miniprogram/pages/gallery/gallery.js`
- `miniprogram/pages/gallery/gallery.wxml`
- `backend/server.py`（如果存在）

### 2. 逐项核查

**【A】全局配置风险（app.json）**
- `__usePrivacyCheck__` 是否存在？若存在，警告：需确认平台隐私政策已发布且每个敏感 API scope 都已声明
- `privacy` 字段是否存在？若存在，报错：该字段不是合法微信配置，必须删除
- `pages` 里声明的页面路径是否都能在项目中找到对应文件

**【B】隐私与权限 API 核查**

扫描所有 JS 文件，检查以下 API 的使用情况：

- `wx.getClipboardData`：若存在，确认没有 `__usePrivacyCheck__: true`；若有该标志，需额外确认平台政策
- `wx.saveImageToPhotosAlbum`：若存在，检查是否有对 fail 回调的处理，且没有 `wx.openSetting()` 死循环风险
- `wx.downloadFile`：若存在，记录所有请求的域名
- `wx.request`：若存在，记录所有请求的域名

**【C】保存流程安全检查（gallery.js）**

- `_handleSaveFail` 里是否有 `wx.openSetting()` 调用？若有，报错：可能造成死循环
- `saveImageToPhotosAlbum` 的 fail 回调是否有对 `auth deny` 类错误的提示处理？
- `_downloadSequential` 里是否有在 auth 错误时停止整个队列的逻辑（避免16张全失败）？

**【D】后端域名核查**

- 从 `app.js` 或 `app.globalData.BACKEND_URL` 提取后端地址
- 提醒用户确认该域名已在微信后台"request合法域名"和"downloadFile合法域名"中配置

**【E】代码一致性检查**

- `app.js` 里 `globalData` 定义的字段，和各页面里 `app.globalData.xxx` 读取的字段是否一致（无拼写错误）
- 检查是否有页面引用了 `app.globalData.pendingPrivacy` 或 `_showPrivacy`（旧隐私逻辑残留）

**【F】WXML 残留检查**

- 扫描所有 wxml 文件，检查是否还有 `_showPrivacy`、`privacy-mask`、`onPrivacyAgree`、`onPrivacyDeny` 相关代码（旧隐私弹窗残留）

### 3. 输出检查报告

按以下格式输出：

```
════════════════════════════════════
        发布前检查报告
════════════════════════════════════

【A】全局配置
  ✅ / ❌  检查项描述

【B】隐私与权限 API
  ✅ / ❌  检查项描述

【C】保存流程安全
  ✅ / ❌  检查项描述

【D】后端域名
  ✅ / ⚠️  检查项描述（需人工在微信后台确认的标 ⚠️）

【E】代码一致性
  ✅ / ❌  检查项描述

【F】WXML 残留
  ✅ / ❌  检查项描述

────────────────────────────────────
总结：X 项通过 / X 项需修复 / X 项需人工确认

需修复的问题：
  1. 具体问题描述 + 建议修复方式

需人工在微信后台确认的事项：
  1. 具体描述
════════════════════════════════════
```

如果发现需要修复的问题，询问用户是否需要立即帮忙修复。
