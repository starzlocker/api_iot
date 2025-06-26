from flask import Flask, request, jsonify
import os
import json 
import threading
app = Flask(__name__)

def adicionar_registro(data):
    try:
        with file_lock:
            with open('./log_requests.log', '+a', encoding='utf-8') as file:
                file.write(json.dumps(data, indent=2) + '\n\n')
                file.flush()
    except Exception as e:
        print(f"Erro ao escrever no arquivo: {e}")
            
            
file_lock = threading.Lock()
@app.route('/iot', methods=['POST'])
def iot():
    global counter
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
                
        adicionar_registro(data)
        if not counter:
            counter = 0
        counter += 1
        
        if counter in range(1, 5):
            return ({'error': 'Erro mockado'}), 400
        
        return  ({'message': 'OK'}), 200
    except Exception as e:
        return jsonify({'error': f'Invalid JSON data: {str(e)}'}), 400
        

@app.route('/', methods=['GET'])
def home():
    print('API accessed')
    return jsonify({'message': 'API is running! Send POST to /iot'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='192.168.101.91', port=port, debug=True, threaded=True)
    
    

        