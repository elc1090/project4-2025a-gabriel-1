#import eventlet
#eventlet.monkey_patch()

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import os
import datetime
import json

from google.oauth2 import id_token
from google.auth.transport import requests

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

# Configura o CORS para todas as rotas da aplicação Flask
CORS(app, origins=cors_config, supports_credentials=True)

db = SQLAlchemy(app)
migrate = Migrate(app, db)
socketio = SocketIO(app, cors_allowed_origins=cors_config, async_mode='gevent')

# Tabela de associação para o acesso do usuário aos quadros
whiteboard_access = db.Table('whiteboard_access',
    db.Column('user_id', db.String(255), db.ForeignKey('users.id'), primary_key=True),
    db.Column('whiteboard_id', db.Integer, db.ForeignKey('whiteboards.id'), primary_key=True)
)

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String(255), primary_key=True) # Google's user ID
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    profile_pic = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    owned_whiteboards = db.relationship('Whiteboard', backref='owner', lazy='dynamic')
    accessible_whiteboards = db.relationship('Whiteboard', secondary=whiteboard_access, back_populates='accessible_by_users', lazy='dynamic')

    def __repr__(self):
        return f'<User id={self.id} name={self.name}>'

class Whiteboard(db.Model):
    __tablename__ = 'whiteboards'

    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    owner_id = db.Column(db.String(255), db.ForeignKey('users.id'), nullable=False)
    
    strokes = db.relationship('Stroke', backref='whiteboard', lazy=True, cascade="all, delete-orphan")
    accessible_by_users = db.relationship('User', secondary=whiteboard_access, back_populates='accessible_whiteboards', lazy='dynamic')

    def __repr__(self):
        return f'<Whiteboard id={self.id} nickname={self.nickname}>'

class Stroke(db.Model):
    __tablename__ = 'stroke' # Nome explícito da tabela

    id = db.Column(db.Integer, primary_key=True)
    whiteboard_id = db.Column(db.Integer, db.ForeignKey('whiteboards.id'), nullable=False)
    
    color = db.Column(db.String(7), nullable=False) # Ex: #RRGGBB
    line_width = db.Column(db.Float, nullable=False)
    
    points_json = db.Column(db.Text, nullable=False) # [{"x":10,"y":20},{"x":12,"y":22}, ...]

    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow) # Quando o traço foi concluído/salvo

    def __repr__(self):
        return f'<Stroke id={self.id} board_id={self.whiteboard_id} color={self.color}>'

@app.cli.command("ensure_default_whiteboard")
def ensure_default_whiteboard():
    """Garante que a lousa padrão (ID 1) exista."""
    default_board = Whiteboard.query.get(1)
    if not default_board:
        # Tenta encontrar um usuário para ser o "dono" inicial.
        # Pode ser o primeiro usuário do sistema ou um usuário admin específico.
        # Se nenhum usuário existir, a criação falhará, o que é esperado.
        first_user = User.query.first()
        if not first_user:
            print("Nenhum usuário no banco de dados. Não é possível criar a lousa padrão sem um dono.")
            print("Crie um usuário primeiro e depois rode este comando novamente.")
            return
            
        default_board = Whiteboard(id=1, nickname="Lousa Principal", owner_id=first_user.id)
        db.session.add(default_board)
        db.session.commit()
        print(f"Lousa padrão criada com ID 1 e proprietário {first_user.email}.")
    else:
        print("Lousa padrão (ID 1) já existe.")

@app.route('/')
def home():
    return "Backend Flask com SQLAlchemy e modelos Whiteboard/Stroke."

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
    """Chamado quando um cliente se conecta, mas não entra em nenhuma sala de lousa ainda."""
    print(f"Cliente {request.sid} conectado ao servidor.")
    emit('connection_established', {'message': 'Conectado ao servidor Socket.IO!', 'sid': request.sid})

