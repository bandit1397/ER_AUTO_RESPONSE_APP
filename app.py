import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
import sqlite3
from datetime import datetime, timedelta
import os
import json

import firebase_admin
from firebase_admin import credentials, messaging

app = Flask(__name__)
CORS(app)

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# =========================
# Firebase Init
# =========================
cred_json = json.loads(os.environ["FIREBASE_CREDENTIALS"])
cred = credentials.Certificate(cred_json)
firebase_admin.initialize_app(cred)

print("🔥 EMERGENCY SYSTEM STARTED")

def send_fcm(token, title="긴급 요청", body="상황실 요청 도착"):

    message = messaging.Message(
        token=token,

        android=messaging.AndroidConfig(
            priority="high"
        ),

        data={
            "title": title,
            "body": body
        }
    )

    response = messaging.send(message)
    print("FCM SENT:", response)

    return response
# =========================
# FCM 전송 함수 (핵심 정리)
# =========================
def send_fcm(token, title="긴급 요청", body="상황실 요청 도착"):

    message = messaging.Message(

        token=token,

        data={
            "title": title,
            "body": body
        },

        android=messaging.AndroidConfig(
            priority="high",
            ttl=0   # ⭐ 핵심: 즉시 전달
        ),
    )

    response = messaging.send(message)
    print("FCM SENT:", response)

    return response


# =========================
# FCM 테스트 API
# =========================
@app.route("/send", methods=["POST"])
def send():

    data = request.json
    token = data.get("token")
    title = data.get("title", "긴급 요청")
    body = data.get("body", "상황실 요청 도착")

    if not token:
        return jsonify({"error": "no token"}), 400

    result = send_fcm(token, title, body)

    return jsonify({
        "status": "ok",
        "result": str(result)
    })


