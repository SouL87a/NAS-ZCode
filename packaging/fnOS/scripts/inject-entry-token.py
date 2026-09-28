#!/usr/bin/env python3
"""给 web/index.html 注入「访问令牌」登录门禁。

端口访问不再把令牌放在 URL 路径（地址栏泄露）。
打开 http://NAS:8988/ 时：先探测 /api/server-info →
未通过则弹出登录框 → 输入令牌写 cookie → 校验通过后进入。

统一网关由 gateway-proxy 自动注入令牌，浏览器侧探测会直接通过，不弹框。
"""

from __future__ import annotations

import sys
from pathlib import Path

MARKER = "zcode-fnos-login-gate"

# 同时承担：鉴权探测、登录 UI、cookie 写入
SNIPPET = (
    "<script>/* " + MARKER + " */"
    "(function(){"
    "if(window.__ZCODE_FNOS_LOGIN__)return;"
    "window.__ZCODE_FNOS_LOGIN__=1;"
    "var KEY='zcode_lite_token';"
    "function cookieSet(v){"
    "document.cookie=KEY+'='+encodeURIComponent(v)+'; path=/; SameSite=Lax';"
    "}"
    "function cookieClear(){document.cookie=KEY+'=; path=/; Max-Age=0';}"
    "function el(tag,css){var e=document.createElement(tag);if(css)e.style.cssText=css;return e;}"
    "function ensureRoot(){"
    "var r=document.getElementById('zcode-fnos-login');"
    "if(r)return r;"
    "r=el('div','position:fixed;inset:0;z-index:2147483646;display:flex;align-items:center;justify-content:center;background:rgba(15,23,42,0.92);font-family:Inter,-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;color:#e2e8f0');"
    "r.id='zcode-fnos-login';"
    "function mount(){(document.body||document.documentElement).appendChild(r);}"
    "if(document.body)mount();else document.addEventListener('DOMContentLoaded',mount);"
    "return r;"
    "}"
    "function showStatus(text){"
    "var root=ensureRoot();root.innerHTML='';"
    "var card=el('div','width:340px;padding:28px;border-radius:16px;background:#1e293b;border:1px solid #334155;text-align:center;font-size:13px;color:#94a3b8');"
    "card.textContent=text||'正在验证访问权限…';"
    "root.appendChild(card);"
    "}"
    "function showLogin(err){"
    "var root=ensureRoot();root.innerHTML='';"
    "var card=el('div','width:340px;padding:28px 28px 24px;border-radius:16px;background:#1e293b;border:1px solid #334155;box-shadow:0 18px 50px rgba(0,0,0,.45)');"
    "var h=el('div','font-size:18px;font-weight:600;margin:0 0 8px');h.textContent='ZCode';"
    "var s=el('div','font-size:13px;line-height:1.5;color:#94a3b8;margin-bottom:18px');s.textContent='请输入访问令牌以继续';"
    "var inp=el('input','width:100%;box-sizing:border-box;padding:10px 12px;border-radius:10px;border:1px solid #475569;background:#0f172a;color:#f8fafc;font-size:14px;outline:none');"
    "inp.type='password';inp.placeholder='访问令牌';inp.autocomplete='current-password';"
    "var msg=el('div','min-height:18px;margin:10px 0 4px;font-size:12px;color:#f87171');"
    "if(err)msg.textContent=err;"
    "var btn=el('button','width:100%;margin-top:8px;padding:10px 12px;border:0;border-radius:10px;background:#2563eb;color:#fff;font-size:14px;font-weight:600;cursor:pointer');"
    "btn.type='button';btn.textContent='进入';"
    "card.appendChild(h);card.appendChild(s);card.appendChild(inp);card.appendChild(msg);card.appendChild(btn);"
    "root.appendChild(card);"
    "setTimeout(function(){try{inp.focus();}catch(e){}},0);"
    "function submit(){"
    "var v=(inp.value||'').trim();"
    "if(!v){msg.textContent='请输入访问令牌';return;}"
    "msg.style.color='#94a3b8';msg.textContent='验证中…';btn.disabled=true;"
    "cookieSet(v);"
    "check(true);"
    "}"
    "btn.onclick=submit;"
    "inp.addEventListener('keydown',function(e){if(e.key==='Enter')submit();});"
    "}"
    "function removeGate(){"
    "var g=document.getElementById('zcode-fnos-login');"
    "if(g&&g.parentNode)g.parentNode.removeChild(g);"
    "}"
    "function check(afterSubmit){"
    "fetch('/api/server-info',{cache:'no-store',credentials:'same-origin'}).then(function(r){"
    "if(r.ok){cookieKeepHint();removeGate();if(afterSubmit)location.reload();return;}"
    "if(afterSubmit){cookieClear();showLogin('令牌不正确或服务未就绪');return;}"
    "showLogin('');"
    "}).catch(function(){"
    "if(afterSubmit)showLogin('无法连接服务，请稍后重试');else showLogin('');"
    "});"
    "}"
    "function cookieKeepHint(){}"
    "showStatus('正在验证访问权限…');"
    "if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',function(){check(false);});"
    "else check(false);"
    "})();"
    "</script>"
)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: inject-entry-token.py <web/index.html>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"✗ 找不到 {path}", file=sys.stderr)
        return 1

    html = path.read_text(encoding="utf-8")

    # 移除历史版本注入（路径令牌 / 旧登录门禁）
    for old in ("zcode-fnos-entry-token", "zcode-fnos-login-gate"):
        while True:
            start = html.find("<script>/* " + old)
            if start == -1:
                break
            end = html.find("</script>", start)
            if end == -1:
                break
            html = html[:start] + html[end + len("</script>") :]

    inject = SNIPPET
    if "<head>" in html:
        html = html.replace("<head>", "<head>" + inject, 1)
    else:
        html = inject + html

    path.write_text(html, encoding="utf-8", newline="\n")
    print("[build] 已注入访问令牌登录门禁 → web/index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
