#import eventlet
#eventlet.monkey_patch()

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_socketio import SocketIO, emit, join_room, leave_room
import os
import datetime
import json

app = Flask(__name__)

env_cors_str = os.environ.get('CORS_ALLOWED_ORIGINS')

if env_cors_str == '*':
    cors_config = '*'
    print("CORS: Permitindo todas as origens ('*').")
elif env_cors_str:
    cors_config = [origin.strip() for origin in env_cors_str.split(',')]
    print(f"CORS: Origens permitidas configuradas via variável de ambiente: {cors_config}")
else:
    cors_config = ["https://elc1090.github.io"]
    print(f"CORS: Variável de ambiente CORS_ALLOWED_ORIGINS não definida. Usando fallback: {cors_config}")

DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or f'sqlite:///{os.path.join(app.instance_path, "desenho_local.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)
socketio = SocketIO(app, cors_allowed_origins=cors_config, async_mode='gevent')

class DrawingBoard(db.Model):
    __tablename__ = 'drawing_board'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=True, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    strokes = db.relationship('Stroke', backref='board', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<DrawingBoard id={self.id} name={self.name}>'

class Stroke(db.Model):
    __tablename__ = 'stroke' # Nome explícito da tabela

    id = db.Column(db.Integer, primary_key=True)
    drawing_board_id = db.Column(db.Integer, db.ForeignKey('drawing_board.id'), nullable=False)
    
    color = db.Column(db.String(7), nullable=False) # Ex: #RRGGBB
    line_width = db.Column(db.Float, nullable=False)
    
    points_json = db.Column(db.Text, nullable=False) # [{"x":10,"y":20},{"x":12,"y":22}, ...]

    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow) # Quando o traço foi concluído/salvo

    def __repr__(self):
        return f'<Stroke id={self.id} board_id={self.drawing_board_id} color={self.color}>'

@app.route('/')
def home():
    return "Backend Flask com SQLAlchemy e modelos DrawingBoard/Stroke."

@app.route('/api/status')
def status_api():
    try:
        db.session.execute(db.text('SELECT 1'))
        db_status = "conectado"
    except Exception as e:
        db_status = f"desconectado ({type(e).__name__}: {e})"
    return jsonify(message="API Flask está rodando!", database_status=db_status)

DEFAULT_BOARD_ID = 1

@socketio.on('connect')
def handle_connect():
    """Chamado quando um cliente se conecta."""
    room = str(DEFAULT_BOARD_ID)
    join_room(room)
    print(f"Cliente {request.sid} conectado e entrou na sala {room}")
    emit('connection_established', {'message': 'Conectado ao servidor Socket.IO!', 'sid': request.sid})

    try:
        board = db.session.get(DrawingBoard, DEFAULT_BOARD_ID)
        if board:
            existing_strokes_data = []
            for stroke_model in board.strokes:
                existing_strokes_data.append({
                    'id': stroke_model.id,
                    'color': stroke_model.color,
                    'lineWidth': stroke_model.line_width,
                    'points': json.loads(stroke_model.points_json)
                })
            emit('initial_drawing', {'strokes': existing_strokes_data})
        else:
            print(f"Quadro {DEFAULT_BOARD_ID} não encontrado. Enviando desenho inicial vazio.")
            emit('initial_drawing', {'strokes': []})

    except Exception as e:
        print(f"Erro ao buscar/enviar dados iniciais do desenho: {e}")
        emit('initial_drawing', {'strokes': []})


@socketio.on('disconnect')
def handle_disconnect():
    """Chamado quando um cliente se desconecta."""
    # Não precisa fazer leave_room explicitamente aqui, o SocketIO geralmente cuida disso.
    print(f"Cliente {request.sid} desconectado")


@socketio.on('draw_stroke_event')
def handle_draw_stroke_event(data):
    """Recebe um traço completo do cliente e o retransmite para outros na mesma sala."""
    # 'data' deve conter: { color: '...', lineWidth: ..., points: [{x,y}, ...] }
    # lineWidth aqui é a espessura no "mundo"
    print(f"Evento de desenho recebido: {data.get('color')}, {len(data.get('points', []))} pontos")
    
    room = str(DEFAULT_BOARD_ID)
    emit('stroke_received', data, room=room, include_self=False)

    try:
        board = db.session.get(DrawingBoard, DEFAULT_BOARD_ID)
        if not board:
            print(f"Quadro {DEFAULT_BOARD_ID} não encontrado, criando...")
            board = DrawingBoard(id=DEFAULT_BOARD_ID, name="Quadro Principal")
            db.session.add(board)

        new_stroke = Stroke(
            drawing_board_id=board.id,
            color=data['color'],
            line_width=data['lineWidth'],
            points_json=json.dumps(data['points'])
        )
        db.session.add(new_stroke)
        db.session.commit()
        print(f"Traço salvo no BD com ID: {new_stroke.id}")
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao salvar traço no banco de dados: {e}")


@socketio.on('clear_canvas_event')
def handle_clear_canvas_event(data): # data pode ser vazio ou conter board_id
    """Recebe um evento para limpar o canvas e retransmite."""
    room = str(DEFAULT_BOARD_ID)
    print(f"Evento para limpar canvas recebido para a sala {room}")
    emit('canvas_cleared', room=room, include_self=False) # Avisa outros clientes

    try:
        board = db.session.get(DrawingBoard, DEFAULT_BOARD_ID)
        if board:
            Stroke.query.filter_by(drawing_board_id=board.id).delete()
            db.session.commit()
            print(f"Traços do quadro {board.id} removidos do banco de dados.")
        else:
            print(f"Quadro {DEFAULT_BOARD_ID} não encontrado para limpar traços.")
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao limpar traços do banco de dados: {e}")
        

if __name__ == '__main__':
    print("Iniciando servidor Flask-SocketIO com Eventlet...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=True)