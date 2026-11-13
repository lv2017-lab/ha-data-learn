#!/usr/bin/env python3
"""
Print Bot - kho ma loi tu hoc (auto-learn store)

Chay doc lap canh Home Assistant. Chi dung thu vien chuan cua Python.
Home Assistant goi qua rest_command:
  POST   /learn            {"code": "E999", "text": "noi dung", "group_id": "..."}
  GET    /lookup?code=E999 -> {"found": true, "code": "E999", "text": "..."}
  GET    /list             -> {"count": n, "items": [{code, text, updated_at}, ...]}
  DELETE /learn?code=E999  -> xoa ma da hoc (ban cu van con trong bang history)

Bao mat tuy chon: dat bien moi truong PRINT_BOT_TOKEN, Home Assistant gui kem
header X-Token. Khong dat token thi ai trong LAN cung ghi duoc - chi nen dung
khi mang noi bo tin cay.

Du lieu: SQLite tai PRINT_DB_PATH (mac dinh /data/print_learn.db, khi chay
local thi ./print_learn.db). Moi lan ghi deu luu 1 ban vao bang history de
co the tra cuu / khoi phuc ban truoc.
"""
import csv
import io
import json
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

VN_TZ = timezone(timedelta(hours=7))

DB_PATH = os.environ.get("PRINT_DB_PATH", "./print_learn.db")
TOKEN = os.environ.get("PRINT_BOT_TOKEN", "")
PORT = int(os.environ.get("PRINT_BOT_PORT", "8765"))


def _migrate_learned(conn):
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='learned'"
    ).fetchone()
    if row and "PRIMARY KEY(code, group_id)" not in (row[0] or ""):
        conn.execute(
            """CREATE TABLE IF NOT EXISTS learned_v2 (
                   code TEXT NOT NULL,
                   text TEXT NOT NULL,
                   group_id TEXT DEFAULT '',
                   updated_at TEXT NOT NULL,
                   PRIMARY KEY(code, group_id)
               )"""
        )
        conn.execute(
            "INSERT OR REPLACE INTO learned_v2(code, text, group_id, updated_at) "
            "SELECT code, text, IFNULL(group_id, ''), updated_at FROM learned"
        )
        conn.execute("DROP TABLE learned")
        conn.execute("ALTER TABLE learned_v2 RENAME TO learned")
        conn.commit()


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS learned (
               code TEXT NOT NULL,
               text TEXT NOT NULL,
               group_id TEXT DEFAULT '',
               updated_at TEXT NOT NULL,
               PRIMARY KEY(code, group_id)
           )"""
    )
    _migrate_learned(conn)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS history (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               code TEXT NOT NULL,
               text TEXT NOT NULL,
               group_id TEXT DEFAULT '',
               saved_at TEXT NOT NULL,
               action TEXT NOT NULL DEFAULT 'upsert'
           )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS settings (
               key TEXT PRIMARY KEY,
               value TEXT NOT NULL
           )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS repair_logs (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               date_iso TEXT NOT NULL,
               device TEXT NOT NULL,
               position TEXT DEFAULT '',
               machine TEXT DEFAULT '',
               note TEXT DEFAULT '',
               group_id TEXT DEFAULT '',
               created_at TEXT NOT NULL
           )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS reminders (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               group_id TEXT DEFAULT '',
               content TEXT NOT NULL,
               remind_at INTEGER NOT NULL,
               sent INTEGER NOT NULL DEFAULT 0,
               created_at TEXT NOT NULL
           )"""
    )
    return conn


def parse_date_to_iso(raw):
    """Nhan 'dd/mm/yyyy' hoac 'yyyy-mm-dd'; rong/khong hop le -> hom nay (gio VN)."""
    raw = (raw or "").strip()
    if raw:
        for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
            try:
                return datetime.strptime(raw, fmt).date().isoformat()
            except ValueError:
                continue
    return datetime.now(VN_TZ).date().isoformat()


def iso_to_display(iso):
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return iso or ""


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_machine(raw):
    raw = (raw or "").strip()
    rest = raw[4:].strip() if raw.lower().startswith("máy ") else raw
    m = re.search(r"DC\s?(\d+)", rest.upper())
    if m:
        return f"DC{m.group(1)}"
    m = re.search(r"DÂY CHUYỀN\s?(\d+)", rest.upper())
    if m:
        return f"DC{m.group(1)}"
    if re.match(r"^\d", rest):
        return rest
    return raw


DEFAULT_BOT_NAMES = ["Lyly", "Ly Ly", "Ly Ky"]


