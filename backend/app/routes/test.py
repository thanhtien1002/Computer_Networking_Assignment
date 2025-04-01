from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/test', methods=['GET'])
def test_route():
    return jsonify({"message": "This is a test route!"}), 200

if __name__ == '__main__':
    app.run(debug=True)