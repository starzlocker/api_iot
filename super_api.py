import flask

app = flask.Flask(__name__)

@app.route('/transform', methods=['POST'])
def transform():
    data = flask.request.json
    transformed = process_object(data)
    return flask.jsonify(transformed)

if __name__ == '__main__':
    app.run(debug=True) 