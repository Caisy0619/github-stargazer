#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动翻译：把英文项目描述翻成人话中文（DeepSeek 批量），存 translate_cache.json
- 只翻"没有手写人话解释(plain)且描述是英文"的项目
- 缓存驱动：翻过的不再翻，每周只花新增部分的钱（约几分钱）
- 失败不阻塞：哪批失败跳过哪批
"""
import json, os, re, time, urllib.request

ROOT = os.environ.get('BOARD_ROOT') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
CACHE_PATH = os.path.join(DATA, 'translate_cache.json')

def load_env_key():
    p = os.path.expanduser('~/.hermes/.env')
    if os.path.exists(p):
        for line in open(p):
            if line.startswith('DEEPSEEK_API_KEY='):
                return line.split('=', 1)[1].strip().strip('"').strip("'")
    return os.environ.get('DEEPSEEK_API_KEY', '')

KEY = load_env_key()
API = 'https://api.deepseek.com/v1/chat/completions'
MODEL = 'deepseek-v4-flash'


def mostly_english(s):
    if not s:
        return False
    zh = len(re.findall(r'[一-鿿]', s))
    return zh / max(1, len(s)) < 0.1


def call_llm(batch):
    """batch: [(name, desc)] -> {name: zh}"""
    items = '\n'.join(f'- {n}: {d}' for n, d in batch)
    prompt = (
        '把以下 GitHub 项目描述翻译成中文。要求：一句话、说人话（给非程序员看）、'
        '说明这个项目是干什么的、普通人能拿它做什么。不要术语堆砌。\n'
        '只返回 JSON，格式 {"仓库名": "中文描述"}，不要别的内容。\n\n' + items
    )
    body = json.dumps({
        'model': MODEL,
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': 0.2,
    }).encode()
    req = urllib.request.Request(API, data=body, headers={
        'Authorization': f'Bearer {KEY}',
        'Content-Type': 'application/json',
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        out = json.loads(r.read())
    text = out['choices'][0]['message']['content'].strip()
    m = re.search(r'\{.*\}', text, re.S)
    return json.loads(m.group(0)) if m else {}


def main():
    if not KEY:
        print('未找到 DEEPSEEK_API_KEY，跳过翻译')
        return
    latest = json.load(open(os.path.join(DATA, 'latest.json'), encoding='utf-8'))
    plain = json.load(open(os.path.join(DATA, 'plain_names.json'), encoding='utf-8'))
    cache = {}
    if os.path.exists(CACHE_PATH):
        cache = json.load(open(CACHE_PATH, encoding='utf-8'))

    todo = []
    for r in latest['repos']:
        n = r['full_name']
        d = r.get('description', '')
        if n in plain or n in cache or not mostly_english(d):
            continue
        todo.append((n, d[:150]))
    print(f'待翻译: {len(todo)} 个（缓存已有 {len(cache)} 个）')

    ok = 0
    for i in range(0, len(todo), 30):
        batch = todo[i:i+30]
        try:
            res = call_llm(batch)
            cache.update(res)
            ok += len(res)
            print(f'  批次 {i//30+1}: +{len(res)}')
        except Exception as e:
            print(f'  批次 {i//30+1} 失败（跳过）: {e}')
        time.sleep(1)

    json.dump(cache, open(CACHE_PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'完成: 新翻 {ok}，缓存总数 {len(cache)}')


if __name__ == '__main__':
    main()
