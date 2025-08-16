# server.py
from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import sqlite3
import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'replace_this_with_a_real_secret'
socketio = SocketIO(app, cors_allowed_origins="*")  # dev: allow all origins

DB = 'messages.db'

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  room TEXT,
                  sender TEXT,
                  text TEXT,
                  ts TEXT)''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return "Messaging server running."

@socketio.on('connect')
def on_connect():
    print('Client connected:', request.sid)
    emit('connected', {'sid': request.sid})

@socketio.on('join')
def on_join(data):
    room = data.get('room', 'global')
    username = data.get('username', 'anonymous')
    join_room(room)
    emit('status', {'msg': f'{username} joined {room}'}, room=room)

@socketio.on('leave')
def on_leave(data):
    room = data.get('room', 'global')
    username = data.get('username', 'anonymous')
    leave_room(room)
    emit('status', {'msg': f'{username} left {room}'}, room=room)

@socketio.on('send_message')
def handle_message(data):
    # expected data: {'room': 'global', 'sender': 'Zain', 'text': 'hello'}
    room = data.get('room', 'global')
    sender = data.get('sender', 'anonymous')
    text = data.get('text', '')
    ts = datetime.datetime.utcnow().isoformat() + 'Z'

    # persist
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO messages (room, sender, text, ts) VALUES (?, ?, ?, ?)",
              (room, sender, text, ts))
    conn.commit()
    conn.close()

    # broadcast to room
    emit('new_message', {'room': room, 'sender': sender, 'text': text, 'ts': ts}, room=room)

@socketio.on('load_history')
def load_history(data):
    room = data.get('room', 'global')
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT sender, text, ts FROM messages WHERE room=? ORDER BY id DESC LIMIT 200", (room,))
    rows = c.fetchall()
    conn.close()
    # send recent messages (reverse to chronological)
    rows.reverse()
    emit('history', {'room': room, 'messages': [{'sender': r[0], 'text': r[1], 'ts': r[2]} for r in rows]})

@socketio.on('disconnect')
def on_disconnect():
    print('Client disconnected:', request.sid)

if __name__ == '__main__':
    init_db()
    # for production: use eventlet/gevent + TLS; for development:
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)

