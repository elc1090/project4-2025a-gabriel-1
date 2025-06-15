# Projeto: Lousa Colaborativa

<img src="preview.gif" alt="desktop preview" width="720"/>

Acesso: [https://elc1090.github.io/project4-2025a-gabriel-1/](https://elc1090.github.io/project4-2025a-gabriel-1/)


### Desenvolvedor
Gabriel Bisognin Moro | Ciência da Computação


### Descrição do produto

Aplicação web de desenho compartilhado em tempo real, permite que múltiplos usuários desenhem simultaneamente em um canvas digital, visualizando as contribuições uns dos outros instantaneamente.

Funcionalidades principais incluem:

  - Autenticação de usuários via Google Sign-In para acessar a lousa.  
  - Uma tela de desenho interativa com capacidade de arrastar (pan) e aplicar zoom, acessível tanto por mouse quanto por gestos de toque (um dedo para desenhar, dois dedos para zoom/pan).  
  - Ferramentas de desenho com seleção de cor (através de uma paleta) e espessura do pincel.  
  - Um menu de contexto customizado, ativado por clique direito no desktop ou toque longo em dispositivos móveis, oferecendo opções para limpar o desenho e resetar a visualização.
  - Persistência dos desenhos, que são salvos no banco de dados e recarregados quando um usuário acessa ou atualiza a página.


### Desenvolvimento

Configuração inicial do projeto (Vue.js para frontend, Flask/Python para backend) e o setup para deploy no GitHub Pages e Render.  
Progressivamente, implementei  a interface de desenho no frontend, evoluindo de um canvas básico para uma versão com funcionalidades de arrastar (pan), zoom, e um menu de contexto customizado, adaptando-a para interações de mouse e toque (incluindo toque longo e gestos de pinça).
No backend, configurei SQLAlchemy com PostgreSQL para persistência de dados e o Flask-SocketIO (utilizando gevent após depurar questões com eventlet) para a comunicação em tempo real, essencial para a colaboração.  
Houve etapas significativas de depuração e refinamento, especialmente para:  
- Corrigir configurações de deploy no Render (Gunicorn, workers assíncronos, variáveis de ambiente).  
- Resolver problemas de CORS entre o frontend e o backend.  
- Garantir que as migrações do banco de dados funcionassem corretamente em um ambiente PostgreSQL novo.  
- Assegurar que as interações de toque fossem funcionais em dispositivos móveis.  
- Implementar o carregamento do estado do desenho ao conectar/recarregar a página.  

#### Tecnologias
**Frontend:**
- [Vue.js](https://vuejs.org/)
- [Vite](https://vitejs.dev/)
- [Socket.IO Client](https://socket.io/docs/v4/client-api/)
- [Google Sign-In for Websites](https://developers.google.com/identity/gsi/web)

**Backend:**
- [Flask](https://flask.palletsprojects.com/)
- [Flask-SocketIO](https://flask-socketio.readthedocs.io/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/)
- [Flask-Migrate](https://flask-migrate.readthedocs.io/)
- [Flask-Cors](https://flask-cors.corydolphin.com/)
- [google-auth](https://google-auth.readthedocs.io/) (para verificação de tokens do Google)
- [psycopg2](https://www.psycopg.org/)
- [Gunicorn](https://gunicorn.org/)
- [gevent](http://www.gevent.org/)

**Base de Dados:**
- [PostgreSQL](https://www.postgresql.org/)

**Plataformas de Hospedagem:**
- [GitHub Pages](https://pages.github.com/)
- [Render](https://render.com/)

#### Ambiente de desenvolvimento

- [Cursor](https://www.cursor.com/)    

#### Referências e créditos

- [Flask-SocketIO](https://flask-socketio.readthedocs.io/): Extensão Flask para adicionar suporte a WebSockets usando Socket.IO
- [gevent](http://www.gevent.org/): Um framework de rede baseado em corrotinas para Python (usado como worker do Gunicorn para Socket.IO)
- [Flask-Migrate](https://flask-migrate.readthedocs.io/): Extensão Flask para lidar com migrações de banco de dados SQLAlchemy 
- [Gemini](https://gemini.google.com/) criação de códigos repetitivos, ajuda com novas técnologias, debug e otimização.

Projeto entregue para a disciplina de [Desenvolvimento de Software para a Web](http://github.com/andreainfufsm/elc1090-2025a) em 2025a
