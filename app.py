from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
import sqlite3
from datetime import datetime, timedelta
import os

app = Flask(__name__)
CORS(app)

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

print("🔥 EMERGENCY SYSTEM STARTED")

# =========================
# DB 초기화
# =========================
import sqlite3

def init_db():

    conn = sqlite3.connect("hospital.db")
    cur = conn.cursor()

    # =========================
    # 1️⃣ 테이블 생성 (기본 구조)
    # =========================
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

    # =========================
    # 2️⃣ 컬럼 존재 여부 체크 (핵심 개선)
    # =========================
    cur.execute("PRAGMA table_info(requests)")
    columns = cur.fetchall()

    column_names = [col[1] for col in columns]

    # =========================
    # 3️⃣ status 컬럼 없을 때만 추가
    # =========================
    if "status" not in column_names:
        cur.execute("""
        ALTER TABLE requests 
        ADD COLUMN status TEXT DEFAULT 'OPEN'
        """)

    # =========================
    # 4️⃣ 저장
    # =========================
    conn.commit()
    conn.close()


# =========================
# 5️⃣ 실행
# =========================
init_db()

# =========================
# WebSocket 연결
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
# 요청 생성 (실시간 push)
# =========================
@app.route("/request", methods=["POST"])
def create_request():

    data = request.json
    now = datetime.now()

    # ⏰ 30분 유효시간 (추천 실전값)
    expire = now + timedelta(minutes=30)

    conn = sqlite3.connect("hospital.db")
    cur = conn.cursor()

    for h in data["hospitals"]:

        h = h.strip()

        # =========================
        # 1️⃣ 기존 응답 여부 확인
        # =========================
        cur.execute("""
        SELECT response, expires_at
        FROM requests
        WHERE requestID=? AND hospital=?
        """, (data["requestID"], h))

        row = cur.fetchone()

        # 이미 응답 완료된 경우 → 재전송 안 함
        if row and row[0]:
            continue

        # =========================
        # 2️⃣ 데이터 저장 (없으면 생성)
        # =========================
        cur.execute("""
        INSERT OR IGNORE INTO requests (
            requestID,
            hospital,
            summary,
            eta,
            response,
            created_at,
            expires_at,
            status
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

        # =========================
        # 3️⃣ 실시간 전송 (WebSocket)
        # =========================
        socketio.emit("new_request", {
            "requestID": data["requestID"],
            "summary": data.get("summary", ""),
            "eta": data.get("eta", ""),
            "hospital": h,
            "expire": expire.strftime("%Y-%m-%d %H:%M:%S")
        }, room=h)

    conn.commit()
    conn.close()

    return jsonify({"status": "ok"})


# =========================
# 응답 처리 (1회 제한 + 10분 제한)
# =========================
@app.route("/response")
def response():

    requestID = request.args.get("requestID")
    hospital = request.args.get("hospital")
    resp = request.args.get("response")

    conn = sqlite3.connect("hospital.db")
    cur = conn.cursor()

    # =========================
    # 1️⃣ 데이터 조회 (한 번만)
    # =========================
    cur.execute("""
    SELECT response, expires_at
    FROM requests
    WHERE requestID=? AND hospital=?
    """, (requestID, hospital))

    row = cur.fetchone()

    # =========================
    # 2️⃣ 존재 여부
    # =========================
    if not row:
        conn.close()
        return "not found"

    # =========================
    # 3️⃣ CLOSED 체크 (강제 종료 핵심)
    # =========================
    if row[0] == "CLOSED":
        conn.close()
        return "closed request"

    # =========================
    # 4️⃣ 이미 응답했는지
    # =========================
    if row[0]:
        conn.close()
        return "already responded"

    # =========================
    # 5️⃣ 만료 체크
    # =========================
    if datetime.now() > datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S"):
        conn.close()
        return "expired"

    # =========================
    # 6️⃣ 응답 저장
    # =========================
    cur.execute("""
    UPDATE requests
    SET response=?
    WHERE requestID=? AND hospital=?
    """, (resp, requestID, hospital))

    conn.commit()
    conn.close()

    return "ok"


# =========================
# 상황실 조회
# =========================
@app.route("/status/<requestID>")
def status(requestID):

    conn = sqlite3.connect("hospital.db")
    cur = conn.cursor()

    # =========================
    # 1️⃣ 요청 데이터 조회
    # =========================
    cur.execute("""
    SELECT hospital, summary, eta, response, requestID
    FROM requests
    WHERE requestID=?
    """, (requestID,))

    rows = cur.fetchall()
    conn.close()

    # =========================
    # 2️⃣ 데이터 없을 때
    # =========================
    if not rows:
        return jsonify([])

    # =========================
    # 3️⃣ CLOSED 요청은 상황실에서 제외 (중요)
    # =========================
    result = []

    for r in rows:

        # CLOSED 상태는 화면에서 숨김
        if r[3] == "CLOSED":
            continue

        result.append({
            "hospital": r[0],
            "summary": r[1],
            "eta": r[2],
            "response": r[3],
            "requestID": r[4]
        })
    return jsonify(result)

# =========================
# ⭐ 강제 종료 API (여기 추가!)
# =========================
@app.route("/close/<requestID>")
def close(requestID):

    conn = sqlite3.connect("hospital.db")
    cur = conn.cursor()

    # 1️⃣ 상태 종료 처리 (핵심 수정)
    cur.execute("""
    UPDATE requests
    SET status='CLOSED'
    WHERE requestID=?
    """, (requestID,))

    conn.commit()
    conn.close()

    # 2️⃣ 병원 전체 종료 알림
    socketio.emit("close_request", {
        "requestID": requestID
    })

    return "closed"
    
# =========================
# 테스트 ⭐ (여기에 추가)
# =========================
@app.route('/test')
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
# Render 실행
# =========================
if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    socketio.run(app, host="0.0.0.0", port=port)
