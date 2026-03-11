import sys
from src.config import load_common_config, load_peer_info, get_peer_by_id


def main():
    # Make sure peer id was given
    if len(sys.argv) != 2:
        print("Usage: python3 peerProcess.py <peer_id>")
        return

    # Get peer id from command line
    peer_id = int(sys.argv[1])

    # Read both config files
    common_config = load_common_config()
    peers = load_peer_info()

    # Find this peer
    current_peer = get_peer_by_id(peer_id, peers)

    if current_peer is None:
        print("Peer ID not found")
        return

    # Just print some info for now
    print(f"Starting peer {peer_id}")
    print(f"Host: {current_peer.host_name}")
    print(f"Port: {current_peer.port}")
    print(f"Has file: {current_peer.has_file}")
    print(f"Total pieces: {common_config.number_of_pieces}")

    # Real peer logic will go here later


if __name__ == "__main__":
    main()