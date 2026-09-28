#!/usr/bin/env node
/**
 * fnOS 统一网关适配层：Unix Socket → 本机 TCP。
 *
 * 背景：ZCode entry-http 只监听 TCP；前端用根路径 /assets、/ws、/api。
 * 统一网关把 /app/zcode/** 转到 ${TRIM_APPDEST}/zcode.sock，且**不剥前缀**。
 *
 * 职责：
 *  1. 监听 Unix Socket（gatewaySocket）
 *  2. 剥掉 gatewayPrefix 后转发到 127.0.0.1:ZCODE_PORT
 *  3. HTML 里根路径资源改写到前缀下
 *  4. 注入 fetch/WebSocket 补丁，把 /ws、/api 收进前缀
 *  5. WebSocket upgrade 原样管道转发
 *
 * 环境变量：
 *  ZCODE_GATEWAY_SOCKET   必填，socket 绝对路径
 *  ZCODE_GATEWAY_PREFIX   默认 /app/zcode
 *  ZCODE_UPSTREAM_HOST    默认 127.0.0.1
 *  ZCODE_UPSTREAM_PORT    默认 8988
 */
import http from "node:http";
import net from "node:net";
import fs from "node:fs";
import path from "node:path";

const SOCKET_PATH = process.env.ZCODE_GATEWAY_SOCKET || "";
const PREFIX = (process.env.ZCODE_GATEWAY_PREFIX || "/app/zcode").replace(/\/+$/, "");
const UP_HOST = process.env.ZCODE_UPSTREAM_HOST || "127.0.0.1";
const UP_PORT = Number(process.env.ZCODE_UPSTREAM_PORT || 8988);
// 本地调试：ZCODE_GATEWAY_TCP_PORT 走 TCP 监听（Windows 无法建 Unix Socket）
const TCP_PORT = Number(process.env.ZCODE_GATEWAY_TCP_PORT || 0);

if (!SOCKET_PATH && !TCP_PORT) {
  console.error("[gateway] ZCODE_GATEWAY_SOCKET is required (or ZCODE_GATEWAY_TCP_PORT for debug)");
  process.exit(1);
}

function log(msg) {
  console.log(`[gateway] ${new Date().toISOString()} ${msg}`);
}

/** 去掉 /app/zcode 前缀，得到上游路径（以 / 开头）。 */
function stripPrefix(urlPath) {
  if (!PREFIX) return urlPath || "/";
  if (urlPath === PREFIX) return "/";
  if (urlPath.startsWith(PREFIX + "/")) return urlPath.slice(PREFIX.length) || "/";
  // 网关外路径（理论不应出现）原样透传
  return urlPath || "/";
}

