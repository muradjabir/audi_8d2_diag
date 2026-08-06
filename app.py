# app.py
from flask import Flask, render_template, jsonify, request, Response
import threading
import time
import json
import logging
from port_scanner import scan_ports, auto_select
from kwp1281 import KWP1281, KWP1281Exception
from dtc_db import decode_dtc
from meas_decoder import decode_measurement
from ecu_defs import HVAC_GROUPS, HVAC_ADDRESS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WebAPI")

app = Flask(__name__)

# Global state for KWP1281 connection
protocol = None
connection_lock = threading.Lock()
is_connected = False
ecu_info = {}
live_mode = False
live_group = 1

def keep_alive_thread():
    global is_connected, protocol, live_mode
    while True:
        time.sleep(0.5)
        with connection_lock:
            if is_connected and protocol and not live_mode:
                try:
                    # Send ACK periodically to keep connection alive if we aren't doing live polling
                    protocol.send_ack()
                    # Wait for ECU to respond (usually with an ACK)
                    protocol.receive_block()
                except Exception as e:
                    logger.error(f"Keep-alive failed: {e}")
                    is_connected = False

threading.Thread(target=keep_alive_thread, daemon=True).start()


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/ports')
def get_ports():
    ports = scan_ports()
    return jsonify({
        "ports": ports,
        "auto": auto_select()
    })

@app.route('/api/connect', methods=['POST'])
def connect():
    global protocol, is_connected, ecu_info
    data = request.json
    port = data.get('port')
    
    if not port:
        return jsonify({"success": False, "error": "No port provided"}), 400
        
    with connection_lock:
        if is_connected and protocol:
            try:
                protocol.disconnect()
            except:
                pass
                
        protocol = KWP1281(port)
        try:
            ecu_info = protocol.connect(HVAC_ADDRESS)
            is_connected = True
            return jsonify({
                "success": True,
                "ecu_info": ecu_info
            })
        except KWP1281Exception as e:
            is_connected = False
            return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/disconnect', methods=['POST'])
def disconnect():
    global protocol, is_connected
    with connection_lock:
        if protocol and is_connected:
            try:
                protocol.disconnect()
            except:
                pass
        is_connected = False
        return jsonify({"success": True})

@app.route('/api/status')
def status():
    return jsonify({
        "connected": is_connected,
        "ecu_info": ecu_info if is_connected else None
    })

@app.route('/api/dtcs')
def get_dtcs():
    global protocol, is_connected
    with connection_lock:
        if not is_connected or not protocol:
            return jsonify({"success": False, "error": "Not connected"}), 400
            
        try:
            raw_dtcs = protocol.read_dtcs()
            decoded = [decode_dtc(d['hi'], d['lo'], d['elaboration']) for d in raw_dtcs]
            return jsonify({
                "success": True,
                "dtcs": decoded
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/dtcs/clear', methods=['POST'])
def clear_dtcs():
    global protocol, is_connected
    with connection_lock:
        if not is_connected or not protocol:
            return jsonify({"success": False, "error": "Not connected"}), 400
            
        try:
            protocol.clear_dtcs()
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/meas/<int:group>')
def get_meas(group):
    global protocol, is_connected
    
    if group < 1 or group > 255:
         return jsonify({"success": False, "error": "Invalid group"}), 400
         
    with connection_lock:
        if not is_connected or not protocol:
            return jsonify({"success": False, "error": "Not connected"}), 400
            
        try:
            raw_meas = protocol.read_meas_block(group)
            decoded = [decode_measurement(m['formula'], m['a'], m['b']) for m in raw_meas]
            
            # Add labels if available
            group_info = HVAC_GROUPS.get(group, {"name": f"Group {group}", "fields": []})
            for i, meas in enumerate(decoded):
                if i < len(group_info["fields"]):
                    meas["label"] = group_info["fields"][i]
                else:
                    meas["label"] = f"Field {i+1}"
                    
            return jsonify({
                "success": True,
                "group": group,
                "name": group_info["name"],
                "measurements": decoded
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/meas/live/<int:group>')
def live_meas(group):
    global protocol, is_connected, live_mode, live_group
    
    live_mode = True
    live_group = group
    
    def generate():
        global is_connected, protocol, live_mode
        try:
            while live_mode and is_connected:
                with connection_lock:
                    if not is_connected or not protocol:
                        break
                    try:
                        raw_meas = protocol.read_meas_block(group)
                        decoded = [decode_measurement(m['formula'], m['a'], m['b']) for m in raw_meas]
                        
                        group_info = HVAC_GROUPS.get(group, {"name": f"Group {group}", "fields": []})
                        for i, meas in enumerate(decoded):
                            if i < len(group_info["fields"]):
                                meas["label"] = group_info["fields"][i]
                            else:
                                meas["label"] = f"Field {i+1}"
                                
                        data = {
                            "group": group,
                            "measurements": decoded
                        }
                        yield f"data: {json.dumps(data)}\n\n"
                    except Exception as e:
                        logger.error(f"Live polling error: {e}")
                        is_connected = False
                        break
                time.sleep(0.5) # Poll interval
        finally:
            live_mode = False

    return Response(generate(), mimetype='text/event-stream')
    
@app.route('/api/meas/live/stop', methods=['POST'])
def stop_live():
    global live_mode
    live_mode = False
    return jsonify({"success": True})


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True, threaded=True)
