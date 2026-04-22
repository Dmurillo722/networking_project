# CNT4007 Networking Project

## Group Members
- David Murillo
- Jolina Jasperson
- Mariana Cabezas

## Contributions
- **David Murillo**: project skeleton, starter files, repository setup

- **Jolina Jasperson**: message serialization/parsing, configuration loading, peer startup flow, connection management, peer message handling, logging cleanup, demo verification, and final submission cleanup.

- **Mariana Cabezas**: logging setup and fixes, connection management, demo setup and recording, final submission cleanup

## How to Run Demo
1. Make sure `Common.cfg`, `PeerInfo.cfg`, and the seed peer folders are in the project root. Per the project spec, peer-specific files should live in folders named `peer_<peer_id>`, such as `peer_1001/thefile`.
2. Start one terminal per peer from the project root.
3. Start peers in the same order they appear in `PeerInfo.cfg`:

```bash
python peerProcess.py <peer_id>
```

Example:

```bash
python peerProcess.py 1001
python peerProcess.py 1002
python peerProcess.py 1003
```

Each peer writes its events to `log_peer_<peer_id>.log` and stores pieces/reconstructed files in that peer's folder.

## Notes
For a single-machine local demo, create `PeerInfo.cfg` with `127.0.0.1` or `localhost` and different ports for each peer. For a multi-machine video demo, use laptop/VPN hostnames or CISE servers such as `rain.cise.ufl.edu`, `storm.cise.ufl.edu`, and `thunder.cise.ufl.edu`; do not use the obsolete `lin114-*` hosts.

## Final Submission Checklist
- Submit one archive for the group on Canvas before April 22, 11:59 pm.
- Include source files, launcher scripts, this README, and any files needed to run the program.
- Do not include `Common.cfg`, `PeerInfo.cfg`, sample data files, generated peer folders, logs, `__pycache__`, `.pyc` files, or compiled/object files.
- For the recorded demo, use multiple machines and a data file of at least 20 MB with `PieceSize 16384`.
