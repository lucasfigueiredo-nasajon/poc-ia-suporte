from flask import Blueprint, request, jsonify
from nasajon.dao.taxonomy_dao import TaxonomyDAO
import logging
import traceback

logger = logging.getLogger(__name__)

# Mantemos o nome do blueprint para compatibilidade com o wsgi.py
bp_taxonomy = Blueprint('taxonomy', __name__)

def _get_dao():
    """Helper para instanciar o DAO corretamente."""
    return TaxonomyDAO()

@bp_taxonomy.route('/nodes', methods=['GET'])
def list_nodes():
    """
    Lista nós filtrados por tipo.
    Ex: GET /nodes?type=recurso
    """
    try:
        t_type = request.args.get('type')
        if not t_type:
            return jsonify({"error": "Parâmetro 'type' é obrigatório"}), 400
        
        dao = _get_dao()
        nodes = dao.get_nodes(t_type)
        return jsonify(nodes), 200
    except Exception as e:
        logger.error(f"Erro ao listar nodes: {e}")
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

@bp_taxonomy.route('/nodes', methods=['POST'])
def create_node():
    try:
        data = request.get_json()
        
        if not data.get('type') or not data.get('name'):
            return jsonify({"error": "Campos 'type' e 'name' são obrigatórios"}), 400

        dao = _get_dao()
        meta = data.get('metadata', {})
        
        # Agora new_id recebe o ID (inteiro) ou None
        new_id = dao.create_node(
            taxonomy_type=data['type'],
            name=data['name'],
            description=data.get('description', ''),
            parent_id=data.get('parent_id'),
            metadata=meta
        )
        
        if new_id:
            # Retornamos o ID para o frontend usar
            return jsonify({"status": "created", "id": new_id}), 201
        return jsonify({"error": "Falha ao criar registro (Duplicado?)"}), 500
        
    except Exception as e:
        logger.error(f"Erro ao criar node: {e}")
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

@bp_taxonomy.route('/nodes/<int:node_id>', methods=['PUT'])
def update_node(node_id):
    """
    Atualiza um nó existente (nome, descrição, pai ou metadados).
    """
    try:
        data = request.get_json()
        dao = _get_dao()
        
        meta = data.get('metadata', {})
        
        success = dao.update_node(
            node_id=node_id,
            name=data['name'],
            description=data.get('description', ''),
            parent_id=data.get('parent_id'),
            metadata=meta
        )
        
        if success:
            return jsonify({"status": "updated"}), 200
        return jsonify({"error": "Falha ao atualizar registro"}), 500
        
    except Exception as e:
        logger.error(f"Erro ao atualizar node {node_id}: {e}")
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

@bp_taxonomy.route('/nodes/<int:node_id>', methods=['DELETE'])
def delete_node(node_id):
    """
    Soft delete (apenas marca como inativo).
    """
    try:
        dao = _get_dao()
        success = dao.delete_node(node_id)
        
        if success:
            return jsonify({"status": "deleted"}), 200
        return jsonify({"error": "Falha ao deletar registro"}), 500
        
    except Exception as e:
        logger.error(f"Erro ao deletar node {node_id}: {e}")
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500