@socketio.on('join_board')
def handle_join_board(data):
    """Chamado quando um cliente quer se juntar a uma lousa específica."""
    board_id = data.get('board_id')
    user_email = data.get('user_email') # O frontend precisa enviar o email do usuário

    if not board_id or not user_email:
        print(f"Tentativa de join sem board_id ou user_email pelo cliente {request.sid}")
        return
        
    user = User.query.filter_by(email=user_email).first()
    if not user:
        print(f"Usuário com email {user_email} não encontrado.")
        return

    board = Whiteboard.query.get(board_id)
    # Verifica se o usuário tem acesso à lousa
    if not board or user not in board.accessible_by_users:
        print(f"Usuário {user_email} sem acesso à lousa {board_id} ou lousa inexistente.")
        # Poderíamos emitir um erro de volta para o cliente aqui
        return

    room = f"board_{board_id}"
    join_room(room)
    print(f"Cliente {request.sid} (usuário {user_email}) entrou na sala {room}")

    try:
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
            # Este caso não deve acontecer por causa da verificação acima, mas por segurança...
            print(f"Lousa {board_id} não encontrada. Enviando desenho inicial vazio.")
            emit('initial_drawing', {'strokes': []})

    except Exception as e:
        print(f"Erro ao buscar/enviar dados iniciais do desenho para a lousa {board_id}: {e}")
        emit('initial_drawing', {'strokes': []})


@socketio.on('disconnect')
def handle_disconnect():
    """Chamado quando um cliente se desconecta."""
    # Não precisa fazer leave_room explicitamente aqui, o SocketIO geralmente cuida disso.
    print(f"Cliente {request.sid} desconectado")


@socketio.on('draw_stroke_event')
def handle_draw_stroke_event(data):
    """Recebe um traço completo do cliente e o retransmite para outros na mesma sala."""
    board_id = data.get('board_id')
    if not board_id:
        print("Evento de desenho recebido sem 'board_id'. Ignorando.")
        return

    print(f"Evento de desenho recebido para lousa {board_id}: {data.get('color')}, {len(data.get('points', []))} pontos")
    
    room = f"board_{board_id}"
    emit('stroke_received', data, room=room, include_self=False)

    try:
        board = db.session.get(Whiteboard, board_id)
        if not board:
            print(f"Lousa {board_id} não encontrada, não foi possível salvar o traço.")
            return

        new_stroke = Stroke(
            whiteboard_id=board.id,
            color=data['color'],
            line_width=data['lineWidth'],
            points_json=json.dumps(data['points'])
        )
        db.session.add(new_stroke)
        db.session.commit()
        print(f"Traço salvo no BD com ID {new_stroke.id} para a lousa {board.id}")
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao salvar traço no banco de dados: {e}")


@socketio.on('clear_canvas_event')
def handle_clear_canvas_event(data):
    """Recebe um evento para limpar o canvas de uma lousa específica e retransmite."""
    board_id = data.get('board_id')
    if not board_id:
        print("Evento para limpar canvas recebido sem 'board_id'. Ignorando.")
        return
        
    room = f"board_{board_id}"
    print(f"Evento para limpar canvas recebido para a sala {room}")
    emit('canvas_cleared', { 'board_id': board_id }, room=room, include_self=False) # Avisa outros clientes

    try:
        board = db.session.get(Whiteboard, board_id)
        if board:
            Stroke.query.filter_by(whiteboard_id=board.id).delete()
            db.session.commit()
            print(f"Traços da lousa {board.id} removidos do banco de dados.")
        else:
            print(f"Lousa {board_id} não encontrada para limpar traços.")
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao limpar traços do banco de dados: {e}")

# API para Lousas
@app.route('/api/whiteboards', methods=['GET'])
def get_whiteboards():
    user_email = request.args.get('email')
    if not user_email:
        return jsonify({"message": "Parâmetro 'email' é obrigatório"}), 400

    user = User.query.filter_by(email=user_email).first()
    if not user:
        return jsonify({"message": "Usuário não encontrado"}), 404

    boards = user.accessible_whiteboards.order_by(Whiteboard.created_at.asc()).all()
    
    boards_data = [{
        'id': board.id,
        'nickname': board.nickname,
        'owner_id': board.owner_id,
        'is_owner': board.owner_id == user.id
    } for board in boards]

    return jsonify(boards_data)

