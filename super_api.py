from flask import Flask, request, jsonify
import os
import json 
import threading
from functools import wraps
import base64
import datetime

ordens_de_producao = {
    'REC00015': [
        {
            "id_ordem": "ORDEMPROD-0001",
            "desc_ordem_producao": "Ordem de Produção 001",
            "codigo_produto": "01-01-00001",
            "detalhes": "ABC-123",
            "qtde": "5",
            "dt_conclusao_estimada": datetime.date.today().isoformat()
        },
        {
            "id_ordem": "ORDEMPROD-0002",
            "desc_ordem_producao": "Ordem de Produção 002",
            "codigo_produto": "01-01-00002",
            "detalhes": "ABC-123",
            "qtde": "3",
            "dt_conclusao_estimada": datetime.date.today().isoformat()
        },
        {
            "id_ordem": "ORDEMPROD-0003",
            "desc_ordem_producao": "Ordem de Produção 003",
            "codigo_produto": "01-01-00003",
            "detalhes": "ABC-123",
            "qtde": "5000",
            "dt_conclusao_estimada": datetime.date.today().isoformat()
        }
    ] 
}

ordem_default = [
    {
        "id_ordem": "SEM OP ESPECIFICADA",
        "desc_ordem_producao": "",
        "codigo_produto": "",
        "detalhes": "",
        "qtde": "",
        "dt_conclusao_estimada": ""
    }
]

app = Flask(__name__)
counter = 0

def adicionar_registro(data, tipo='GET'):
    try:
        log_file = './log_requests.log' if tipo == 'POST' else './log_gets.log'
        with file_lock:
            with open(log_file, 'a', encoding='utf-8') as file:
                file.write(json.dumps(data, indent=2) + '\n\n')
                file.flush()
    except Exception as e:
        print(f"Erro ao escrever no arquivo: {e}")
            
            
file_lock = threading.Lock()

def validate_headers(required_headers=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Validar Content-Type
            if request.method == 'POST' and request.content_type != 'application/json':
                return jsonify({'error': 'Content-Type must be application/json'}), 400
            
            # Validar headers obrigatórios
            if required_headers:
                for header in required_headers:
                    if header not in request.headers:
                        return jsonify({'error': f'Missing required header: {header}'}), 400
            
            # Validar Authorization (exemplo)
            auth_header = request.headers.get('Authorization')
            print(auth_header)
            if auth_header:
                if auth_header.startswith('Bearer '):
                    token = auth_header.replace('Bearer ', '')
                    if token != '1234':  # Substitua pela sua validação
                        return jsonify({'error': 'Invalid token'}), 401
                    
                elif auth_header.startswith('Basic '):
                    token = auth_header.replace('Basic ', '')
                    if not validate_basic_auth(token):
                        return jsonify({'error': 'Invalid Basic Auth credentials'}), 401
                    # Aqui você pode validar o token Basic se necessário
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_basic_auth(encoded_credentials):
    try:
        decoded = base64.b64decode(encoded_credentials).decode('utf-8')
        username, password = decoded.split(':', 1)
        
        valid_users = {
            'david': '123',
            'adolfo': '123'
        }
        
        return valid_users.get(username) == password
    except (ValueError, TypeError):
        return False
        
    except Exception as e:
        return jsonify({'error': f'Invalid Basic Auth credentials: {str(e)}'}), 401
    

@app.route('/', methods=['GET'])
# @validate_headers(['User-Agent', 'Content-Type'])
def get():
    
    adicionar_registro(request.full_path, 'GET')
    
    id_machine = request.args.get('idmachine')
    search = request.args.get('search')
    
    data = ordens_de_producao.get(id_machine, None)
    
    if data is None:
        data = ordem_default

    elif len(data) > 0 and search:
        data = [ordem for ordem in data if search in ordem['id_ordem'] or search in ordem['codigo_produto']]

    adicionar_registro(data, 'GET')
    return jsonify(data)


@app.route('/', methods=['POST'])
@validate_headers(['User-Agent', 'Content-Type'])
def post():
    global counter
    try:        
        data = request.json
        if not counter:
            counter = 0
        if int(data['NAME'][-1]) % 2 != 0 and counter > 0:
            counter -= 1
            print(f'{data["NAME"]} falha numero {counter}')
            return jsonify({'error': 'Odd number in name'}), 400

        print(f'Recebido: {data["NAME"]}')

        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
                
        adicionar_registro(data, 'POST')
            
        counter = 5
        
        # if counter in range(1, 5):
        #     return ({'error': 'Erro mockado'}), 400
        auth_header = request.headers.get('Authorization')
        
        username = 'unknown'
        
        if auth_header and auth_header.startswith('Basic '):
            token = auth_header.replace('Basic ', '')
            decoded = base64.b64decode(token).decode('utf-8')
            username, _ = decoded.split(':', 1)
        elif auth_header and auth_header.startswith('Bearer '):
            username = 'token_user'

        return  ({
            'message': f'Dados recebidos com sucesso: {username} validado',
            'data': data
        }), 200
    except Exception as e:
        return jsonify({'error': f'Invalid JSON data: {str(e)}'}), 400
        

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='192.168.101.91', port=port, debug=True, threaded=True)
