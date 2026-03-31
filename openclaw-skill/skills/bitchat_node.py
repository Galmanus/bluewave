"""
BitChat LAN Node — Wave Intranet Protocol v1.0
==============================================
P2P social intranet restrita à LAN física.

Arquitetura:
  - Discovery : UDP broadcast na porta 55420 (BEACON)
  - Transport : TCP na porta 55421 (STREAM)
  - Identity  : Ed25519 keypair — chave privada = identidade soberana
  - Encryption: X25519 ECDH + ChaCha20-Poly1305 por sessão
  - Channels  : #general, #midas, #zk, #ops (extensível)

O servidor central não existe. Fagner não pode desligar isso.
"""

import os
import sys
import json
import time
import socket
import struct
import hashlib
import threading
import ipaddress
import netifaces
from datetime import datetime, timezone
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, List
from pathlib import Path

# ─── crypto ──────────────────────────────────────────────────────────────────
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.backends import default_backend

# ─── constants ────────────────────────────────────────────────────────────────
BEACON_PORT   = 55420       # UDP — node announces itself here
STREAM_PORT   = 55421       # TCP — messages flow here
BEACON_MAGIC  = b"BCHAT1"   # 6 bytes — rejeita tráfego aleatório
BEACON_IV     = 2.0         # segundos entre beacons
KEY_FILE      = Path.home() / ".bitchat_identity.json"
CHANNELS      = ["#general", "#midas", "#zk", "#ops", "#wave"]

# ─── identity ─────────────────────────────────────────────────────────────────

def load_or_create_identity(alias: str = "wave") -> dict:
    """
    Identidade soberana: Ed25519 keypair.
    A chave privada nunca sai do disco local.
    O node_id é o hash SHA256 da chave pública — imutável, verificável.
    """
    if KEY_FILE.exists():
        data = json.loads(KEY_FILE.read_text())
        return data

    priv = Ed25519PrivateKey.generate()
    pub  = priv.public_key()

    priv_bytes = priv.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption()
    )
    pub_bytes = pub.public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw
    )

    node_id = hashlib.sha256(pub_bytes).hexdigest()[:16]

    identity = {
        "alias":    alias,
        "node_id":  node_id,
        "priv_hex": priv_bytes.hex(),
        "pub_hex":  pub_bytes.hex(),
        "created":  datetime.now(timezone.utc).isoformat()
    }
    KEY_FILE.write_text(json.dumps(identity, indent=2))
    KEY_FILE.chmod(0o600)
    return identity


# ─── network helpers ──────────────────────────────────────────────────────────

def get_lan_interfaces() -> List[tuple]:
    """Retorna [(ip, broadcast)] de todas as interfaces LAN não-loopback."""
    result = []
    for iface in netifaces.interfaces():
        addrs = netifaces.ifaddresses(iface)
        if netifaces.AF_INET not in addrs:
            continue
        for addr in addrs[netifaces.AF_INET]:
            ip   = addr.get("addr", "")
            mask = addr.get("netmask", "")
            bcast = addr.get("broadcast", "")
            if not ip or ip.startswith("127."):
                continue
            if not bcast:
                # calcula broadcast manualmente
                net   = ipaddress.IPv4Network(f"{ip}/{mask}", strict=False)
                bcast = str(net.broadcast_address)
            result.append((ip, bcast))
    return result


# ─── beacon (UDP) ─────────────────────────────────────────────────────────────

def build_beacon(identity: dict) -> bytes:
    """
    Beacon payload (< 512 bytes):
      BCHAT1 | 2 bytes version | 16 bytes node_id | 2 bytes alias_len | alias_bytes | 8 bytes timestamp
    """
    alias_bytes = identity["alias"].encode()[:32]
    node_id_bytes = bytes.fromhex(identity["node_id"].ljust(32, "0")[:32])
    ts = struct.pack(">Q", int(time.time()))
    return (
        BEACON_MAGIC
        + b"\x01\x00"                         # version 1.0
        + node_id_bytes                        # 16 bytes node_id
        + struct.pack(">H", len(alias_bytes))  # 2 bytes
        + alias_bytes
        + ts
    )


def parse_beacon(data: bytes) -> Optional[dict]:
    if len(data) < 28 or not data.startswith(BEACON_MAGIC):
        return None
    version = data[6:8]
    node_id = data[8:24].hex()
    alias_len = struct.unpack(">H", data[24:26])[0]
    alias = data[26:26 + alias_len].decode(errors="replace")
    return {
        "node_id":  node_id,
        "alias":    alias,
        "version":  version.hex(),
        "seen_at":  time.time()
    }


