import flask
import os

app = flask.Flask(__name__)

def process_object(obj):
    """Transforma strings com vírgulas em arrays"""
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            result[key] = process_object(value)
        return result
    elif isinstance(obj, list):
        return [process_object(item) for item in obj]
    elif isinstance(obj, str):
        # Se contém vírgulas, transforma em array
        if ',' in obj:
            return obj.split(',')
        return obj
    else:
        return obj

@app.route('/transform', methods=['POST'])
def transform():
    try:
        data = flask.request.json
        if not data:
            return flask.jsonify({'error': 'No JSON data provided'}), 400
        
        transformed = process_object(data)
        return flask.jsonify({'transformed': transformed})
    except Exception as e:
        return flask.jsonify({'error': str(e)}), 500

@app.route('/', methods=['GET'])
def home():
    return flask.jsonify({'message': 'API is running! Send POST to /transform'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)