@app.route('/api/whiteboards', methods=['POST'])
def create_whiteboard():
    data = request.get_json()
    nickname = data.get('nickname')
    user_email = data.get('email')

    if not nickname or not user_email:
        return jsonify({"message": "Apelido ('nickname') e email do usuário são obrigatórios"}), 400

    user = User.query.filter_by(email=user_email).first()
    if not user:
        return jsonify({"message": "Usuário proprietário não encontrado"}), 404

    new_board = Whiteboard(
        nickname=nickname,
        owner_id=user.id
    )
    # Adiciona o criador à lista de acesso
    new_board.accessible_by_users.append(user)
    
    db.session.add(new_board)
    db.session.commit()

    return jsonify({
        "message": "Lousa criada com sucesso!",
        "whiteboard": {
            'id': new_board.id,
            'nickname': new_board.nickname,
            'owner_id': new_board.owner_id,
            'is_owner': True
        }
    }), 201

@app.route('/api/whiteboards/<int:board_id>', methods=['DELETE'])
def delete_whiteboard(board_id):
    user_email = request.args.get('email')
    if not user_email:
        return jsonify({"message": "Parâmetro 'email' é obrigatório para autenticação"}), 400
    
    if board_id == 1:
        return jsonify({"message": "A lousa principal não pode ser deletada."}), 403

    user = User.query.filter_by(email=user_email).first()
    if not user:
        return jsonify({"message": "Usuário não encontrado"}), 404
        
    board = Whiteboard.query.get(board_id)
    if not board:
        return jsonify({"message": "Lousa não encontrada"}), 404

    if board.owner_id != user.id:
        return jsonify({"message": "Apenas o dono pode deletar a lousa"}), 403

    db.session.delete(board)
    db.session.commit()

    return jsonify({"message": f"Lousa '{board.nickname}' deletada com sucesso."})
        

@app.route('/api/auth/google', methods=['POST'])
def google_auth():
    data = request.get_json()
    token = data.get('credential')
    client_id = os.environ.get('GOOGLE_CLIENT_ID')

    if not token:
        return jsonify({"message": "Missing token"}), 400
    
    if not client_id:
        print("ERRO: Variável de ambiente GOOGLE_CLIENT_ID não definida no backend.")
        return jsonify({"message": "Server configuration error"}), 500

    try:
        # Verificar o token com o Google
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), client_id)

        # Extrair informações do usuário
        user_id = idinfo['sub']
        user_email = idinfo['email']
        user_name = idinfo['name']
        user_picture = idinfo['picture']

        # 1. Encontrar ou preparar o objeto do usuário
        user = User.query.get(user_id)
        is_new_user = False
        if not user:
            is_new_user = True
            user = User(
                id=user_id,
                email=user_email,
                name=user_name,
                profile_pic=user_picture
            )
            db.session.add(user)

        # 2. Encontrar ou criar a lousa padrão
        default_board = Whiteboard.query.get(DEFAULT_BOARD_ID)
        if not default_board:
            # A lousa não existe, vamos criá-la e o usuário atual será o dono.
            default_board = Whiteboard(
                id=DEFAULT_BOARD_ID, 
                nickname="Lousa Principal", 
                owner_id=user.id
            )
            db.session.add(default_board)
        
        # 3. Garantir que o usuário tenha acesso
        # Esta verificação é importante para usuários existentes que podem não ter o acesso.
        if default_board not in user.accessible_whiteboards:
            user.accessible_whiteboards.append(default_board)
        
        # 4. Commit de todas as alterações
        db.session.commit()

        if is_new_user:
            print(f"Novo usuário criado: {user_name} ({user_email})")
        else:
            print(f"Usuário existente logado: {user.name} ({user.email})")

        # Futuramente, poderíamos gerar um token JWT aqui para sessões seguras
        return jsonify({
            "message": "Login successful",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "profile_pic": user.profile_pic
            }
        })

    except ValueError as e:
        # O token pode ser inválido
        print(f"Erro de verificação de token: {e}")
        return jsonify({"message": "Invalid token"}), 401
    except Exception as e:
        print(f"Erro inesperado durante a autenticação: {e}")
        db.session.rollback()
        return jsonify({"message": "An unexpected error occurred"}), 500


if __name__ == '__main__':
    print("Iniciando servidor Flask-SocketIO com Eventlet...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=True)