# =========================
# DB 초기화
# =========================
def init_db():

    conn = sqlite3.connect("hospital.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS requests (
        requestID TEXT,
        hospital TEXT,
        summary TEXT,
        eta TEXT,
        response TEXT,
        created_at TEXT,
        expires_at TEXT,
        UNIQUE(requestID, hospital)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS hospital_tokens (
        hospital TEXT PRIMARY KEY,
        token TEXT
    )
    """)

    cur.execute("PRAGMA table_info(requests)")
    columns = cur.fetchall()
    column_names = [col[1] for col in columns]

    if "status" not in column_names:
        cur.execute("""
        ALTER TABLE requests
        ADD COLUMN status TEXT DEFAULT 'OPEN'
        """)

    conn.commit()
    conn.close()


init_db()


# =========================
# WebSocket
# =========================
@socketio.on("connect")
def connect():
    print("client connected")


@socketio.on("join")
def join(data):
    hospital = data.get("hospital")
    join_room(hospital)
    print("joined:", hospital)


# =========================
# 토큰 저장
# =========================
@app.route("/save_token", methods=["POST"])
def save_token():

    data = request.json
    hospital = data.get("hospital")
    token = data.get("token")

    conn = sqlite3.connect("hospital.db")
    cur = conn.cursor()

    cur.execute("""
    INSERT OR REPLACE INTO hospital_tokens (hospital, token)
    VALUES (?, ?)
    """, (hospital, token))

    conn.commit()
    conn.close()

    return jsonify({"status": "saved"})


# =========================
# 요청 생성 + FCM PUSH
# =========================
@app.route("/request", methods=["POST"])
def create_request():

    data = request.json
    now = datetime.now()
    expire = now + timedelta(minutes=30)

    conn = sqlite3.connect("hospital.db")
    cur = conn.cursor()

    for h in data["hospitals"]:

        h = h.strip()

        cur.execute("""
        UPDATE requests
        SET status='CLOSED'
        WHERE hospital=? AND status='OPEN'
        """, (h,))

        cur.execute("""
        SELECT response FROM requests
        WHERE requestID=? AND hospital=?
        """, (data["requestID"], h))

        row = cur.fetchone()

        if row and row[0]:
            continue

        cur.execute("""
        INSERT OR IGNORE INTO requests (
            requestID, hospital, summary, eta,
            response, created_at, expires_at, status
        )
        VALUES (?, ?, ?, ?, '', ?, ?, 'OPEN')
        """, (
            data["requestID"],
            h,
            data.get("summary", ""),
            data.get("eta", ""),
            now.strftime("%Y-%m-%d %H:%M:%S"),
            expire.strftime("%Y-%m-%d %H:%M:%S")
        ))

        socketio.emit("new_request", {
            "requestID": data["requestID"],
            "summary": data.get("summary", ""),
            "eta": data.get("eta", ""),
            "hospital": h,
            "expire": expire.strftime("%Y-%m-%d %H:%M:%S")
        }, room=h)

        # =========================
        # FCM PUSH (정상 구조)
        # =========================
        cur.execute("""
        SELECT token FROM hospital_tokens WHERE hospital=?
        """, (h,))

        token_row = cur.fetchone()

        if token_row and token_row[0]:

            try:
                send_fcm(
                    token_row[0],
                    "🚨 긴급 요청",
                    data.get("summary", "새 요청")
                )

            except Exception as e:
                print("FCM ERROR:", e)

    conn.commit()
    conn.close()

    return jsonify({"status": "ok"})


# =========================
# 응답 처리
# =========================
@app.route("/response")
def response():

    requestID = request.args.get("requestID")
    hospital = request.args.get("hospital")
    resp = request.args.get("response")

    conn = sqlite3.connect("hospital.db")
    cur = conn.cursor()

    cur.execute("""
    SELECT response, expires_at, status
    FROM requests
    WHERE requestID=? AND hospital=?
    """, (requestID, hospital))

    row = cur.fetchone()

    if not row:
        return "not found"

    if row[2] == "CLOSED":
        return "closed"

    if row[0]:
        return "already responded"

    if datetime.now() > datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S"):
        return "expired"

    cur.execute("""
    UPDATE requests
    SET response=?
    WHERE requestID=? AND hospital=?
    """, (resp, requestID, hospital))

    conn.commit()
    conn.close()

    return "ok"


# =========================
# 최신 요청
# =========================
@app.route("/latest/<hospital>")
def latest(hospital):

    conn = sqlite3.connect("hospital.db")
    cur = conn.cursor()

    cur.execute("""
    SELECT requestID, summary, eta
    FROM requests
    WHERE hospital=? AND status='OPEN'
    ORDER BY created_at DESC
    LIMIT 1
    """, (hospital,))

    row = cur.fetchone()

    conn.close()

    if not row:
        return jsonify({})

    return jsonify({
        "requestID": row[0],
        "summary": row[1],
        "eta": row[2]
    })


# =========================
# 상태 조회
# =========================
@app.route("/status/<requestID>")
def status(requestID):

    conn = sqlite3.connect("hospital.db")
    cur = conn.cursor()

    cur.execute("""
    SELECT hospital, summary, eta, response, requestID
    FROM requests
    WHERE requestID=?
    """, (requestID,))

    rows = cur.fetchall()
    conn.close()

    result = []

    for r in rows:
        result.append({
            "hospital": r[0],
            "summary": r[1],
            "eta": r[2],
            "response": r[3],
            "requestID": r[4]
        })

    return jsonify(result)


# =========================
# 강제 종료
# =========================
@app.route("/close/<requestID>")
def close(requestID):

    conn = sqlite3.connect("hospital.db")
    cur = conn.cursor()

    cur.execute("""
    UPDATE requests
    SET status='CLOSED'
    WHERE requestID=?
    """, (requestID,))

    conn.commit()
    conn.close()

    socketio.emit("close_request", {
        "requestID": requestID
    })

    return "closed"


# =========================
# 테스트
# =========================
@app.route("/test")
def test():
    return "test ok"


# =========================
# 화면
# =========================
@app.route("/hospital/<name>")
def hospital(name):
    return render_template("hospital.html", hospital=name)


@app.route("/control")
def control():
    return render_template("control.html")


# =========================
# 실행
# =========================
if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
