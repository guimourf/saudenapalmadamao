from app.services.session_link import create_session_url
from app.services.meet import create_meet_link_from_hash
from app.services.auth import require_token
from app.utils.serializers import convert_to_serializable
from flask import jsonify, request
from flask_restx import Resource, Namespace
from app.extensions import api
from datetime import datetime
import os

ns = Namespace('servicos', description='Endpoints de Serviços')
api.add_namespace(ns, path='/servicos_')

@ns.route('healthcheck')
class HealthCheck(Resource):
    def get(self):
        """Health check da API"""
        return {
            'status': 'healthy',
            'message': 'API está funcionando corretamente',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'service': 'Saúde na Palma da Mão API',
            'environment': os.getenv('FLASK_ENV', 'development'),
            'uptime': 'OK'
        }, 200

@ns.route('link-meet')
class LinkMeet(Resource):
    @require_token
    def post(self):
        """Gerar link do Jitsi Meet"""
        data = request.get_json() or {}
        session_hash = data.get('session_hash')
        
        if not session_hash:
            return {
                'message': 'session_hash é obrigatório',
                'status': 'error'
            }, 400
        
        result = create_meet_link_from_hash(session_hash)
        
        if not result['success']:
            return {
                'message': result['error'],
                'status': 'error'
            }, 400
        
        return {
            'message': 'Link do Jitsi Meet criado com sucesso',
            'meet_link': result['meet_link'],
            'session_hash': result['session_hash'],
            'room_name': result['room_name'],
            'session_data': result['session_data']
        }, 200

@ns.route('jitsi_token')
class GenerateJitsiToken(Resource):
    @require_token
    def post(self):
        """Gera um token JWT assinado para autenticação no Jitsi"""
        data = request.get_json() or {}
        room_name = data.get('room_name') or data.get('roomName')
        user_name = data.get('user_name') or data.get('userName')
        role = data.get('role', 'participant')
        user_id = data.get('user_id') or data.get('userId')
        email = data.get('email')
        affiliation = data.get('affiliation')
        
        if not room_name or not user_name:
            return {
                'message': 'room_name e user_name são obrigatórios',
                'status': 'error'
            }, 400
        
        try:
            from app.services.jitsi_token import generate_jitsi_token
            out = generate_jitsi_token(
                room_name, user_name, role, user_id, email, affiliation
            )
            body = {
                'message': 'Token Jitsi gerado com sucesso',
                'status': 'success',
                'token': out['token'],
                'room_name': room_name,
                'user_name': user_name,
                'role': role,
                'jwt_payload': out['jwt_payload'],
                'expires_at_epoch': out['expires_at_epoch'],
                'expires_at': out['expires_at'],
            }
            if 'host_url' in out:
                body['host_url'] = out['host_url']
                body['guest_url'] = out['guest_url']
            return body, 200
            
        except Exception as e:
            return {
                'message': f'Erro ao gerar token Jitsi: {str(e)}',
                'status': 'error'
            }, 500
