"""
CDDA Meeting Manager - Fabric Lakehouse Backend.
Flask REST API that manages meeting agendas with data in Fabric.

Endpoints:
  GET  /                    - Serve HTML UI
  GET  /api/health         - Health check
  GET  /api/meetings        - List all meetings
  POST /api/meetings        - Create meeting
  GET  /api/meetings/<id>   - Get single meeting
  PUT  /api/meetings/<id>   - Update meeting
  DELETE /api/meetings/<id> - Delete meeting

  GET  /api/meetings/<id>/agenda      - Get agenda items for meeting
  POST /api/meetings/<id>/agenda      - Add agenda item
  PUT  /api/agenda/<id>               - Update agenda item
  DELETE /api/agenda/<id>             - Delete agenda item
"""

from flask import Flask, jsonify, request
import os
import config

server = Flask(__name__, static_folder='static', static_url_path='/static')
app = server

# ============================================================================
# HTML Routes
# ============================================================================

@app.route('/')
def serve_root():
    """Serve the main HTML interface."""
    try:
        app_dir = os.path.dirname(os.path.abspath(__file__))
        index_path = os.path.join(app_dir, 'static', 'index.html')
        if os.path.exists(index_path):
            with open(index_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content, 200, {'Content-Type': 'text/html; charset=utf-8'}
        return "index.html not found", 404
    except Exception as e:
        return f"Error: {str(e)}", 500

# ============================================================================
# Health & Status
# ============================================================================

@app.route('/api/health')
def health():
    """Health check endpoint."""
    try:
        return jsonify({
            'status': 'ok',
            'message': 'CDDA Meeting Manager running',
            'demo_mode': config.DEMO_MODE,
            'environment': config.APP_ENVIRONMENT
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ============================================================================
# Meetings API
# ============================================================================

@app.route('/api/meetings', methods=['GET'])
def get_meetings():
    """Get all meetings."""
    try:
        # Demo data for now
        meetings = [
            {
                'id': 'mtg_1',
                'title': 'CDDA Open Office Hours',
                'description': 'Regular forum for open discussions',
                'forum': 'ooh',
                'duration': 60,
            },
            {
                'id': 'mtg_2',
                'title': 'Clinical Design & Statistics Review',
                'description': 'Review forum for clinical design',
                'forum': 'cdsr',
                'duration': 90,
            }
        ]
        return jsonify({'success': True, 'data': meetings, 'count': len(meetings)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/meetings', methods=['POST'])
def create_meeting():
    """Create new meeting."""
    try:
        data = request.json or {}
        title = data.get('title', 'Untitled Meeting')
        description = data.get('description', '')
        duration = int(data.get('duration', 60))
        forum = data.get('forum', 'ooh')

        data_layer = fabric.get_data_layer()
        meeting_id = data_layer.create_meeting(title, description, duration, forum)

        if meeting_id:
            return jsonify({'success': True, 'data': {'id': meeting_id}})
        return jsonify({'success': False, 'error': 'Failed to create meeting'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/meetings/<meeting_id>', methods=['GET'])
def get_meeting(meeting_id):
    """Get single meeting."""
    try:
        data_layer = fabric.get_data_layer()
        meeting = data_layer.get_meeting(meeting_id)
        if meeting:
            return jsonify({'success': True, 'data': meeting})
        return jsonify({'success': False, 'error': 'Meeting not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/meetings/<meeting_id>', methods=['PUT'])
def update_meeting(meeting_id):
    """Update meeting."""
    try:
        data = request.json or {}
        data_layer = fabric.get_data_layer()
        success = data_layer.update_meeting(meeting_id, **data)

        if success:
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Failed to update'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/meetings/<meeting_id>', methods=['DELETE'])
def delete_meeting(meeting_id):
    """Delete meeting."""
    try:
        data_layer = fabric.get_data_layer()
        success = data_layer.delete_meeting(meeting_id)

        if success:
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Failed to delete'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# Agenda Items API
# ============================================================================

@app.route('/api/meetings/<meeting_id>/agenda', methods=['GET'])
def get_agenda(meeting_id):
    """Get agenda items for a meeting."""
    try:
        data_layer = fabric.get_data_layer()
        items = data_layer.get_agenda_items(meeting_id)
        return jsonify({'success': True, 'data': items, 'count': len(items)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/meetings/<meeting_id>/agenda', methods=['POST'])
def create_agenda_item(meeting_id):
    """Create agenda item."""
    try:
        data = request.json or {}
        title = data.get('title', 'Untitled')
        topic = data.get('topic', '')
        duration = int(data.get('duration', 15))
        presenter = data.get('presenter', '')

        data_layer = fabric.get_data_layer()
        item_id = data_layer.create_agenda_item(meeting_id, title, topic, duration, presenter)

        if item_id:
            return jsonify({'success': True, 'data': {'id': item_id}})
        return jsonify({'success': False, 'error': 'Failed to create item'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/agenda/<item_id>', methods=['PUT'])
def update_agenda_item(item_id):
    """Update agenda item."""
    try:
        data = request.json or {}
        data_layer = fabric.get_data_layer()
        success = data_layer.update_agenda_item(item_id, **data)

        if success:
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Failed to update'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/agenda/<item_id>', methods=['DELETE'])
def delete_agenda_item(item_id):
    """Delete agenda item."""
    try:
        data_layer = fabric.get_data_layer()
        success = data_layer.delete_agenda_item(item_id)

        if success:
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Failed to delete'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# Documents API
# ============================================================================

@app.route('/api/agenda/<item_id>/documents', methods=['GET'])
def get_documents(item_id):
    """Get documents for agenda item."""
    try:
        data_layer = fabric.get_data_layer()
        docs = data_layer.get_documents(item_id)
        return jsonify({'success': True, 'data': docs, 'count': len(docs)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500

if __name__ == "__main__":
    server.run(debug=True, port=8050)
