class User:
    def __init__(self, username, peer_ip, peer_port, is_visitor=False):
        self.username = username
        self.peer_ip = peer_ip
        self.peer_port = peer_port
        self.is_visitor = is_visitor
        self.is_streaming = False
        self.is_receiving = False
        self.is_online = True
        self.last_seen = None
        
    def to_dict(self):
        return {
            "username": self.username,
            "peer_ip": self.peer_ip,
            "peer_port": self.peer_port,
            "is_visitor": self.is_visitor,
            "is_streaming": self.is_streaming,
            "is_receiving": self.is_receiving,
            "is_online": self.is_online,
            "last_seen": self.last_seen
        }
        
    @classmethod
    def from_dict(cls, data):
        user = cls(
            data["username"],
            data["peer_ip"],
            data["peer_port"],
            data.get("is_visitor", False)
        )
        user.is_streaming = data.get("is_streaming", False)
        user.is_receiving = data.get("is_receiving", False)
        user.is_online = data.get("is_online", True)
        user.last_seen = data.get("last_seen")
        return user 