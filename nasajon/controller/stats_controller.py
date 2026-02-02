from flask import Blueprint, jsonify
from nasajon.dao.neo4j_stats_dao import Neo4jStatsDAO
import logging

logger = logging.getLogger(__name__)

bp_stats = Blueprint('stats', __name__)

@bp_stats.route('/tickets/classification', methods=['GET'])
def stats_classification():
    try:
        dao = Neo4jStatsDAO()
        data = dao.get_ticket_status_distribution()
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp_stats.route('/tickets/sintomas', methods=['GET'])
def stats_sintomas():
    try:
        dao = Neo4jStatsDAO()
        data = dao.get_top_sintomas(limit=10)
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500