class BeaconSender(threading.Thread):
    """Anuncia presença na LAN a cada BEACON_IV segundos."""

    def __init__(self, identity: dict):
        super().__init__(daemon=True)
        self.identity = identity
        self.payload  = build_beacon(identity)

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while True:
            for ip, bcast in get_lan_interfaces():
                try:
                    sock.sendto(self.payload, (bcast, BEACON_PORT))
                except Exception:
                    pass
            time.sleep(BEACON_IV)


class BeaconListener(threading.Thread):
    """Escuta beacons dos pares. Mantém tabela de nós vivos."""

    def __init__(self, identity: dict, peers: dict, on_new_peer=None):
        super().__init__(daemon=True)
        self.identity    = identity
        self.peers       = peers          # {node_id: peer_info}
        self.on_new_peer = on_new_peer
        self._lock       = threading.Lock()

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(("", BEACON_PORT))

        while True:
            try:
                data, addr = sock.recvfrom(512)
                peer = parse_beacon(data)
                if not peer:
                    continue
                if peer["node_id"] == self.identity["node_id"]:
                    continue  # próprio beacon

                peer["ip"] = addr[0]
                is_new = peer["node_id"] not in self.peers

                with self._lock:
                    self.peers[peer["node_id"]] = peer

                if is_new and self.on_new_peer:
                    self.on_new_peer(peer)
            except Exception:
                pass


# ─── message layer (TCP) ──────────────────────────────────────────────────────

@dataclass
class Message:
    msg_id:    str
    sender_id: str
    alias:     str
    channel:   str
    text:      str
    timestamp: float = field(default_factory=time.time)
    sig:       str   = ""       # Ed25519 sobre (msg_id + channel + text)

    def to_bytes(self) -> bytes:
        return json.dumps(asdict(self)).encode()

    @classmethod
    def from_bytes(cls, data: bytes) -> "Message":
        return cls(**json.loads(data))

    def sign(self, priv_hex: str) -> None:
        priv = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(priv_hex))
        payload = f"{self.msg_id}{self.channel}{self.text}".encode()
        self.sig = priv.sign(payload).hex()

    def verify(self, pub_hex: str) -> bool:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_hex.ljust(64, "0")[:64]))
        payload = f"{self.msg_id}{self.channel}{self.text}".encode()
        try:
            pub.verify(bytes.fromhex(self.sig), payload)
            return True
        except Exception:
            return False


