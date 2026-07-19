import csv
import io
import json
import os
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(ROOT_DIR, "game_tracker.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game TEXT NOT NULL,
            participants TEXT NOT NULL,
            winner TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


init_db()


class GameTrackerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/entries":
            self._send_json(self._get_entries())
        elif parsed.path == "/api/export/csv":
            self._send_csv()
        else:
            self._serve_static(parsed.path)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/entries":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self._send_json({"error": "Ungültiges JSON"}, status=400)
            return

        game = (payload.get("game") or "").strip()
        winner = (payload.get("winner") or "").strip()
        participants = payload.get("participants") or []
        timestamp = payload.get("timestamp") or ""

        if not game or not winner or not isinstance(participants, list) or len(participants) < 2:
            self._send_json({"error": "Bitte gültige Daten übergeben"}, status=400)
            return

        if winner not in participants:
            self._send_json({"error": "Der Gewinner muss ein Teilnehmer sein"}, status=400)
            return

        self._save_entry(game, participants, winner, timestamp)
        self._send_json({"ok": True})

    def _get_entries(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT game, participants, winner, timestamp FROM games ORDER BY id DESC"
        ).fetchall()
        conn.close()

        return [
            {
                "game": row["game"],
                "participants": json.loads(row["participants"]),
                "winner": row["winner"],
                "timestamp": row["timestamp"],
            }
            for row in rows
        ]

    def _save_entry(self, game, participants, winner, timestamp):
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO games (game, participants, winner, timestamp) VALUES (?, ?, ?, ?)",
            (game, json.dumps(participants), winner, timestamp or ""),
        )
        conn.commit()
        conn.close()

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_csv(self):
        rows = self._get_entries()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Spiel", "Teilnehmer", "Gewinner", "Zeitstempel"])
        for row in rows:
            writer.writerow([
                row["game"],
                "; ".join(row["participants"]),
                row["winner"],
                row["timestamp"],
            ])

        body = output.getvalue().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", "attachment; filename=spiel-tracker.csv")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self, path):
        if path in ["", "/"]:
            path = "/test.html"
        if path.startswith("/"):
            path = path[1:]
        file_path = os.path.join(ROOT_DIR, path)
        if os.path.isdir(file_path):
            file_path = os.path.join(file_path, "test.html")

        if os.path.exists(file_path) and os.path.isfile(file_path):
            self.send_response(200)
            if file_path.endswith(".html"):
                self.send_header("Content-Type", "text/html; charset=utf-8")
            elif file_path.endswith(".css"):
                self.send_header("Content-Type", "text/css; charset=utf-8")
            else:
                self.send_header("Content-Type", "application/octet-stream")
            content = open(file_path, "rb").read()
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error(404)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 8000), GameTrackerHandler)
    print("Server läuft auf http://localhost:8000")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer beendet")
        server.server_close()
