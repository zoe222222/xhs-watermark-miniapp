# 原图助手 - 微信小程序

## 当前结构

- `miniprogram/`：微信小程序前端
- `backend/`：Python 后端，可部署到腾讯云轻量服务器或 Railway
- `tests/`：本地回归检查

根目录网页版本已移除，当前只维护小程序和后端。

## 主流程

1. 小程序首页粘贴小红书帖子链接或分享文本。
2. 小程序请求后端 `/api/fetch-xhs` 解析图片地址。
3. 图库页通过 `/api/proxy-image?thumb=1` 展示缩略图。
4. 保存图片时通过 `/api/proxy-image?fmt=png` 下载 PNG，兼容 iOS 相册保存。

## 版本诊断

小程序首页底部会显示两行版本：

- `miniapp ...`：当前小程序代码版本
- `backend ...`：当前连接到的后端版本

如果截图里出现 `POST /api/fetch-xhs 404`，通常表示线上后端没有部署包含该接口的版本，或小程序指向了错误的后端域名。先看首页底部的 `backend ...`，再检查服务器部署状态。

## 本地检查

```bash
python3 -m unittest tests/test_backend_contract.py
node --check miniprogram/app.js
node --check miniprogram/pages/index/index.js
node --check miniprogram/pages/gallery/gallery.js
python3 -m py_compile backend/server.py backend/xhs_fetcher.py
```

发布前还必须执行项目内的 `/pre-release-check` 清单。

## 小程序测试与上传

1. 用微信开发者工具打开 `miniprogram/`。
2. 编译后先在模拟器确认页面无报错。
3. 点“预览”，用手机扫码真机测试保存相册。
4. 测试通过后，在开发者工具右上角点“上传”。

微信后台需要确认：

- 当前 `miniprogram/app.js` 中的 `BACKEND_URL` 已配置到 request 合法域名。
- 同一域名已配置到 downloadFile 合法域名。

## 后端更新

当前项目已经合并为单仓库。小程序和后端改动都在同一个 Git 仓库里提交、推送。

腾讯云轻量服务器部署说明见：

- `backend/DEPLOY_TENCENT.md`

后端部署完成后，在浏览器或开发者工具里检查：

- `/api/version`
- `/api/health`
- `/api/fetch-xhs`

## 关键注意事项

- 不要加 `__usePrivacyCheck__: true`。
- 不要在 `app.json` 加 `"privacy"` 字段。
- 不要在保存失败回调里调用 `wx.openSetting()`。
- iOS 保存图片必须使用 PNG/JPEG，不能保存 WebP。
- 后端改动后必须确认服务器部署成功，再用小程序真机测试。
