#!/usr/bin/env python3
"""生成单文件离线版 _web/standalone.html：把 formula.db 全量数据压缩内联进 index.html，
用本地 JS 数据层替换 fetch API，浏览器双击即可使用（无需服务/数据库）。
可重复运行：改完 _web/index.html 或重建 formula.db 后重跑本脚本刷新快照。"""
import json
import os
import sqlite3

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
DB = os.path.join(ROOT, "data", "formula.db")
SRC = os.path.join(ROOT, "web", "index.html")
OUT = os.path.join(ROOT, "web", "standalone.html")
API_LINE = "const api=(p,q)=>fetch('/api/'+p+'?'+new URLSearchParams(q)).then(r=>r.json());"

DROP_COLS = {"infoshar_id", "company_en"}


def main():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    prods = []
    for r in c.execute("SELECT * FROM product ORDER BY reg"):
        d = {k: v for k, v in dict(r).items() if k not in DROP_COLS}
        prods.append(d)
    names, nidx = [], {}
    units, uidx = [], {}
    nut = []

    def ix(lst, mp, v):
        if v not in mp:
            mp[v] = len(lst)
            lst.append(v)
        return mp[v]

    for pi, d in enumerate(prods):
        for n in c.execute("SELECT seq,name,unit,per_100kj,per_100g FROM nutrient WHERE reg=? ORDER BY seq",
                           (d["reg"],)):
            nut.append([pi, ix(names, nidx, n["name"]), ix(units, uidx, n["unit"] or ""),
                        n["seq"], n["per_100kj"], n["per_100g"]])
    limits = [dict(r) for r in c.execute(
        "SELECT nutrient,basis,min_v,max_v,unit,source,stage,kind FROM limits "
        "ORDER BY stage,CASE kind WHEN 'domestic' THEN 0 ELSE 1 END")]
    flagdefs = [dict(r) for r in c.execute("SELECT name,category,tier,evidence,effect FROM flag_def")]
    meta = {r["k"]: r["v"] for r in c.execute("SELECT k,v FROM meta")}
    c.close()

    data = {"asof": meta.get("as_of", ""), "meta": meta, "flagdefs": flagdefs,
            "limits": limits, "names": names, "units": units, "p": prods, "n": nut}
    dj = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    shim = r"""const DATA=__DATA__;
const _NUTMAP=(()=>{const m=new Map();for(const [pi,ni,ui,seq,kj,g] of DATA.n){let a=m.get(pi);if(!a){a=[];m.set(pi,a);}a.push({seq,name:DATA.names[ni],unit:DATA.units[ui],per_100kj:kj,per_100g:g});}return m;})();
const _BYREG=new Map(DATA.p.map((x,i)=>[x.reg,i]));
const _nut=p=>_NUTMAP.get(p)||[];
const _bool=s=>s==='1';
function _pass(x,q){
 if(q.stage&&x.stage!=+q.stage)return false;
 if(q.status&&x.status!==q.status)return false;
 if(q.goat&&!x.is_goat)return false;
 if(q.cow&&x.is_goat)return false;
 if(q.in_table&&!x.in_table)return false;
 if(q.not_in_table&&x.in_table)return false;
 if(q.recommended&&!x.is_recommended)return false;
 if(q.mainstream&&!x.is_mainstream)return false;
 if(q.expired&&!x.is_expired)return false;
 if(q.valid&&x.is_expired)return false;
 if(q.fetched&&!x.detail_fetched)return false;
 if(q.flag)for(const fg of q.flag.split(',')){const s=fg.trim();if(s&&!(x.flags||'').split(',').includes(s))return false;}
 if(q.q){const kw=q.q.toLowerCase();const j=((x.product_name||'')+(x.brand||'')+(x.company||'')+x.reg).toLowerCase();if(!j.includes(kw))return false;}
 return true;}
const _sortk=(a,b)=>(b.in_table-a.in_table)||(b.is_recommended-a.is_recommended)||((b.status==='有效')-(a.status==='有效'))||(a.brand||'').localeCompare(b.brand||'','zh')||a.reg.localeCompare(b.reg);
function _products(q){const rows=DATA.p.filter(x=>_pass(x,q)).sort(_sortk);
 const page=+(q.page||1),size=+(q.size||50),total=rows.length;
 return {total,page,size,pages:Math.ceil(total/size)||1,rows:rows.slice((page-1)*size,(page-1)*size+size)};}
function _recommend(q){const rows=DATA.p.filter(x=>x.stage===1&&x.status==='有效'&&!x.is_expired&&!x.in_table&&x.is_mainstream)
 .filter(x=>_pass(x,{flag:q.flag,goat:q.goat,cow:q.cow})).sort((a,b)=>(b.detail_fetched-a.detail_fetched)||(a.brand||'').localeCompare(b.brand||'','zh')||a.reg.localeCompare(b.reg));
 return {rows:rows.slice(0,+(q.size||500))};}
function _stats(){const f=p=>DATA.p.filter(p).length;
 return {total:DATA.p.length,fetched:f(x=>x.detail_fetched),nutrients:DATA.n.length,
  by_stage:{'1':f(x=>x.stage===1),'2':f(x=>x.stage===2),'3':f(x=>x.stage===3)},
  stage1_valid:f(x=>x.stage===1&&x.status==='有效'),in_table:f(x=>x.in_table),recommended:f(x=>x.is_recommended),
  mainstream:f(x=>x.is_mainstream),expired:f(x=>x.is_expired),
  rec_pool:f(x=>x.stage===1&&x.status==='有效'&&!x.is_expired&&!x.in_table&&x.is_mainstream)};}
function _product(reg){const pi=_BYREG.get(reg);if(pi==null)return {error:'not found'};
 return {product:DATA.p[pi],nutrients:_nut(pi)};}
function _compare(regs){const ps=regs.map(r=>DATA.p[_BYREG.get(r)]).filter(Boolean);
 const order=[],seen=new Set(),cells={};
 for(const p of ps)for(const n of _nut(_BYREG.get(p.reg))){const k=(n.name||'').trim();
  if(!seen.has(k)){seen.add(k);order.push(k);}cells[p.reg+'|'+k]={unit:n.unit,kj:n.per_100kj,g:n.per_100g};}
 return {products:ps,nutrient_order:order,cells};}
const PAT={
 '蛋白质':n=>n==='蛋白质','脂肪':n=>n==='脂肪','亚油酸':n=>n==='亚油酸',
 'α-亚麻酸':n=>n.startsWith('α-亚麻酸'),'DHA':n=>/dha/i.test(n)||(n.includes('二十二碳六烯酸')&&!n.includes('%')),
 'ARA':n=>/ara/i.test(n)||n.toLowerCase().includes('aa/ara')||(n.includes('二十碳四烯酸')&&!n.includes('%')),
 '胆碱':n=>n==='胆碱','牛磺酸':n=>n==='牛磺酸','左旋肉碱':n=>n.includes('肉碱'),'核苷酸':n=>n.includes('核苷酸'),
 '肌醇':n=>n==='肌醇','维生素D':n=>n.startsWith('维生素D'),'铁':n=>n==='铁','钙':n=>n==='钙','锌':n=>n==='锌',
 '碘':n=>n==='碘','钠':n=>n==='钠','磷脂':n=>n.includes('磷脂'),'维生素A':n=>n.startsWith('维生素A'),
 '维生素E':n=>n.startsWith('维生素E'),'维生素K':n=>n.startsWith('维生素K'),'维生素C':n=>n.startsWith('维生素C'),
 '钾':n=>n==='钾','磷':n=>n==='磷','镁':n=>n==='镁','硒':n=>n==='硒','碳水化合物':n=>n.startsWith('碳水化合物')};
function _limits(q){
 if(!q.reg)return DATA.limits;
 const pi=_BYREG.get(q.reg);if(pi==null)return {reg:q.reg,rows:[]};
 const st=DATA.p[pi].stage,stage=[1,2,3].includes(st)?st:1;
 const conv={'g':1000,'mg':1,'µg':0.001,'μg':0.001};const rows=[];
 for(const lm of DATA.limits.filter(x=>x.stage===stage)){
  const f=PAT[lm.nutrient];let val=null,vu=null;
  if(f)for(const nr of _nut(pi)){if(f(nr.name)&&['g','mg','µg','μg'].includes(nr.unit)&&nr.per_100kj){const fv=parseFloat(nr.per_100kj);if(!isNaN(fv)){val=fv;vu=nr.unit;break;}}}
  let v=null;if(val!=null)v=val*(conv[vu]/conv[lm.unit]);
  let verdict='未列示';
  if(v!=null){const lo=lm.min_v,hi=lm.max_v;
   if(lo!=null&&v<lo)verdict='低于参考下限';
   else if(hi!=null&&v>hi)verdict='高于参考上限';
   else if(hi!=null&&v>=hi*0.85)verdict='接近上限';
   else verdict='区间内';}
  rows.push({...lm,value:v!=null?Math.round(v*1000)/1000:null,value_unit:lm.unit,verdict});}
 return {reg:q.reg,rows};}
const api=(p,q)=>Promise.resolve((()=>{
 if(p==='stats')return _stats();
 if(p==='products')return _products(q||{});
 if(p==='recommend')return _recommend(q||{});
 if(p==='product')return _product((q||{}).reg||'');
 if(p==='compare')return _compare(((q||{}).regs||'').split(',').filter(Boolean));
 if(p==='limits')return _limits(q||{});
 if(p==='flagdefs')return DATA.flagdefs;
 if(p==='meta')return DATA.meta;
 if(p==='brands'){const m={};for(const x of DATA.p)if(!(q&&q.stage)||x.stage===+q.stage)m[x.brand]=(m[x.brand]||0)+1;
  return Object.entries(m).map(([brand,n])=>({brand,n})).sort((a,b)=>b.n-a.n||(a.brand||'').localeCompare(b.brand||'','zh'));}
 return {error:'no route'};})());"""

    html = open(SRC, encoding="utf-8").read()
    if API_LINE not in html:
        raise SystemExit("api 行未找到——index.html 结构变了，请同步更新本生成器")
    html = html.replace(API_LINE, shim.replace("__DATA__", dj), 1)
    html = html.replace("注册配方对比 <span class=\"small\">数据来源：国家市场监督管理总局 特殊食品信息查询平台</span>",
                        "注册配方对比 <span class=\"small\">离线单文件版 · 数据快照 " + data["asof"] +
                        " · 来源：国家市场监督管理总局 特殊食品信息查询平台 · 重新生成：python server/gen_standalone.py</span>", 1)
    open(OUT, "w", encoding="utf-8").write(html)
    print(f"OK {OUT}  {os.path.getsize(OUT)/1e6:.2f} MB  products={len(prods)} nut_rows={len(nut)} limits={len(limits)}")


if __name__ == "__main__":
    main()
