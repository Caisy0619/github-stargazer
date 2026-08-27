#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub 每周情报看板 - 数据抓取脚本
功能：
1. 批量验证白名单仓库（404剔除/改名跟进）
2. 抓取白名单仓库完整数据（stars/描述/语言/pushed_at/license/topics）
3. 全领域 top 500（高星榜候选池）
4. GitHub Trending 周榜（黑马榜补充，抓不到跳过）
5. 与上一快照对比算周增速（绝对增量+百分比）
6. 输出 history/YYYY-MM-DD.json（追加式，不覆盖）+ data/latest.json
限速：搜索 API 匿名 10次/分钟，每次调用间隔 6.5 秒
"""
import json, os, sys, time, re, datetime, urllib.request, urllib.parse

ROOT = os.environ.get('BOARD_ROOT') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
HIST = os.path.join(ROOT, 'history')
TOKEN = os.environ.get('GITHUB_TOKEN', '')
UA = {'Accept': 'application/vnd.github+json', 'User-Agent': 'github-board/0.1'}
if TOKEN:
    UA['Authorization'] = f'token {TOKEN}'

TODAY = datetime.date.today().isoformat()


def gh_get(url, timeout=25, raw=False, retries=3):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
                return body if raw else json.loads(body)
        except Exception as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise last


def search_repos(query, per_page=100, page=1, sort=None):
    """搜索 API，返回 items 列表"""
    params = {'q': query, 'per_page': per_page, 'page': page}
    if sort:
        params['sort'] = sort
        params['order'] = 'desc'
    url = 'https://api.github.com/search/repositories?' + urllib.parse.urlencode(params)
    return gh_get(url).get('items', [])


def normalize(d):
    """统一仓库字段"""
    lic = d.get('license') or {}
    return {
        'full_name': d['full_name'],
        'name': d['name'],
        'owner': d['owner']['login'],
        'url': d['html_url'],
        'description': (d.get('description') or '').strip(),
        'stars': d['stargazers_count'],
        'forks': d.get('forks_count', 0),
        'language': d.get('language') or '',
        'topics': d.get('topics', []),
        'pushed_at': d.get('pushed_at', ''),
        'created_at': d.get('created_at', ''),
        'license': lic.get('spdx_id', '') if lic else '',
        'archived': d.get('archived', False),
    }


def batch_verify(repo_list, batch=8):
    """用 repo: 批量搜索验证白名单，返回 (found_dict, missing_list)"""
    found, missing = {}, []
    for i in range(0, len(repo_list), batch):
        chunk = repo_list[i:i+batch]
        q = ' '.join(f'repo:{r}' for r in chunk)
        try:
            items = search_repos(q, per_page=batch)
            got = {it['full_name'].lower(): it for it in items}
            for r in chunk:
                hit = got.get(r.lower())
                if hit:
                    found[hit['full_name']] = normalize(hit)
                    if hit['full_name'].lower() != r.lower():
                        print(f"  [改名] {r} -> {hit['full_name']}")
                else:
                    missing.append(r)
        except Exception as e:
            print(f"  [批次失败] {chunk[0]}...: {e}")
            missing.extend(chunk)
        time.sleep(6.5)
    return found, missing


def fetch_global_top(n=500):
    """全领域按 stars 排序 top n（分页，每页50防大响应断连）"""
    out = []
    per = 50
    pages = (n + per - 1) // per
    for p in range(1, pages + 1):
        try:
            items = search_repos('stars:>5000', per_page=per, page=p, sort='stars')
            out.extend(normalize(it) for it in items)
            print(f"  全领域第 {p} 页: {len(items)} 个")
        except Exception as e:
            print(f"  全领域第 {p} 页失败: {e}")
            break
        time.sleep(6.5)
    return out[:n]


def fetch_trending():
    """抓 github.com/trending?since=weekly，解析仓库名和本周新增星。失败返回空。"""
    try:
        html = gh_get('https://github.com/trending?since=weekly', timeout=20, raw=True).decode('utf-8', 'ignore')
        # 宽松匹配：trending 每行 article 里 /owner/repo 链接
        rows = re.findall(r'<article[^>]*>.*?<a[^>]*href="/([^"/]+/[^"/]+)"', html, re.S)
        gains = re.findall(r'([\d,]+)\s*stars?\s*this week', html)
        res = []
        seen = set()
        for name in rows:
            n = name.strip()
            if n in seen or n.count('/') != 1:
                continue
            seen.add(n)
            g = int(gains[len(res)].replace(',', '')) if len(res) < len(gains) else None
            res.append({'full_name': n, 'week_gain': g})
        print(f"  Trending 抓到 {len(res)} 个")
        return res
    except Exception as e:
        print(f"  Trending 抓取失败（跳过，不影响主流程）: {e}")
        return []


def load_prev_snapshot():
    """找最近一份历史快照"""
    files = sorted(f for f in os.listdir(HIST) if f.endswith('.json')) if os.path.isdir(HIST) else []
    if not files:
        return None, {}
    prev_date = files[-1].replace('.json', '')
    with open(os.path.join(HIST, files[-1]), encoding='utf-8') as f:
        d = json.load(f)
    return prev_date, {r['full_name']: r for r in d.get('repos', [])}


def main():
    os.makedirs(HIST, exist_ok=True)
    with open(os.path.join(DATA, 'categories.json'), encoding='utf-8') as f:
        cats = json.load(f)['categories']

    # 1. 白名单验证+抓取
    all_whitelist = []
    for c in cats:
        all_whitelist.extend(c['repos'])
    print(f"[1/4] 验证白名单 {len(all_whitelist)} 个仓库...")
    found, missing = batch_verify(all_whitelist)
    print(f"  有效 {len(found)}，缺失/404 {len(missing)}: {missing}")

    # 1.5 搜索补位：每领域自动补足 top 项目——白名单管"准"，搜索管"全"
    # 每分类目标 ≥20 个；不足则放宽 stars 下限再补一轮；真没有就全列
    print("[1.5] 搜索补位（每领域自动补足）...")
    extra_map = {}
    for c in cats:
        qs = c.get('search_queries') or []
        if not qs:
            continue
        pool = {}
        for q in qs:
            try:
                for it in search_repos(q, per_page=20, sort='stars'):
                    pool[it['full_name']] = normalize(it)
            except Exception as e:
                print(f"  补位失败 [{c['id']}] {q}: {e}")
            time.sleep(6.5)
        # 白名单命中 + 池 < 20 → 放宽 stars 下限补第二轮
        whitelist_hit = sum(1 for r in c['repos'] if r in found)
        if whitelist_hit + len(pool) < 20:
            for q in qs:
                q2 = re.sub(r'stars:>\d+', 'stars:>10', q)
                try:
                    for it in search_repos(q2, per_page=20, sort='stars'):
                        pool[it['full_name']] = normalize(it)
                except Exception as e:
                    print(f"  放宽补位失败 [{c['id']}] {q2}: {e}")
                time.sleep(6.5)
        added = 0
        for name, r in pool.items():
            if name not in found:
                found[name] = r
                added += 1
            extra_map.setdefault(name.lower(), [])
            if c['id'] not in extra_map[name.lower()]:
                extra_map[name.lower()].append(c['id'])
        print(f"  [{c['name']}] 白名单 {whitelist_hit} + 池 {len(pool)}（新增 {added}）")

    # 2. 全领域 top500
    print("[2/4] 抓全领域 top500...")
    global_top = fetch_global_top(500)

    # 3. Trending
    print("[3/4] 抓 Trending 周榜...")
    trending = fetch_trending()

    # 4. 合并 + 增速计算
    print("[4/4] 合并数据、计算增速...")
    prev_date, prev = load_prev_snapshot()
    days = 7
    if prev_date:
        days = max(1, (datetime.date.today() - datetime.date.fromisoformat(prev_date)).days)
    trend_map = {t['full_name']: t.get('week_gain') for t in trending}

    repos = {}
    for name, r in found.items():
        repos[name] = r
    for r in global_top:
        repos.setdefault(r['full_name'], r)
    # trending 里不在已知池的补抓（限额友好：只抓前30）
    extra = [t for t in trending if t['full_name'] not in repos][:30]
    if extra:
        print(f"  补抓 Trending 新仓库 {len(extra)} 个...")
        f2, _m = batch_verify([t['full_name'] for t in extra], batch=8)
        repos.update(f2)

    out_repos = []
    for name, r in repos.items():
        p = prev.get(name)
        if p:
            delta = r['stars'] - p['stars']
            r['week_gain'] = delta
            r['week_gain_pct'] = round(delta / p['stars'] * 100, 2) if p['stars'] else None
            r['span_days'] = days
            r['avg_daily_gain'] = round(delta / days, 1)
        elif name in trend_map and trend_map[name] is not None:
            r['week_gain'] = trend_map[name]
            r['week_gain_pct'] = None
            r['span_days'] = 7
            r['avg_daily_gain'] = round(trend_map[name] / 7, 1)
        else:
            r['week_gain'] = None  # 新收录，下周起有真实增速
            r['week_gain_pct'] = None
            r['span_days'] = days
            r['avg_daily_gain'] = None
        out_repos.append(r)

    # 领域归属
    cat_map = {}
    for c in cats:
        for repo in c['repos']:
            cat_map.setdefault(repo.lower(), []).append(c['id'])
    for k, v in extra_map.items():
        cat_map.setdefault(k, [])
        for cid in v:
            if cid not in cat_map[k]:
                cat_map[k].append(cid)
    for r in out_repos:
        r['categories'] = cat_map.get(r['full_name'].lower(), [])

    snapshot = {
        'date': TODAY,
        'prev_date': prev_date,
        'span_days': days,
        'missing': missing,
        'trending_count': len(trending),
        'repos': out_repos,
    }
    with open(os.path.join(HIST, f'{TODAY}.json'), 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=1)
    with open(os.path.join(DATA, 'latest.json'), 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=1)

    print(f"\n完成: {len(out_repos)} 个仓库, 快照 history/{TODAY}.json")
    print(f"缺失 {len(missing)} 个: {missing}")


if __name__ == '__main__':
    main()