def get_bot_names(conn, group=""):
    keys = [f"bot_names:{group}"] if group else []
    keys.append("bot_names")
    for key in keys:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        if row:
            try:
                names = json.loads(row[0])
                if isinstance(names, list) and names:
                    return [str(n) for n in names]
            except Exception:
                pass
    return list(DEFAULT_BOT_NAMES)


def clean_names(raw_names):
    out = []
    seen = set()
    for n in raw_names:
        name = re.sub(r"\s+", " ", str(n)).strip(" ,.!?")
        if not name or len(name) > 40:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(name)
        if len(out) >= 8:
            break
    return out


def save_bot_names(conn, names, group=""):
    names = clean_names(names)
    if not names:
        names = list(DEFAULT_BOT_NAMES)
    key = f"bot_names:{group}" if group else "bot_names"
    conn.execute(
        "INSERT INTO settings(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, json.dumps(names, ensure_ascii=False)),
    )
    conn.commit()
    return names


class Handler(BaseHTTPRequestHandler):
    def _json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self):
        if not TOKEN:
            return True
        return self.headers.get("X-Token", "") == TOKEN

    def _guard(self):
        if self._authorized():
            return True
        self._json(401, {"ok": False, "error": "unauthorized"})
        return False

    def do_GET(self):
        if not self._guard():
            return
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        if parsed.path == "/health":
            self._json(200, {"ok": True})
            return
        if parsed.path == "/lookup":
            code = (qs.get("code", [""])[0] or "").strip().upper()
            group = (qs.get("group_id", [""])[0] or "").strip()
            if not code:
                self._json(200, {"found": False, "code": "", "text": ""})
                return
            conn = db()
            rows = conn.execute(
                "SELECT text, updated_at, group_id FROM learned WHERE code = ?",
                (code,),
            ).fetchall()
            conn.close()
            row = None
            for r in rows:
                if r[2] == group:
                    row = r
                    break
            if row is None:
                for r in rows:
                    if r[2] == "":
                        row = r
                        break
            if row:
                self._json(
                    200,
                    {
                        "found": True,
                        "code": code,
                        "text": row[0],
                        "updated_at": row[1],
                        "group_id": row[2],
                    },
                )
            else:
                self._json(200, {"found": False, "code": code, "text": ""})
            return
        if parsed.path == "/logs":
            q = (qs.get("q", [""])[0] or "").strip()
            machine = (qs.get("machine", [""])[0] or "").strip().upper()
            log_group = (qs.get("group_id", [""])[0] or "").strip()
            try:
                limit = min(max(int(qs.get("limit", ["10"])[0]), 1), 100)
            except ValueError:
                limit = 10
            sql = "SELECT id, date_iso, device, position, machine, note FROM repair_logs WHERE 1=1"
            args = []
            if log_group:
                sql += " AND (group_id = ? OR group_id = '')"
                args.append(log_group)
            if q:
                sql += " AND (LOWER(device) LIKE ? OR LOWER(position) LIKE ? OR LOWER(note) LIKE ? OR LOWER(machine) LIKE ?)"
                like = f"%{q.lower()}%"
                args += [like, like, like, like]
            if machine:
                sql += " AND machine = ?"
                args.append(machine)
            sql += " ORDER BY date_iso DESC, id DESC LIMIT ?"
            args.append(limit)
            conn = db()
            rows = conn.execute(sql, args).fetchall()
            conn.close()
            self._json(
                200,
                {
                    "count": len(rows),
                    "items": [
                        {
                            "id": r[0],
                            "date": iso_to_display(r[1]),
                            "device": r[2],
                            "position": r[3],
                            "machine": r[4],
                            "note": r[5],
                        }
                        for r in rows
                    ],
                },
            )
            return
        if parsed.path == "/logs.csv":
            conn = db()
            rows = conn.execute(
                "SELECT date_iso, device, position, machine, note FROM repair_logs "
                "ORDER BY date_iso ASC, id ASC"
            ).fetchall()
            conn.close()
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(
                ["STT", "Tên Vật Tư", "Vị Trí Thay", "Ngày/Tháng/Năm", "Máy In", "Ghi chú"]
            )
            for i, r in enumerate(rows, 1):
                writer.writerow([i, r[1], r[2], iso_to_display(r[0]), r[3], r[4]])
            body = ("﻿" + buf.getvalue()).encode("utf-8")
            self.send_response(200)
            self.send_header(
                "Content-Type", "text/csv; charset=utf-8"
            )
            self.send_header(
                "Content-Disposition", "attachment; filename=nhat-ky-sua-chua.csv"
            )
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/bot-names":
            group = (qs.get("group_id", [""])[0] or "").strip()
            conn = db()
            names = get_bot_names(conn, group)
            conn.close()
            self._json(200, {"ok": True, "names": names})
            return
        if parsed.path == "/memory-epoch":
            group = (qs.get("group_id", [""])[0] or "").strip()
            conn = db()
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?",
                (f"memory_epoch:{group}",),
            ).fetchone()
            conn.close()
            epoch = 0
            if row:
                try:
                    epoch = int(row[0])
                except ValueError:
                    epoch = 0
            self._json(200, {"ok": True, "group_id": group, "epoch": epoch})
            return
        if parsed.path == "/reminders/due":
            now_ts = int(datetime.now(timezone.utc).timestamp())
            conn = db()
            rows = conn.execute(
                "SELECT id, group_id, content, remind_at FROM reminders "
                "WHERE sent = 0 AND remind_at <= ? ORDER BY remind_at LIMIT 20",
                (now_ts,),
            ).fetchall()
            conn.close()
            self._json(
                200,
                {
                    "ok": True,
                    "count": len(rows),
                    "items": [
                        {"id": r[0], "group_id": r[1], "content": r[2], "remind_at": r[3]}
                        for r in rows
                    ],
                },
            )
            return
        if parsed.path == "/reminders":
            group = (qs.get("group_id", [""])[0] or "").strip()
            conn = db()
            rows = conn.execute(
                "SELECT id, content, remind_at FROM reminders "
                "WHERE sent = 0 AND group_id = ? ORDER BY remind_at LIMIT 20",
                (group,),
            ).fetchall()
            conn.close()
            self._json(
                200,
                {
                    "ok": True,
                    "group_id": group,
                    "count": len(rows),
                    "items": [
                        {"id": r[0], "content": r[1], "remind_at": r[2]} for r in rows
                    ],
                },
            )
            return
        if parsed.path == "/list":
            conn = db()
            rows = conn.execute(
                "SELECT code, text, updated_at FROM learned ORDER BY code"
            ).fetchall()
            conn.close()
            self._json(
                200,
                {
                    "count": len(rows),
                    "items": [
                        {"code": r[0], "text": r[1], "updated_at": r[2]} for r in rows
                    ],
                },
            )
            return
        self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        if not self._guard():
            return
        parsed = urlparse(self.path)
        if parsed.path == "/log/update":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                data = json.loads(self.rfile.read(length) or b"{}")
            except Exception:
                self._json(400, {"ok": False, "error": "invalid json"})
                return
            try:
                log_id = int(str(data.get("id", "")).strip())
            except ValueError:
                self._json(400, {"ok": False, "error": "id must be a number"})
                return
            conn = db()
            row = conn.execute(
                "SELECT date_iso, device, position, machine, note FROM repair_logs WHERE id = ?",
                (log_id,),
            ).fetchone()
            if not row:
                conn.close()
                self._json(404, {"ok": False, "error": "log not found", "id": log_id})
                return
            date_iso, device, position, machine, note = row
            new_device = str(data.get("device", "")).strip()
            if new_device:
                device = new_device
            new_position = str(data.get("position", "")).strip()
            if new_position:
                position = new_position
            new_machine = str(data.get("machine", "")).strip()
            if new_machine:
                machine = normalize_machine(new_machine)
            new_note = str(data.get("note", "")).strip()
            if new_note:
                note = new_note
            raw_date = str(data.get("date", "")).strip()
            if raw_date:
                parsed_date = None
                for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
                    try:
                        parsed_date = datetime.strptime(raw_date, fmt).date().isoformat()
                        break
                    except ValueError:
                        continue
                if parsed_date is None:
                    conn.close()
                    self._json(400, {"ok": False, "error": "invalid date"})
                    return
                date_iso = parsed_date
            conn.execute(
                "UPDATE repair_logs SET date_iso = ?, device = ?, position = ?, machine = ?, note = ? WHERE id = ?",
                (date_iso, device, position, machine, note, log_id),
            )
            conn.commit()
            conn.close()
            self._json(
                200,
                {
                    "ok": True,
                    "id": log_id,
                    "date": iso_to_display(date_iso),
                    "device": device,
                    "position": position,
                    "machine": machine,
                    "note": note,
                },
            )
            return
        if parsed.path == "/log":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                data = json.loads(self.rfile.read(length) or b"{}")
            except Exception:
                self._json(400, {"ok": False, "error": "invalid json"})
                return
            device = str(data.get("device", "")).strip()
            if not device:
                self._json(400, {"ok": False, "error": "device is required"})
                return
            date_iso = parse_date_to_iso(str(data.get("date", "")))
            machine = normalize_machine(str(data.get("machine", "")))
            conn = db()
            cur = conn.execute(
                "INSERT INTO repair_logs(date_iso, device, position, machine, note, group_id, created_at) "
                "VALUES(?,?,?,?,?,?,?)",
                (
                    date_iso,
                    device,
                    str(data.get("position", "")).strip(),
                    machine,
                    str(data.get("note", "")).strip(),
                    str(data.get("group_id", "")).strip(),
                    now_iso(),
                ),
            )
            conn.commit()
            new_id = cur.lastrowid
            conn.close()
            self._json(
                200,
                {"ok": True, "id": new_id, "date": iso_to_display(date_iso)},
            )
            return
        if parsed.path == "/reminder":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                data = json.loads(self.rfile.read(length) or b"{}")
            except Exception:
                self._json(400, {"ok": False, "error": "invalid json"})
                return
            group = str(data.get("group_id", "")).strip()
            content = str(data.get("content", "")).strip()
            try:
                remind_at = int(data.get("remind_at", 0))
            except (TypeError, ValueError):
                remind_at = 0
            if not content or remind_at <= 0:
                self._json(400, {"ok": False, "error": "content/remind_at required"})
                return
            conn = db()
            cur = conn.execute(
                "INSERT INTO reminders(group_id, content, remind_at, sent, created_at) "
                "VALUES(?, ?, ?, 0, ?)",
                (group, content, remind_at, now_iso()),
            )
            conn.commit()
            rid = cur.lastrowid
            conn.close()
            self._json(200, {"ok": True, "id": rid, "group_id": group, "remind_at": remind_at})
            return
        if parsed.path == "/reminder/sent":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                data = json.loads(self.rfile.read(length) or b"{}")
            except Exception:
                self._json(400, {"ok": False, "error": "invalid json"})
                return
            try:
                rid = int(data.get("id", 0))
            except (TypeError, ValueError):
                rid = 0
            conn = db()
            cur = conn.execute("UPDATE reminders SET sent = 1 WHERE id = ?", (rid,))
            conn.commit()
            updated = cur.rowcount
            conn.close()
            self._json(200, {"ok": True, "id": rid, "updated": updated})
            return
        if parsed.path == "/memory-epoch/bump":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                data = json.loads(self.rfile.read(length) or b"{}")
            except Exception:
                self._json(400, {"ok": False, "error": "invalid json"})
                return
            group = str(data.get("group_id", "")).strip()
            conn = db()
            key = f"memory_epoch:{group}"
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            ).fetchone()
            epoch = 0
            if row:
                try:
                    epoch = int(row[0])
                except ValueError:
                    epoch = 0
            epoch += 1
            conn.execute(
                "INSERT INTO settings(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, str(epoch)),
            )
            conn.commit()
            conn.close()
            self._json(200, {"ok": True, "group_id": group, "epoch": epoch})
            return
        if parsed.path.startswith("/bot-names/"):
            try:
                length = int(self.headers.get("Content-Length", "0"))
                data = json.loads(self.rfile.read(length) or b"{}")
            except Exception:
                self._json(400, {"ok": False, "error": "invalid json"})
                return
            group = str(data.get("group_id", "")).strip()
            conn = db()
            current = get_bot_names(conn, group)
            if parsed.path == "/bot-names/replace":
                names = data.get("names", [])
                if isinstance(names, str):
                    names = names.split(",")
                current = save_bot_names(conn, names, group)
            elif parsed.path == "/bot-names/add":
                current = save_bot_names(conn, current + [data.get("name", "")], group)
            elif parsed.path == "/bot-names/remove":
                target = re.sub(r"\s+", " ", str(data.get("name", ""))).strip().lower()
                current = save_bot_names(
                    conn, [n for n in current if n.lower() != target], group
                )
            else:
                conn.close()
                self._json(404, {"ok": False, "error": "not found"})
                return
            conn.close()
            self._json(200, {"ok": True, "names": current})
            return
        if parsed.path != "/learn":
            self._json(404, {"ok": False, "error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            self._json(400, {"ok": False, "error": "invalid json"})
            return
        code = str(data.get("code", "")).strip().upper()
        text = str(data.get("text", "")).strip()
        group_id = str(data.get("group_id", "")).strip()
        if not code or not text:
            self._json(400, {"ok": False, "error": "code and text are required"})
            return
        ts = now_iso()
        conn = db()
        conn.execute(
            "INSERT INTO learned(code, text, group_id, updated_at) VALUES(?,?,?,?) "
            "ON CONFLICT(code, group_id) DO UPDATE SET text=excluded.text, "
            "group_id=excluded.group_id, updated_at=excluded.updated_at",
            (code, text, group_id, ts),
        )
        conn.execute(
            "INSERT INTO history(code, text, group_id, saved_at, action) "
            "VALUES(?,?,?,?,'upsert')",
            (code, text, group_id, ts),
        )
        conn.commit()
        conn.close()
        self._json(200, {"ok": True, "code": code, "updated_at": ts})

    def do_DELETE(self):
        if not self._guard():
            return
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        if parsed.path == "/reminder":
            raw_id = (qs.get("id", [""])[0] or "").strip()
            group = (qs.get("group_id", [""])[0] or "").strip()
            try:
                rid = int(raw_id)
            except ValueError:
                self._json(400, {"ok": False, "error": "id must be a number"})
                return
            conn = db()
            cur = conn.execute(
                "DELETE FROM reminders WHERE id = ? AND group_id = ?", (rid, group)
            )
            conn.commit()
            deleted = cur.rowcount
            conn.close()
            if deleted:
                self._json(200, {"ok": True, "deleted": deleted, "id": rid})
            else:
                self._json(404, {"ok": False, "error": "reminder not found"})
            return
        if parsed.path == "/log":
            raw_id = (qs.get("id", [""])[0] or "").strip()
            try:
                log_id = int(raw_id)
            except ValueError:
                self._json(400, {"ok": False, "error": "id must be a number"})
                return
            conn = db()
            row = conn.execute(
                "SELECT date_iso, device FROM repair_logs WHERE id = ?", (log_id,)
            ).fetchone()
            cur = conn.execute("DELETE FROM repair_logs WHERE id = ?", (log_id,))
            conn.commit()
            deleted = cur.rowcount
            conn.close()
            self._json(
                200,
                {
                    "ok": True,
                    "deleted": deleted,
                    "id": log_id,
                    "date": iso_to_display(row[0]) if row else "",
                    "device": row[1] if row else "",
                },
            )
            return
        if parsed.path == "/logs":
            date_iso = parse_date_to_iso(qs.get("date", [""])[0])
            del_group = (qs.get("group_id", [""])[0] or "").strip()
            conn = db()
            if del_group:
                cur = conn.execute(
                    "DELETE FROM repair_logs WHERE date_iso = ? AND (group_id = ? OR group_id = '')",
                    (date_iso, del_group),
                )
            else:
                cur = conn.execute(
                    "DELETE FROM repair_logs WHERE date_iso = ?", (date_iso,)
                )
            conn.commit()
            deleted = cur.rowcount
            conn.close()
            self._json(
                200,
                {"ok": True, "deleted": deleted, "date": iso_to_display(date_iso)},
            )
            return
        if parsed.path != "/learn":
            self._json(404, {"ok": False, "error": "not found"})
            return
        code = (qs.get("code", [""])[0] or "").strip().upper()
        del_group = (qs.get("group_id", [""])[0] or "").strip()
        if not code:
            self._json(400, {"ok": False, "error": "code is required"})
            return
        conn = db()
        if del_group:
            row = conn.execute(
                "SELECT text, group_id FROM learned WHERE code = ? AND group_id = ?",
                (code, del_group),
            ).fetchone()
            if not row:
                row = conn.execute(
                    "SELECT text, group_id FROM learned WHERE code = ? AND group_id = ''",
                    (code,),
                ).fetchone()
            if row:
                conn.execute(
                    "DELETE FROM learned WHERE code = ? AND group_id = ?",
                    (code, row[1]),
                )
            else:
                conn.execute(
                    "DELETE FROM learned WHERE code = ? AND group_id = ?",
                    (code, del_group),
                )
        else:
            row = conn.execute(
                "SELECT text, group_id FROM learned WHERE code = ?", (code,)
            ).fetchone()
            conn.execute("DELETE FROM learned WHERE code = ?", (code,))
        if row:
            conn.execute(
                "INSERT INTO history(code, text, group_id, saved_at, action) "
                "VALUES(?,?,?,?,'delete')",
                (code, row[0], row[1], now_iso()),
            )
        conn.commit()
        conn.close()
        self._json(200, {"ok": True, "code": code, "deleted": bool(row)})

    def log_message(self, fmt, *args):
        # Giu log ngan gon
        print("%s - %s" % (self.address_string(), fmt % args), flush=True)


if __name__ == "__main__":
    db().close()
    print(f"print-learn-server listening on :{PORT}, db={DB_PATH}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
