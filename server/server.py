#!/usr/bin/env python3
"""配方奶粉库存查询/对比 HTTP 服务。静态页 + JSON API，数据来自 _db/formula.db。"""
import json
import os
import sqlite3
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
DB = os.path.join(ROOT, "data", "formula.db")
WEB = os.path.join(ROOT, "web")
PORT = int(os.environ.get("PORT", "8899"))


def conn():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def norm(s):
    return (s or "").strip()


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _static(self, path):
        if path in ("", "/"):
            path = "/index.html"
        fp = os.path.join(WEB, path.lstrip("/"))
        fp = os.path.normpath(fp)
        if not fp.startswith(WEB) or not os.path.isfile(fp):
            self.send_error(404)
            return
        ct = "text/html; charset=utf-8" if fp.endswith(".html") else \
            "text/css" if fp.endswith(".css") else \
            "application/javascript" if fp.endswith(".js") else "text/plain"
        with open(fp, "rb") as f:
            b = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.end_headers()

    def do_POST(self):
        if urllib.parse.urlparse(self.path).path == "/api/savepdf":
            n = int(self.headers.get("Content-Length", 0))
            data = self.rfile.read(n)
            with open("/tmp/codex_cx72.pdf", "wb") as f:
                f.write(data)
            self._json({"saved": len(data)})
        else:
            self._json({"error": "no route"}, 404)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        p = u.path
        try:
            if p == "/api/stats":
                return self.stats()
            if p == "/api/products":
                return self.products(q)
            if p == "/api/brands":
                return self.brands(q)
            if p == "/api/meta":
                return self.meta()
            if p == "/api/flagdefs":
                return self.flagdefs()
            if p == "/api/limits":
                return self.limits(q)
            if p == "/api/recommend":
                return self.recommend(q)
            if p == "/api/product":
                return self.product(q)
            if p == "/api/compare":
                return self.compare(q)
            if p.startswith("/api/"):
                return self._json({"error": "no route"}, 404)
            return self._static(p)
        except Exception as e:  # noqa: BLE001
            return self._json({"error": str(e)}, 500)

    # ---- API ----
    def stats(self):
        c = conn()
        s = {
            "total": c.execute("SELECT COUNT(*) n FROM product").fetchone()["n"],
            "fetched": c.execute("SELECT COUNT(*) n FROM product WHERE detail_fetched=1").fetchone()["n"],
            "nutrients": c.execute("SELECT COUNT(*) n FROM nutrient").fetchone()["n"],
            "by_stage": {r["stage"]: r["n"] for r in c.execute("SELECT stage, COUNT(*) n FROM product GROUP BY stage")},
            "stage1_valid": c.execute("SELECT COUNT(*) n FROM product WHERE stage=1 AND status='有效'").fetchone()["n"],
            "in_table": c.execute("SELECT COUNT(*) n FROM product WHERE in_table=1").fetchone()["n"],
            "recommended": c.execute("SELECT COUNT(*) n FROM product WHERE is_recommended=1").fetchone()["n"],
            "mainstream": c.execute("SELECT COUNT(*) n FROM product WHERE is_mainstream=1").fetchone()["n"],
            "expired": c.execute("SELECT COUNT(*) n FROM product WHERE is_expired=1").fetchone()["n"],
            "rec_pool": c.execute("SELECT COUNT(*) n FROM product WHERE stage=1 AND status='有效' AND is_expired=0 AND in_table=0 AND is_mainstream=1").fetchone()["n"],
        }
        c.close()
        self._json(s)

    def products(self, q):
        c = conn()
        def flag(k):
            return q.get(k, [""])[0] == "1"
        where, args = [], []
        if q.get("stage"):
            where.append("stage=?")
            args.append(int(q["stage"][0]))
        if q.get("status"):
            where.append("status=?")
            args.append(q["status"][0])
        if q.get("country"):
            where.append("country=?")
            args.append(q["country"][0])
        if flag("goat"):
            where.append("is_goat=1")
        if flag("cow"):
            where.append("is_goat=0")
        if flag("in_table"):
            where.append("in_table=1")
        if flag("recommended"):
            where.append("is_recommended=1")
        if flag("mainstream"):
            where.append("is_mainstream=1")
        if flag("not_in_table"):
            where.append("in_table=0")
        if flag("expired"):
            where.append("is_expired=1")
        if flag("valid"):
            where.append("is_expired=0")
        if q.get("flag"):
            for fg in q["flag"][0].split(","):
                fg = fg.strip()
                if fg:
                    where.append("flags LIKE ?")
                    args.append("%" + fg + "%")
        if flag("fetched"):
            where.append("detail_fetched=1")
        if q.get("q"):
            kw = "%" + q["q"][0] + "%"
            where.append("(product_name LIKE ? OR brand LIKE ? OR company LIKE ? OR reg LIKE ?)")
            args += [kw, kw, kw, kw]
        wsql = ("WHERE " + " AND ".join(where)) if where else ""
        page = int(q.get("page", ["1"])[0])
        size = int(q.get("size", ["50"])[0])
        total = c.execute(f"SELECT COUNT(*) n FROM product {wsql}", args).fetchone()["n"]
        rows = c.execute(
            f"SELECT reg,brand,product_name,country,company,process,status,valid_until,"
            f"stage,is_goat,in_table,is_recommended,detail_fetched,n_nutrients,"
            f"flags,is_mainstream,is_expired "
            f"FROM product {wsql} ORDER BY in_table DESC,is_recommended DESC,status='有效' DESC,brand,reg "
            f"LIMIT ? OFFSET ?", args + [size, (page - 1) * size]).fetchall()
        c.close()
        self._json({"total": total, "page": page, "size": size,
                    "pages": (total + size - 1) // size,
                    "rows": [dict(r) for r in rows]})

    def brands(self, q):
        c = conn()
        w = "WHERE stage=?" if q.get("stage") else ""
        a = [int(q["stage"][0])] if q.get("stage") else []
        rs = c.execute(f"SELECT brand, COUNT(*) n FROM product {w} GROUP BY brand ORDER BY n DESC, brand", a).fetchall()
        c.close()
        self._json([dict(r) for r in rs])

    def meta(self):
        c = conn()
        m = {r["k"]: r["v"] for r in c.execute("SELECT k,v FROM meta")}
        c.close()
        self._json(m)

    def flagdefs(self):
        c = conn()
        rs = c.execute("SELECT name,category,tier,evidence,effect FROM flag_def").fetchall()
        c.close()
        self._json([dict(r) for r in rs])

    def limits(self, q):
        """参考带判定：产品营养成分(每100kJ) vs Codex/ESPGHAN/GB/ENA 参考区间"""
        import re
        c = conn()
        reg = q.get("reg", [""])[0]
        if reg:
            stg = c.execute("SELECT stage FROM product WHERE reg=?", (reg,)).fetchone()
            stage = (stg[0] if stg and stg[0] in (1, 2, 3) else 1)
            lms = [dict(r) for r in c.execute(
                "SELECT nutrient,basis,min_v,max_v,unit,source,kind FROM limits WHERE stage=? "
                "ORDER BY CASE kind WHEN 'domestic' THEN 0 ELSE 1 END", (stage,))]
        if reg:
            # 与 build_db 的 JUDGE_PATTERNS 保持一致
            pat = {
                "蛋白质": lambda n: n == "蛋白质",
                "脂肪": lambda n: n == "脂肪",
                "亚油酸": lambda n: n == "亚油酸",
                "α-亚麻酸": lambda n: n.startswith("α-亚麻酸"),
                "DHA": lambda n: "dha" in n.lower() or "二十二碳六烯酸" in n and "%" not in n,
                "ARA": lambda n: "ara" in n.lower() or "aa/ara" in n or ("二十碳四烯酸" in n and "%" not in n),
                "胆碱": lambda n: n == "胆碱",
                "牛磺酸": lambda n: n == "牛磺酸",
                "左旋肉碱": lambda n: "肉碱" in n,
                "核苷酸": lambda n: "核苷酸" in n,
                "肌醇": lambda n: n == "肌醇",
                "维生素D": lambda n: n.startswith("维生素D"),
                "铁": lambda n: n == "铁",
                "钙": lambda n: n == "钙",
                "锌": lambda n: n == "锌",
                "碘": lambda n: n == "碘",
                "钠": lambda n: n == "钠",
                "磷脂": lambda n: "磷脂" in n,
                "维生素A": lambda n: n.startswith("维生素A"),
                "维生素E": lambda n: n.startswith("维生素E"),
                "维生素K": lambda n: n.startswith("维生素K"),
                "维生素C": lambda n: n.startswith("维生素C"),
                "钾": lambda n: n == "钾",
                "磷": lambda n: n == "磷",
                "镁": lambda n: n == "镁",
                "硒": lambda n: n == "硒",
                "碳水化合物": lambda n: n.startswith("碳水化合物"),
            }
            nut = [dict(r) for r in c.execute("SELECT name,unit,per_100kj FROM nutrient WHERE reg=?", (reg,))]
            rows = []
            for lm in lms:
                f = pat.get(lm["nutrient"])
                val = val_unit = None
                if f:
                    for nrow in nut:
                        if f(nrow["name"]) and nrow["unit"] in ("g", "mg", "µg", "μg") and nrow["per_100kj"]:
                            try:
                                float(nrow["per_100kj"])
                            except ValueError:
                                continue
                            val, val_unit = nrow["per_100kj"], nrow["unit"]
                            break
                conv = {"g": 1000.0, "mg": 1.0, "µg": 0.001, "μg": 0.001}
                v = None
                if val is not None:
                    v = float(val) * (conv.get(val_unit, 1) / conv.get(lm["unit"], 1))
                verdict = "未列示"
                if v is not None:
                    lo, hi = lm["min_v"], lm["max_v"]
                    if lo is not None and v < lo:
                        verdict = "低于参考下限"
                    elif hi is not None and v > hi:
                        verdict = "高于参考上限"
                    elif hi is not None and v >= hi * 0.85:
                        verdict = "接近上限"
                    else:
                        verdict = "区间内"
                rows.append({**lm, "value": round(v, 3) if v is not None else None,
                             "value_unit": lm["unit"], "verdict": verdict})
            c.close()
            return self._json({"reg": reg, "rows": rows})
        c.close()
        self._json(lms)

    def recommend(self, q):
        c = conn()
        where = ["stage=1", "status='有效'", "is_expired=0", "in_table=0", "is_mainstream=1"]
        args = []
        if q.get("flag"):
            for fg in q["flag"][0].split(","):
                fg = fg.strip()
                if fg:
                    where.append("flags LIKE ?")
                    args.append("%" + fg + "%")
        if q.get("goat") == "1":
            where.append("is_goat=1")
        if q.get("cow") == "1":
            where.append("is_goat=0")
        wsql = "WHERE " + " AND ".join(where)
        size = int(q.get("size", ["500"])[0])
        rows = c.execute(
            f"SELECT reg,brand,product_name,country,company,process,valid_until,"
            f"is_goat,detail_fetched,n_nutrients,flags FROM product {wsql} "
            f"ORDER BY detail_fetched DESC,brand,reg LIMIT ?", args + [size]).fetchall()
        c.close()
        self._json({"rows": [dict(r) for r in rows]})

    def product(self, q):
        c = conn()
        reg = q.get("reg", [""])[0]
        pr = c.execute("SELECT * FROM product WHERE reg=?", (reg,)).fetchone()
        if not pr:
            return self._json({"error": "not found"}, 404)
        ns = c.execute("SELECT seq,name,unit,per_100kj,per_100g FROM nutrient WHERE reg=? ORDER BY seq", (reg,)).fetchall()
        c.close()
        self._json({"product": dict(pr), "nutrients": [dict(n) for n in ns]})

    def compare(self, q):
        c = conn()
        regs = [r for r in (q.get("regs", [""])[0]).split(",") if r]
        prods = []
        for reg in regs:
            pr = c.execute("SELECT * FROM product WHERE reg=?", (reg,)).fetchone()
            if pr:
                prods.append(dict(pr))
        # 营养成分按名称对齐
        order = []
        seen = set()
        cells = {}
        for pr in prods:
            ns = c.execute("SELECT seq,name,unit,per_100kj,per_100g FROM nutrient WHERE reg=? ORDER BY seq",
                           (pr["reg"],)).fetchall()
            for n in ns:
                key = norm(n["name"])
                if key not in seen:
                    seen.add(key)
                    order.append(key)
                cells[(pr["reg"], key)] = {"unit": n["unit"], "kj": n["per_100kj"], "g": n["per_100g"]}
        c.close()
        self._json({"products": prods, "nutrient_order": order, "cells": {f"{k[0]}|{k[1]}": v for k, v in cells.items()}})


if __name__ == "__main__":
    print(f"serving on http://127.0.0.1:{PORT}  db={DB}")
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
