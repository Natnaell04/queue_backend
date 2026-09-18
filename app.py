import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from ami import AMIConnector

load_dotenv()

app = Flask(__name__)
CORS(app)

ami = AMIConnector(
    host=os.getenv("AMI_HOST", "127.0.0.1"),
    port=int(os.getenv("AMI_PORT", 5038)),
    user=os.getenv("AMI_USER", "queue_backend"),
    secret=os.getenv("AMI_SECRET", "queue123")
)

@app.route('/', methods=['GET'])
def index():
    return jsonify({'status': 'online', 'message': 'API is running. Query /api/queues'}), 200


@app.route('/api/queues', methods=['GET'])
def get_queues():
    try:
        data = ami.get_queue_data()
        return jsonify({'status': 'success', 'data': data}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/agent/pause', methods=['POST'])
def pause_agent():
    req = request.get_json(force=True)
    action = {
        'Action': 'QueuePause',
        'Interface': req.get('interface'),
        'Queue': req.get('queue'),
        'Reason': req.get('reason', 'Break'),
        'Paused': 'true' if req.get('paused') else 'false'
    }
    try:
        ami.send_command(action)
        return jsonify({'status': 'success', 'message': 'Pause status updated'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/call/hangup', methods=['POST'])
def hangup_call():
    req = request.get_json(force=True)
    action = {
        'Action': 'Hangup',
        'Channel': req.get('channel')
    }
    try:
        ami.send_command(action)
        return jsonify({'status': 'success', 'message': 'Call hung up'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(
        os.getenv("FLASK_PORT", 5000)), debug=True)