/** HTML 根路径静态资源 → 前缀下。 */
function rewriteHtml(html, prefix) {
  let out = html;
  // src/href="/assets/..." 等
  out = out.replace(
    /(src|href)=["'](\/(?:assets|favicon|static|media)\/[^"']*)["']/gi,
    (_m, attr, p) => `${attr}="${prefix}${p}"`
  );
  // 极少数 data-url 之外的 import("/assets/...")
  out = out.replace(/(from|import\()\s*["'](\/assets\/[^"']+)["']/g, (_m, a, p) => {
    return `${a} "${prefix}${p}"`;
  });
  // 注入路径补丁（幂等）
  const marker = "zcode-fnos-gateway-shim";
  if (!out.includes(marker)) {
    const shim = `<script>/* ${marker} */(function(){try{
var B=${JSON.stringify(prefix)};
function fixPath(u){
  if(typeof u!=='string'||!u)return u;
  if(u.charAt(0)!=='/')return u;
  if(u.indexOf(B+'/')===0||u===B)return u;
  if(u.indexOf('/assets/')===0||u.indexOf('/api/')===0||u==='/api'||u.indexOf('/ws')===0||u==='/ws'){
    return B+u;
  }
  return u;
}
var _f=window.fetch;
if(_f){
  window.fetch=function(input,init){
    try{
      if(typeof input==='string')input=fixPath(input);
      else if(input&&typeof input==='object'&&input.url&&typeof Request!=='undefined'&&input instanceof Request){
        var nu=fixPath(input.url);
        if(nu!==input.url)input=new Request(nu,input);
      }
    }catch(e){}
    return _f.call(window,input,init);
  };
}
var _W=window.WebSocket;
if(_W){
  function WS(url,protocols){
    try{
      var u=new URL(url,location.href);
      var p=u.pathname;
      if(p==='/ws'||p.indexOf('/ws/')===0||p==='/api'||p.indexOf('/api/')===0){
        u.pathname=B+p;
      }
      url=u.toString();
    }catch(e){}
    return protocols===undefined?new _W(url):new _W(url,protocols);
  }
  WS.prototype=_W.prototype;
  WS.CONNECTING=_W.CONNECTING;WS.OPEN=_W.OPEN;WS.CLOSING=_W.CLOSING;WS.CLOSED=_W.CLOSED;
  window.WebSocket=WS;
}
}catch(e){}})();</script>`;
    if (out.includes("<head>")) out = out.replace("<head>", "<head>" + shim, 1);
    else out = shim + out;
  }
  return out;
}

function isProbablyHtml(req, resHeaders, buf) {
  const ct = (resHeaders["content-type"] || "") + "";
  if (/text\/html/i.test(ct)) return true;
  const url = (req.url || "").split("?")[0];
  if (url === "/" || url.endsWith("/") || url.endsWith(".html")) return true;
  const head = buf.slice(0, 256).toString("utf8").toLowerCase();
  return head.includes("<!doctype html") || head.includes("<html");
}

const server = http.createServer((req, res) => {
  const rawUrl = req.url || "/";
  const upPath = stripPrefix(rawUrl.split("?")[0]);
  const query = rawUrl.includes("?") ? "?" + rawUrl.split("?").slice(1).join("?") : "";
  const targetPath = upPath + query;

  const headers = { ...req.headers, host: `${UP_HOST}:${UP_PORT}` };
  // 网关身份 Header 原样保留（X-Trim-*）

  const preq = http.request(
    {
      host: UP_HOST,
      port: UP_PORT,
      path: targetPath,
      method: req.method,
      headers,
    },
    (pres) => {
      const ct = String(pres.headers["content-type"] || "");
      const looksHtml =
        /text\/html/i.test(ct) ||
        upPath === "/" ||
        upPath.endsWith("/") ||
        upPath.endsWith(".html") ||
        upPath.endsWith(".htm");

      if (!looksHtml) {
        // 静态资源等直接流式转发
        res.writeHead(pres.statusCode || 502, pres.headers);
        pres.pipe(res);
        return;
      }

      const chunks = [];
      pres.on("data", (c) => chunks.push(c));
      pres.on("end", () => {
        let body = Buffer.concat(chunks);
        const outHeaders = { ...pres.headers };
        if (body.length < 2 * 1024 * 1024) {
          body = Buffer.from(rewriteHtml(body.toString("utf8"), PREFIX), "utf8");
        }
        delete outHeaders["content-encoding"];
        delete outHeaders["transfer-encoding"];
        outHeaders["content-length"] = String(body.length);
        res.writeHead(pres.statusCode || 502, outHeaders);
        res.end(body);
      });
    }
  );
  preq.on("error", (err) => {
    log(`upstream error ${targetPath}: ${err.message}`);
    if (!res.headersSent) {
      res.writeHead(502, { "content-type": "text/plain; charset=utf-8" });
    }
    res.end("ZCode 后端未就绪，请在应用中心重启 ZCode。\n");
  });

  if (req.method === "POST" || req.method === "PUT" || req.method === "PATCH") {
    req.pipe(preq);
  } else {
    preq.end();
  }
});

/** WebSocket / 任意 upgrade：剥前缀后 TCP 管道转发。 */
server.on("upgrade", (req, socket, head) => {
  const rawUrl = req.url || "/";
  const upPath = stripPrefix(rawUrl.split("?")[0]);
  const query = rawUrl.includes("?") ? "?" + rawUrl.split("?").slice(1).join("?") : "";
  const targetPath = upPath + query;

  const up = net.connect(UP_PORT, UP_HOST, () => {
    const headerLines = [`${req.method} ${targetPath} HTTP/1.1`];
    for (let i = 0; i < req.rawHeaders.length; i += 2) {
      const k = req.rawHeaders[i];
      const v = req.rawHeaders[i + 1];
      if (k.toLowerCase() === "host") {
        headerLines.push(`Host: ${UP_HOST}:${UP_PORT}`);
      } else {
        headerLines.push(`${k}: ${v}`);
      }
    }
    up.write(headerLines.join("\r\n") + "\r\n\r\n");
    if (head && head.length) up.write(head);
    socket.pipe(up);
    up.pipe(socket);
  });
  up.on("error", (err) => {
    log(`ws upgrade error ${targetPath}: ${err.message}`);
    try {
      socket.write("HTTP/1.1 502 Bad Gateway\r\nConnection: close\r\n\r\n");
    } catch {}
    socket.destroy();
  });
  socket.on("error", () => up.destroy());
});

function listen() {
  if (TCP_PORT) {
    server.listen(TCP_PORT, "127.0.0.1", () => {
      log(`listening tcp:127.0.0.1:${TCP_PORT} → http://${UP_HOST}:${UP_PORT} (prefix=${PREFIX || "/"})`);
    });
    return;
  }
  try {
    if (fs.existsSync(SOCKET_PATH)) fs.unlinkSync(SOCKET_PATH);
  } catch {}
  fs.mkdirSync(path.dirname(SOCKET_PATH), { recursive: true });
  server.listen(SOCKET_PATH, () => {
    try {
      fs.chmodSync(SOCKET_PATH, 0o777);
    } catch {}
    log(`listening unix:${SOCKET_PATH} → http://${UP_HOST}:${UP_PORT} (prefix=${PREFIX || "/"})`);
  });
}

server.on("error", (err) => {
  log(`server error: ${err.message}`);
  process.exit(1);
});

listen();
