# 原图助手 - 微信小程序

## 项目结构
- `miniprogram/` — 小程序前端代码
- `backend/` — Python 后端，部署在 Railway

## 发布规范

**每次代码改动完成、准备发布前，必须先执行 `/pre-release-check`。**

检查全部通过后才能 push 代码和上传小程序。

## 关键注意事项

- **不要加 `__usePrivacyCheck__: true`**：会导致 clipboard/album 所有隐私 API 行为改变，errno 112 错误
- **不要在 app.json 加 `"privacy"` 字段**：不是合法微信配置，会报 invalid 警告
- **不要加 `wx.openSetting()` 在 fail 回调里**：权限已开时会造成死循环
- **iOS 保存图片必须用 PNG/JPEG**：WebP 会报 PHPhotosErrorDomain 3302 错误
- **后端改动后确认 Railway 自动部署成功**再测试

## 测试环境说明

- DevTools 模拟器（macOS）≠ 真机行为，隐私相关问题必须用真机验证
- 真机测试：开发者工具 → 预览 → 手机扫码
