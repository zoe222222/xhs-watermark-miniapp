# 腾讯云轻量服务器部署

## 推荐配置

- 服务器：腾讯云轻量应用服务器，2 核 2G 起步
- 系统：Ubuntu 22.04 LTS 或 Debian 12
- 域名：备案完成后解析到服务器公网 IP
- 端口：放行 80、443

## 首次部署

服务器安装 Docker 和 Docker Compose 后，在服务器上拉取后端仓库：

```bash
git clone https://github.com/zoe222222/xhs-watermark-backend.git
cd xhs-watermark-backend
cp deploy/Caddyfile.example deploy/Caddyfile
```

编辑 `deploy/Caddyfile`，把 `api.example.com` 改成正式 API 域名。

启动服务：

```bash
GIT_COMMIT_SHA=$(git rev-parse --short HEAD) docker compose up -d --build
```

检查接口：

```bash
curl https://你的域名/api/version
curl https://你的域名/api/health
```

## 后续更新

```bash
git pull
GIT_COMMIT_SHA=$(git rev-parse --short HEAD) docker compose up -d --build
```

## 小程序配置

后端域名稳定后，把 `miniprogram/app.js` 里的 `BACKEND_URL` 改成：

```js
BACKEND_URL: 'https://你的域名'
```

微信公众平台也要添加同一个域名到：

- request 合法域名
- downloadFile 合法域名

## 备案期间临时测试

备案没完成前，可以先用公网 IP 测试后端接口：

```bash
curl http://服务器IP:8787/api/version
```

微信开发者工具里可以临时关闭合法域名校验做开发调试。正式版不能用 IP，必须等备案域名和 HTTPS 完成。
