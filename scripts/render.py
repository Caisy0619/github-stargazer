#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
看板 HTML 生成器 v0.4
- 标签栏模块化（大类套小类：综合/AI学习/大模型 有子标签）
- 整行可点直达 GitHub（↗ 标识）
- 1200px 宽屏利用 / 无使用说明文字（界面自解释）
- 搜索同义词（搜 AI=人工智能=大模型）
- 中文显示优先级：手写人话 > 自动翻译 > 英文原文
- "上线N周"标签 / 僵尸标灰 / License 标签
输出 dist/index.html —— 单文件、数据内嵌、零外部依赖
"""
import json, os

ROOT = os.environ.get('BOARD_ROOT') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
DIST = os.path.join(ROOT, 'dist')


def load(name, default=None):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return default
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def main():
    latest = load('latest.json')
    cats = load('categories.json')['categories']
    plain = load('plain_names.json', default={})
    trans = load('translate_cache.json', default={})

    repos = {r['full_name']: r for r in latest['repos']}
    for name, r in repos.items():
        r['plain'] = plain.get(name, '')
        r['description_zh'] = trans.get(name, '')

    all_repos = sorted(repos.values(), key=lambda r: -r['stars'])
    top_star = all_repos[:30]
    with_gain = [r for r in repos.values() if r.get('week_gain')]
    with_gain.sort(key=lambda r: -(r['week_gain'] or 0))
    top_gain = with_gain[:30]

    payload = {
        'date': latest['date'],
        'prev': latest.get('prev_date'),
        'span': latest.get('span_days', 7),
        'categories': cats,
        'repos': repos,
        'top_star': [r['full_name'] for r in top_star],
        'top_gain': [r['full_name'] for r in top_gain],
    }
    data_js = json.dumps(payload, ensure_ascii=False)

    page = TEMPLATE.replace('__DATA__', data_js).replace('__DATE__', latest['date'])
    os.makedirs(DIST, exist_ok=True)
    out = os.path.join(DIST, 'index.html')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(page)
    # 同时写一份到仓库根目录：GitHub Pages 首页用（dist 版用于微信发送）
    root_out = os.path.join(ROOT, 'index.html')
    with open(root_out, 'w', encoding='utf-8') as f:
        f.write(page)
    print(f'生成 {out} ({os.path.getsize(out)//1024} KB) + {root_out}')


TEMPLATE = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GitHub 每周情报</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif; background:#f6f7f9; color:#1f2329; font-size:14px; line-height:1.6; }
  .header { position:sticky; top:0; background:#f6f7f9; z-index:10; padding:12px 16px 0; border-bottom:1px solid #e5e7eb; }
  .wrap, .main { max-width:1200px; margin:0 auto; }
  h1 { font-size:18px; display:inline; }
  .sub { color:#6b7280; font-size:11px; margin:2px 0 8px; }
  .search-box { width:100%; padding:8px 12px; border:1px solid #e5e7eb; border-radius:8px; font-size:13px; margin:0 0 8px; outline:none; background:#fff; }
  .search-box:focus { border-color:#0969da; }
  .tabs { display:flex; gap:4px; overflow-x:auto; -webkit-overflow-scrolling:touch; }
  .tab { padding:8px 14px; font-size:13px; color:#6b7280; cursor:pointer; white-space:nowrap; border-bottom:2px solid transparent; }
  .tab.on { color:#1f2329; font-weight:600; border-bottom-color:#1f2329; }
  .main { padding:12px 16px 40px; }
  .warn { background:#fffbeb; border:1px solid #fde68a; color:#92400e; font-size:12px; padding:8px 12px; border-radius:8px; margin-bottom:12px; }
  .pills { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:10px; }
  .pill { padding:4px 12px; font-size:12px; border-radius:14px; background:#fff; border:1px solid #e5e7eb; color:#4b5563; cursor:pointer; }
  .pill.on { background:#1f2329; color:#fff; border-color:#1f2329; }
  .sg { font-size:11px; color:#9ca3af; font-weight:600; margin-right:2px; align-self:center; }
  .modebar { display:flex; gap:6px; margin-bottom:8px; align-items:center; }
  .mode { padding:3px 10px; font-size:11px; border-radius:12px; background:#fff; border:1px solid #e5e7eb; color:#6b7280; cursor:pointer; }
  .mode.on { background:#1f2329; color:#fff; border-color:#1f2329; }
  .hint { font-size:11px; color:#9ca3af; margin-left:auto; }
  .card { background:#fff; border:1px solid #e5e7eb; border-radius:10px; overflow:hidden; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  td, th { padding:9px 12px; text-align:left; vertical-align:top; border-bottom:1px solid #f0f1f3; }
  tr:last-child td { border-bottom:none; }
  tbody tr:hover, tr.row:hover { background:#f8fafc; }
  th { font-size:11px; color:#9ca3af; font-weight:500; white-space:nowrap; }
  .num { font-variant-numeric:tabular-nums; white-space:nowrap; font-weight:600; }
  .up { color:#16a34a; }
  .repo a { color:#0969da; text-decoration:none; font-weight:600; }
  .ext { font-size:11px; color:#9ca3af; }
  .desc { color:#4b5563; font-size:12px; }
  .plain { color:#1f2329; font-size:12px; }
  .tag { display:inline-block; font-size:10px; padding:1px 6px; border-radius:8px; margin-left:4px; vertical-align:1px; }
  .tag.lic { background:#eef2ff; color:#4f46e5; }
  .tag.dead { background:#fef2f2; color:#dc2626; }
  .tag.new { background:#ecfdf5; color:#059669; }
  .dead-row { opacity:.45; }
  .muted { color:#9ca3af; font-size:11px; }
  .empty { padding:24px; text-align:center; color:#9ca3af; font-size:12px; }
  .foot { margin-top:20px; font-size:11px; color:#9ca3af; text-align:center; line-height:1.8; }
  .adv { margin-top:8px; font-size:11px; color:#9ca3af; text-align:right; }
  .adv span { cursor:pointer; }
  .adv span:hover { color:#0969da; }
  .adv-box { display:none; margin-top:8px; background:#fff; border:1px dashed #e5e7eb; border-radius:10px; padding:10px 12px; text-align:left; }
  .adv-box.show { display:block; }
  .adv-box input { padding:6px 10px; border:1px solid #d1d5db; border-radius:6px; font-size:12px; width:60%; }
  .adv-box button { padding:6px 12px; border:none; border-radius:6px; background:#1f2329; color:#fff; font-size:12px; cursor:pointer; }
  @media (max-width:600px){ .hide-m{display:none;} th,td{padding:6px 6px;} .header,.main{padding-left:10px;padding-right:10px;} }
</style>
</head>
<body>
<div class="header">
  <div class="wrap">
    <h1>GitHub 每周情报</h1>
    <div class="sub">更新于 __DATE__ · 每周一自动更新</div>
    <input class="search-box" id="search" placeholder="搜一搜：记账 / 笔记 / AI / 孩子 / 截图 ..." oninput="onSearch()">
    <div class="tabs" id="tabs"></div>
  </div>
</div>
<div class="main" id="main"></div>

<script>
const D = __DATA__;
const LS_TAB='gh-tab', LS_SUB='gh-sub', LS_MODE='gh-mode', LS_CUSTOM='gh-board-custom';
const TABS = [
  {id:'hot',  name:'🔥 本周黑马'},
  {id:'top',  name:'🏆 巨头榜'},
  {id:'worklife', name:'💼 工作提效/生活创意', group:'工作提效/生活创意'},
  {id:'industry', name:'🏭 行业提效', group:'行业提效'},
  {id:'ai-learn', name:'🎓 AI 学习', group:'AI 学习'},
  {id:'ai-apps', name:'🚀 AI 应用', cat:'ai-apps'},
  {id:'ai-coding', name:'💻 AI 编程', cat:'ai-coding'},
  {id:'llm', name:'🧠 大模型', group:'大模型'},
];
const SYN = {
  'ai':['ai','人工智能','大模型','llm','智能','机器学习'],
  '人工智能':['ai','人工智能','大模型','llm','智能'],
  '大模型':['大模型','llm','人工智能','ai','模型','gpt'],
  '记账':['记账','accounting','bookkeeping','ledger','财务','账本'],
  '财务':['财务','finance','accounting','记账','会计'],
  '会计':['会计','accounting','财务','记账'],
  '理财':['理财','investment','投资','budget','finance','预算'],
  '投资':['投资','investment','理财','stock','股票','portfolio'],
  '笔记':['笔记','note','knowledge','wiki','知识'],
  '知识':['知识','knowledge','笔记','wiki'],
  '密码':['密码','password','passkey'],
  '同步':['同步','sync','传文件','传输'],
  '截图':['截图','screenshot','screen'],
  '录屏':['录屏','screen','截图'],
  '视频':['视频','video'],
  'pdf':['pdf','文档'],
  '文档':['文档','pdf','document'],
  '客户':['客户','crm','销售'],
  '销售':['销售','crm','客户'],
  '人事':['人事','hr','人力','人力资源'],
  '人力':['人力','hr','人事','人力资源'],
  '招聘':['招聘','hr','人事','hire'],
  '物流':['物流','logistics','供应链','supply'],
  '供应链':['供应链','supply','物流'],
  '库存':['库存','inventory','warehouse','仓储'],
  '仓储':['仓储','warehouse','库存'],
  '孩子':['孩子','儿童','kids','children','教育'],
  '儿童':['儿童','kids','孩子','教育'],
  '教育':['教育','education','学习','孩子'],
  '学习':['学习','tutorial','course','教程','education'],
  '教程':['教程','tutorial','course','学习','guide'],
  '课程':['课程','course','教程','学习'],
  '照片':['照片','photo','相册','图片'],
  '相册':['相册','photo','照片'],
  '白板':['白板','whiteboard','excalidraw'],
  '流程图':['流程图','diagram','drawio','白板'],
  '翻译':['翻译','translate','translation'],
  '编程':['编程','coding','code','程序','开发'],
  '模型':['模型','model','llm','大模型'],
  '医疗':['医疗','medical','health','病历'],
  '病历':['病历','medical','emr','医疗'],
  '图片':['图片','image','照片','photo'],
  'ocr':['ocr','文字识别','tesseract'],
  '智能家居':['智能家居','homeassistant','智能'],
  '待办':['待办','todo','备忘','任务'],
};
let state = {
  tab: localStorage.getItem(LS_TAB) || 'hot',
  sub: JSON.parse(localStorage.getItem(LS_SUB) || '{}'),
  mode: localStorage.getItem(LS_MODE) || 'star',
  q: '',
};

function fmtFull(n){ if(n==null) return '—'; return n.toLocaleString(); }
function esc(s){ return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;'); }
function isDead(r){ return r.pushed_at && (Date.now()-new Date(r.pushed_at))/864e5 > 365; }
function weekAge(r){ if(!r.created_at) return 0; return Math.floor((Date.now()-new Date(r.created_at))/864e5/7); }
function gainText(r){ return r.week_gain==null ? '<span class="muted">新收录</span>' : '<span class="up num">+'+fmtFull(r.week_gain)+'</span>'; }
function pctText(r){ return r.week_gain_pct==null ? '<span class="muted">—</span>' : '<span class="up num">+'+r.week_gain_pct+'%</span>'; }
function getCustom(){ try{ return JSON.parse(localStorage.getItem(LS_CUSTOM)||'[]'); }catch(e){ return []; } }
function termsOf(q){
  const k = q.toLowerCase().trim();
  for(const key in SYN){ if(key.toLowerCase()===k) return SYN[key]; }
  return [k];
}
function matchQ(r,q){
  if(!q) return true;
  const hay = (r.full_name+' '+(r.description||'')+' '+(r.description_zh||'')+' '+(r.plain||'')+' '+(r.language||'')).toLowerCase();
  return termsOf(q).some(t=>hay.includes(t.toLowerCase()));
}

function rowHtml(r, mode){
  const dead = isDead(r);
  const age = weekAge(r);
  const lic = r.license && r.license!=='NOASSERTION' ? r.license : '';
  const zh = r.plain || r.description_zh || '';
  const desc = zh ? '<div class="plain">'+esc(zh)+'</div>' : (r.description ? '<div class="desc">'+esc(r.description)+'</div>' : '');
  const tags = [];
  if(lic) tags.push('<span class="tag lic">'+esc(lic)+'</span>');
  if(dead) tags.push('<span class="tag dead">久未更新</span>');
  if(age>0 && age<=26) tags.push('<span class="tag new">上线'+age+'周</span>');
  const g = mode==='gain' ? '<td>'+gainText(r)+'</td><td class="hide-m">'+pctText(r)+'</td>' : '';
  return '<tr class="row'+(dead?' dead-row':'')+'" onclick="window.open(\''+r.url+'\',\'_blank\')" style="cursor:pointer">'
    + '<td class="repo"><a href="'+r.url+'" target="_blank" rel="noopener" onclick="event.stopPropagation()">'+esc(r.full_name)+' <span class="ext">↗</span></a>'+tags.join('')+desc+'</td>'
    + '<td class="num">'+fmtFull(r.stars)+'</td>' + g + '</tr>';
}
function tableHtml(list, mode){
  if(!list.length) return '<div class="empty">没有匹配的项目</div>';
  const head = mode==='gain'
    ? '<tr><th>项目</th><th>star</th><th>周增量</th><th class="hide-m">周涨幅</th></tr>'
    : '<tr><th>项目</th><th>star</th></tr>';
  return '<div class="card"><table>'+head+'<tbody>'+list.map(r=>rowHtml(r,mode)).join('')+'</tbody></table></div>';
}
function sortBy(list, mode){
  return mode==='gain' ? [...list].sort((a,b)=>((b.week_gain??-1)-(a.week_gain??-1))) : [...list].sort((a,b)=>b.stars-a.stars);
}
function modeBar(){
  return '<div class="modebar"><span class="mode'+(state.mode==='star'?' on':'')+'" onclick="setMode(\'star\')">总 star 榜</span>'
    + '<span class="mode'+(state.mode==='gain'?' on':'')+'" onclick="setMode(\'gain\')">增速榜</span></div>';
}
function reposOfCat(id){
  const c = D.categories.find(x=>x.id===id);
  if(!c) return [];
  const names = new Set(c.repos.map(n=>n.toLowerCase()));
  const base = Object.values(D.repos).filter(r=>names.has(r.full_name.toLowerCase()));
  const custom = getCustom().map(n=>D.repos[n]).filter(Boolean).filter(r=>!base.includes(r));
  return [...base, ...custom];
}

function renderTabs(){
  document.getElementById('tabs').innerHTML = TABS.map(t=>
    '<div class="tab'+(state.tab===t.id?' on':'')+'" onclick="setTab(\''+t.id+'\')">'+t.name+'</div>').join('');
}

function renderGroupTab(t){
  const subs = D.categories.filter(c=>c.group===t.group);
  let cur = state.sub[t.group];
  if(!cur || !subs.find(c=>c.id===cur)) cur = subs[0].id;
  state.sub[t.group] = cur;
  // 有 subgroup 的分类按组分段展示（如 综合→个人创意/行业提效）
  const groups = [];
  const seen = new Set();
  for(const c of subs){
    const sg = c.subgroup || '';
    if(!seen.has(sg)){ seen.add(sg); groups.push([sg, []]); }
    groups.find(g=>g[0]===sg)[1].push(c);
  }
  const pills = groups.map(([sg, cs])=>
    (sg ? '<span class="sg">'+sg+'</span>' : '')
    + cs.map(c=>'<span class="pill'+(cur===c.id?' on':'')+'" onclick="setSub(\''+t.group+'\',\''+c.id+'\')">'+c.name+'</span>').join('')
  ).join('');
  const list = reposOfCat(cur);
  return '<div class="pills">'+pills+'</div>' + modeBar() + tableHtml(sortBy(list, state.mode), state.mode);
}

function renderMain(){
  const m = document.getElementById('main');
  if(state.q){
    const all = Object.values(D.repos).filter(r=>matchQ(r,state.q));
    m.innerHTML = modeBar() + tableHtml(sortBy(all, state.mode).slice(0,60), state.mode)
      + '<div class="muted" style="margin-top:8px">搜索到 '+all.length+' 个项目（清空搜索框返回）</div>' + footHtml();
    renderAdv(m); return;
  }
  const t = TABS.find(x=>x.id===state.tab) || TABS[0];
  let html = '';
  if(t.id==='hot'){
    const list = D.top_gain.map(n=>D.repos[n]).filter(Boolean);
    html = '<div class="warn">提醒：涨得快 ≠ 一定好，有些是短期炒作。新项目建议观望两周再跟进。</div>' + tableHtml(list, 'gain');
  } else if(t.id==='top'){
    html = tableHtml(D.top_star.map(n=>D.repos[n]).filter(Boolean), 'star');
  } else if(t.group){
    html = renderGroupTab(t);
  } else {
    html = modeBar() + tableHtml(sortBy(reposOfCat(t.cat), state.mode), state.mode);
  }
  m.innerHTML = html + footHtml();
  renderAdv(m);
}
function footHtml(){
  return '<div class="foot">仅收录开源（免费可自建）软件 · Obsidian / Notion 等闭源软件不在榜内 · 点任意一行直达 GitHub 项目页</div>';
}
function renderAdv(m){
  const div = document.createElement('div');
  div.innerHTML = '<div class="adv"><span onclick="document.getElementById(\'advbox\').classList.toggle(\'show\')">高级：添加我关注的仓库 ▸</span></div>'
    + '<div class="adv-box" id="advbox"><input id="custom-repo" placeholder="作者/仓库名，如 ollama/ollama"> <button onclick="addCustom()">添加</button>'
    + '<div class="muted" style="margin-top:6px">只加到你自己的浏览器；增速从下周开始统计。</div></div>';
  m.appendChild(div);
}

function renderAll(){ renderTabs(); renderMain(); }
function setTab(t){ state.tab=t; localStorage.setItem(LS_TAB,t); renderAll(); }
function setSub(g,id){ state.sub[g]=id; localStorage.setItem(LS_SUB,JSON.stringify(state.sub)); renderAll(); }
function setMode(mo){ state.mode=mo; localStorage.setItem(LS_MODE,mo); renderAll(); }
function onSearch(){ state.q=document.getElementById('search').value.trim(); renderMain(); }

async function addCustom(){
  const inp = document.getElementById('custom-repo');
  const name = inp.value.trim();
  if(!name || !name.includes('/')) { alert('格式：作者/仓库名'); return; }
  try{
    const resp = await fetch('https://api.github.com/repos/'+encodeURIComponent(name));
    if(!resp.ok){ alert('没找到这个仓库（'+resp.status+'）'); return; }
    const d = await resp.json();
    D.repos[d.full_name] = { full_name:d.full_name, name:d.name, url:d.html_url, description:d.description||'',
      description_zh:'', plain:'', stars:d.stargazers_count, forks:d.forks_count, language:d.language||'', pushed_at:d.pushed_at,
      created_at:d.created_at, license:(d.license&&d.license.spdx_id)||'', week_gain:null, week_gain_pct:null, categories:[] };
    const c = getCustom(); if(!c.includes(d.full_name)){ c.push(d.full_name); localStorage.setItem(LS_CUSTOM, JSON.stringify(c)); }
    inp.value=''; renderAll(); alert('已添加：'+d.full_name+'（在综合领域标签下可见）');
  }catch(e){ alert('网络失败，稍后再试'); }
}

renderAll();
</script>
</body>
</html>
'''


if __name__ == '__main__':
    main()
