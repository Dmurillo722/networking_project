import sys

from src.config import get_peer_by_id, load_common_config, load_peer_info
from src.connection_manager import ConnectionManager
from src.logger import PeerLogger
from src.piece_manager import PieceManager


def main():
    if len(sys.argv) != 2:
        print("Usage: peerProcess <peer_id>")
        return

    peer_id = int(sys.argv[1])
    common_config = load_common_config()
    peers = load_peer_info()
    current_peer = get_peer_by_id(peer_id, peers)

    if current_peer is None:
        print("Peer ID not found")
        return

    logger = PeerLogger(peer_id)
    piece_manager = PieceManager(
        peer_id=peer_id,
        num_pieces=common_config.number_of_pieces,
        piece_size=common_config.piece_size,
        file_size=common_config.file_size,
        has_file=current_peer.has_file,
    )

    if current_peer.has_file:
        piece_manager.initialize_from_complete_file(common_config.file_name)

    connection_manager = ConnectionManager(
        current_peer=current_peer,
        peers=peers,
        piece_manager=piece_manager,
        logger=logger,
        common_config=common_config,
    )

    print(f"Starting peer {peer_id} on {current_peer.host_name}:{current_peer.port}")
    print(f"Total pieces: {common_config.number_of_pieces}")

    try:
        connection_manager.start()
        connection_manager.wait_for_completion()
    except KeyboardInterrupt:
        print("Stopping peer process")
        connection_manager.stop()


if __name__ == "__main__":
    main()
