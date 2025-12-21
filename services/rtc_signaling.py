from typing import Dict, Any
from flask_socketio import emit, join_room, leave_room

class RTCSignalingServer:
    def __init__(self):
        self.rooms: Dict[str, set] = {}
        self.user_rooms: Dict[str, str] = {}
    
    def handle_join_call(self, data: Dict[str, Any]):
        """通話ルームに参加"""
        user_id = str(data.get('user_id'))
        room_id = str(data.get('room_id'))
        
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
        
        # 既存の通話ルームから退出
        if user_id in self.user_rooms:
            old_room = self.user_rooms[user_id]
            if old_room in self.rooms:
                self.rooms[old_room].discard(user_id)
                leave_room(old_room)
        
        # 新しい通話ルームに参加
        self.rooms[room_id].add(user_id)
        self.user_rooms[user_id] = room_id
        join_room(room_id)
        
        # 他の参加者に通知
        emit('user_joined_call', {
            'user_id': user_id
        }, room=room_id, skip_sid=True)
        
        # 現在の参加者リストを返す
        return {
            'participants': list(self.rooms[room_id])
        }
    
    def handle_leave_call(self, data: Dict[str, Any]):
        """通話ルームから退出"""
        user_id = str(data.get('user_id'))
        room_id = self.user_rooms.get(user_id)
        
        if room_id:
            if room_id in self.rooms:
                self.rooms[room_id].discard(user_id)
                if not self.rooms[room_id]:
                    del self.rooms[room_id]
            del self.user_rooms[user_id]
            leave_room(room_id)
            
            # 他の参加者に通知
            emit('user_left_call', {
                'user_id': user_id
            }, room=room_id)
    
    def handle_offer(self, data: Dict[str, Any]):
        """オファーの転送"""
        target_id = str(data.get('target'))
        room_id = self.user_rooms.get(str(data.get('sender')))
        
        if room_id and target_id:
            emit('rtc_offer', {
                'sdp': data.get('sdp'),
                'sender': data.get('sender')
            }, room=target_id)
    
    def handle_answer(self, data: Dict[str, Any]):
        """アンサーの転送"""
        target_id = str(data.get('target'))
        room_id = self.user_rooms.get(str(data.get('sender')))
        
        if room_id and target_id:
            emit('rtc_answer', {
                'sdp': data.get('sdp'),
                'sender': data.get('sender')
            }, room=target_id)
    
    def handle_ice_candidate(self, data: Dict[str, Any]):
        """ICE candidateの転送"""
        target_id = str(data.get('target'))
        room_id = self.user_rooms.get(str(data.get('sender')))
        
        if room_id and target_id:
            emit('ice_candidate', {
                'candidate': data.get('candidate'),
                'sender': data.get('sender')
            }, room=target_id)
    
    def handle_call_request(self, data: Dict[str, Any]):
        """通話リクエストの送信"""
        target_id = str(data.get('target'))
        sender_id = str(data.get('sender'))
        
        emit('incoming_call', {
            'from': sender_id,
            'room_id': data.get('room_id')
        }, room=target_id)
    
    def handle_call_response(self, data: Dict[str, Any]):
        """通話リクエストへの応答"""
        target_id = str(data.get('target'))
        sender_id = str(data.get('sender'))
        accepted = data.get('accepted', False)
        
        emit('call_response', {
            'from': sender_id,
            'accepted': accepted,
            'room_id': data.get('room_id')
        }, room=target_id)