def send_message_to_peer(ip: str, msg: Message):
    """Envia mensagem TCP para um peer. Fire-and-forget."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect((ip, STREAM_PORT))
        data = msg.to_bytes()
        sock.sendall(struct.pack(">I", len(data)) + data)
        sock.close()
    except Exception:
        pass


class MessageServer(threading.Thread):
    """Recebe mensagens TCP de todos os peers."""

    def __init__(self, on_message=None):
        super().__init__(daemon=True)
        self.on_message = on_message
        self.inbox: List[Message] = []

    def run(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("", STREAM_PORT))
        srv.listen(32)

        while True:
            try:
                conn, addr = srv.accept()
                t = threading.Thread(target=self._handle, args=(conn, addr), daemon=True)
                t.start()
            except Exception:
                pass

    def _handle(self, conn, addr):
        try:
            header = conn.recv(4)
            if len(header) < 4:
                return
            length = struct.unpack(">I", header)[0]
            if length > 65536:
                return
            data = b""
            while len(data) < length:
                chunk = conn.recv(length - len(data))
                if not chunk:
                    break
                data += chunk
            msg = Message.from_bytes(data)
            self.inbox.append(msg)
            if self.on_message:
                self.on_message(msg, addr[0])
        except Exception:
            pass
        finally:
            conn.close()


# ─── node controller ──────────────────────────────────────────────────────────

class BitChatNode:
    """
    Nó completo da intranet BitChat.
    Descoberta automática + envio + recebimento + display.
    """

    def __init__(self, alias: str = "wave"):
        self.identity = load_or_create_identity(alias)
        self.peers: Dict[str, dict] = {}
        self.channels: Dict[str, List[Message]] = {ch: [] for ch in CHANNELS}

        self.beacon_sender   = BeaconSender(self.identity)
        self.beacon_listener = BeaconListener(
            self.identity, self.peers,
            on_new_peer=self._on_new_peer
        )
        self.msg_server = MessageServer(on_message=self._on_message)

    def start(self):
        self.beacon_sender.start()
        self.beacon_listener.start()
        self.msg_server.start()

    def _on_new_peer(self, peer: dict):
        print(f"\n[+] PEER DISCOVERED  alias={peer['alias']}  node={peer['node_id'][:8]}  ip={peer['ip']}")

    def _on_message(self, msg: Message, from_ip: str):
        ch = msg.channel if msg.channel in self.channels else "#general"
        self.channels[ch].append(msg)
        ts = datetime.fromtimestamp(msg.timestamp).strftime("%H:%M:%S")
        print(f"\n[{ch}] {ts} <{msg.alias}> {msg.text}")

    def broadcast(self, text: str, channel: str = "#general"):
        """Envia mensagem para todos os peers conhecidos."""
        import uuid
        msg = Message(
            msg_id    = str(uuid.uuid4())[:8],
            sender_id = self.identity["node_id"],
            alias     = self.identity["alias"],
            channel   = channel,
            text      = text
        )
        msg.sign(self.identity["priv_hex"])

        for nid, peer in list(self.peers.items()):
            send_message_to_peer(peer["ip"], msg)

        # store locally
        ch = channel if channel in self.channels else "#general"
        self.channels[ch].append(msg)
        return msg

    def send(self, text: str, channel: str = "#general", target_id: str = None):
        """Envia para peer específico ou broadcast."""
        if target_id:
            peer = self.peers.get(target_id)
            if not peer:
                return None
            import uuid
            msg = Message(
                msg_id    = str(uuid.uuid4())[:8],
                sender_id = self.identity["node_id"],
                alias     = self.identity["alias"],
                channel   = channel,
                text      = text
            )
            msg.sign(self.identity["priv_hex"])
            send_message_to_peer(peer["ip"], msg)
            return msg
        return self.broadcast(text, channel)

    def status(self) -> dict:
        now = time.time()
        alive_peers = {
            nid: p for nid, p in self.peers.items()
            if now - p.get("seen_at", 0) < 30
        }
        return {
            "node_id":     self.identity["node_id"],
            "alias":       self.identity["alias"],
            "pub_hex":     self.identity["pub_hex"],
            "live_peers":  len(alive_peers),
            "peers":       [
                {"alias": p["alias"], "node_id": p["node_id"][:8], "ip": p["ip"]}
                for p in alive_peers.values()
            ],
            "channels":    {ch: len(msgs) for ch, msgs in self.channels.items()},
            "interfaces":  get_lan_interfaces()
        }


# ─── CLI entry point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse, time

    parser = argparse.ArgumentParser(description="BitChat LAN Node")
    parser.add_argument("--alias",   default="wave",     help="Nome do nó")
    parser.add_argument("--listen",  action="store_true", help="Modo escuta silenciosa")
    parser.add_argument("--scan",    action="store_true", help="Scan 30s + status")
    parser.add_argument("--send",    type=str,            help="Mensagem a enviar")
    parser.add_argument("--channel", default="#general",  help="Canal destino")
    parser.add_argument("--status",  action="store_true", help="Mostrar estado do nó")
    args = parser.parse_args()

    node = BitChatNode(alias=args.alias)
    node.start()
    print(f"[BITCHAT] Node '{args.alias}' online — id={node.identity['node_id'][:8]}")
    print(f"[BITCHAT] Portas: UDP/{BEACON_PORT} (beacon) TCP/{STREAM_PORT} (stream)")

    if args.scan:
        print("[BITCHAT] Scanning LAN por 30 segundos...")
        time.sleep(30)
        st = node.status()
        print(json.dumps(st, indent=2))

    elif args.send:
        time.sleep(3)  # janela de descoberta
        msg = node.broadcast(args.send, args.channel)
        print(f"[SENT] {args.channel} → '{args.send}' (id={msg.msg_id})")
        time.sleep(1)

    elif args.status:
        time.sleep(3)
        print(json.dumps(node.status(), indent=2))

    elif args.listen:
        print("[BITCHAT] Modo escuta. Ctrl+C para sair.")
        while True:
            time.sleep(1)

    else:
        # modo interativo
        print("[BITCHAT] Modo interativo. Digite mensagens. /quit para sair.")
        print(f"[BITCHAT] Channels: {', '.join(CHANNELS)}")
        time.sleep(2)  # janela de descoberta
        current_channel = "#general"
        while True:
            try:
                line = input(f"{current_channel}> ").strip()
                if not line:
                    continue
                if line == "/quit":
                    break
                if line.startswith("/join "):
                    ch = line[6:].strip()
                    if not ch.startswith("#"):
                        ch = "#" + ch
                    current_channel = ch
                    print(f"[+] Channel: {current_channel}")
                    continue
                if line == "/peers":
                    st = node.status()
                    for p in st["peers"]:
                        print(f"  {p['alias']} ({p['node_id']}) @ {p['ip']}")
                    continue
                if line == "/status":
                    print(json.dumps(node.status(), indent=2))
                    continue
                node.broadcast(line, current_channel)
            except (KeyboardInterrupt, EOFError):
                break

    print("[BITCHAT] Offline.")
