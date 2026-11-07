#!/usr/bin/env python3
"""公開前の動作確認。単体ページ（index.html）と、飯村システム用モジュール（su-module.js）の両方を確かめる。
使い方: python3 tools/smoke_test.py   （失敗すると終了コード1）
playwright と chrome が無い環境では、構文チェックだけ行う。"""
import os, sys, subprocess, threading, http.server, functools, socketserver
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fails = []
def check(cond, msg):
    print(('OK  ' if cond else 'NG  ') + msg)
    if not cond: fails.append(msg)

# 1) 構文
src = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
open('/tmp/_su_page.js', 'w', encoding='utf-8').write(src.split('<script>')[1].split('</script>')[0])
for f in ('/tmp/_su_page.js', os.path.join(ROOT, 'su-module.js')):
    r = subprocess.run(['node', '--check', f], capture_output=True, text=True)
    check(r.returncode == 0, '構文 ' + os.path.basename(f) + (' ' + r.stderr[:200] if r.returncode else ''))

try:
    from playwright.sync_api import sync_playwright
except Exception:
    print('playwright なし：構文チェックのみ'); sys.exit(1 if fails else 0)
chrome = next((p for p in ('/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser') if os.path.exists(p)), None)

class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = socketserver.TCPServer(('127.0.0.1', 0), functools.partial(Q, directory=ROOT)); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
U = 'http://127.0.0.1:%d/' % port
with sync_playwright() as p:
    b = p.chromium.launch(**({'executable_path': chrome} if chrome else {}), args=['--no-sandbox'])
    # 2) 単体ページ
    pg = b.new_page(viewport={'width': 1300, 'height': 900}); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(U + 'index.html'); pg.wait_for_timeout(2500)
    pg.fill('#mq', '獣医'); pg.wait_for_timeout(300)
    n = pg.locator('.ritem').count(); check(5 <= n <= 30, '単体：「獣医」の検索結果 %d件' % n)
    h = pg.evaluate("document.querySelector('.ritem').getBoundingClientRect().height"); check(h > 20, '単体：結果の行が見える（高さ %dpx）' % h)
    pg.locator('.ritem').first.click(); pg.wait_for_timeout(500)
    check(pg.is_visible('#uov'), '単体：ポップアップが開く')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(200)
    for v in ('ai', 'plan', 'trend', 'map'):
        pg.evaluate('Searchuniv.showView(%r)' % v); pg.wait_for_timeout(300)
        check(pg.is_visible('#v-' + v), '単体：%s 画面' % v)
    check(not errs, '単体：エラーなし ' + '; '.join(errs[:3]))
    # 3) モジュール（邪魔な CSS・同じ ID を持つ親ページの中）
    pg = b.new_page(viewport={'width': 1300, 'height': 900}); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(U + 'tools/module_test.html'); pg.wait_for_timeout(2500)
    check(pg.evaluate('SearchunivModule.apiVersion') == 1, 'モジュール：apiVersion=1')
    check(pg.evaluate('typeof CSS.escape') == 'function', 'モジュール：ブラウザ標準の名前（CSS など）を隠さない')
    sr = "document.getElementById('host').shadowRoot"
    pg.evaluate(sr + ".getElementById('mq').value='獣医'; " + sr + ".getElementById('mq').dispatchEvent(new Event('input'))"); pg.wait_for_timeout(400)
    n2 = pg.evaluate(sr + ".querySelectorAll('.ritem').length"); check(n2 == n, 'モジュール：検索結果が単体と同じ %d件' % n2)
    h2 = pg.evaluate(sr + ".querySelector('.ritem').getBoundingClientRect().height"); check(h2 > 20, 'モジュール：結果の行が見える（高さ %dpx）' % h2)
    pg.locator('#host .ritem').first.click(); pg.wait_for_timeout(500)
    check(pg.evaluate(sr + ".getElementById('uov').hidden") is False, 'モジュール：ポップアップが開く')
    col = pg.evaluate("getComputedStyle(" + sr + ".querySelector('#mpanel h3')).color")
    check(col != 'rgb(255, 0, 0)', 'モジュール：親ページのCSSが漏れない（文字色 %s）' % col)
    check(pg.evaluate("document.getElementById('mq').textContent.includes('親ページ')"), 'モジュール：親ページの同じIDに触れない')
    check(pg.evaluate("location.hash") == '', 'モジュール：親ページのURL(#)を変えない')
    pg.evaluate(sr + ".getElementById('uclose').click()")
    if pg.evaluate(sr + ".querySelectorAll('.wmapwrap').length"):
        pg.evaluate(sr + ".querySelector('.wmapwrap').click()"); pg.wait_for_timeout(400)
        check(pg.evaluate("!!(" + sr + ".getElementById('wmodal')) && !" + sr + ".getElementById('wmodal').hidden"), 'モジュール：協定校の世界地図が拡大できる')
        pg.evaluate(sr + ".getElementById('wmodal').click()"); pg.keyboard.press('Escape')
    for v in ('ai', 'plan', 'trend', 'map'):
        pg.evaluate('API.showView(%r)' % v); pg.wait_for_timeout(300)
        check(pg.evaluate(sr + ".getElementById('v-%s').hidden" % v) is False, 'モジュール：%s 画面' % v)
    check(pg.evaluate('VIEWS.join(",")') == 'ai,plan,trend,map', 'モジュール：画面切替を親に通知')
    check(pg.evaluate('window.MOD_ERR||""') == '' and not errs, 'モジュール：エラーなし ' + '; '.join(errs[:3]))
    b.close()
srv.shutdown()
print('\n' + ('すべて合格' if not fails else '不合格 %d件' % len(fails)))
sys.exit(1 if fails else 0)
