import socket
import time


class AMIConnector:
    def __init__(self, host="127.0.0.1", port=5038, user="queue_backend", secret="queue123"):
        self.host = host
        self.port = port
        self.user = user
        self.secret = secret

    def _send_action(self, action_dict):
        """Connects to AMI via TCP socket, logs in, sends command, and returns response string."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((self.host, self.port))

        # Read welcome banner
        s.recv(1024)

        # Login Action
        login_cmd = f"Action: Login\r\nUsername: {self.user}\r\nSecret: {self.secret}\r\n\r\n"
        s.sendall(login_cmd.encode('utf-8'))

        # Send Target Action
        cmd_str = ""
        for k, v in action_dict.items():
            cmd_str += f"{k}: {v}\r\n"
        cmd_str += "\r\n"
        s.sendall(cmd_str.encode('utf-8'))

        # Logoff
        s.sendall(b"Action: Logoff\r\n\r\n")

        # Collect response
        response = ""
        while True:
            try:
                data = s.recv(4096).decode('utf-8', errors='ignore')
                if not data:
                    break
                response += data
            except socket.timeout:
                break

        s.close()
        return response

    def get_queue_data(self):
        """Queries QueueStatus and parses events into JSON structure."""
        raw_output = self._send_action({'Action': 'QueueStatus'})

        queues_data = {}
        events = raw_output.split('\r\n\r\n')

        for block in events:
            lines = block.split('\r\n')
            event_dict = {}
            for line in lines:
                if ':' in line:
                    key, val = line.split(':', 1)
                    event_dict[key.strip()] = val.strip()

            event = event_dict.get('Event', '')

            # Parse Queue Overview
            if event == 'QueueParams':
                q_name = event_dict.get('Queue')
                if q_name:
                    queues_data[q_name] = {
                        'name': q_name,
                        'calls_waiting': int(event_dict.get('Calls', 0)),
                        'completed': int(event_dict.get('Completed', 0)),
                        'abandoned': int(event_dict.get('Abandoned', 0)),
                        'service_level': event_dict.get('ServiceLevelPerf', '0.0%'),
                        'agents': [],
                        'callers': []
                    }

            # Parse Agents
            elif event == 'QueueMember':
                q_name = event_dict.get('Queue')
                if q_name in queues_data:
                    queues_data[q_name]['agents'].append({
                        'name': event_dict.get('Name'),
                        'location': event_dict.get('Location'),
                        # 1=Idle, 2=InUse, 5=Unavailable
                        'status': int(event_dict.get('Status', 0)),
                        'paused': event_dict.get('Paused') == '1',
                        'pause_reason': event_dict.get('PausedReason', 'N/A')
                    })

            # Parse Live Callers
            elif event == 'QueueEntry':
                q_name = event_dict.get('Queue')
                if q_name in queues_data:
                    queues_data[q_name]['callers'].append({
                        'caller_id': event_dict.get('CallerIDNum'),
                        'position': event_dict.get('Position'),
                        'wait_time': event_dict.get('Wait')
                    })

        return queues_data

    def send_command(self, action_data):
        return self._send_action(action_data)
