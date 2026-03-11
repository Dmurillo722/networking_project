#Manages TCP connections for the peer

#Open server socket and listen for incoming connections

#on startup, connect outbound to all lower-ID peers in order

#spawns one peer_handler thread per connection in both directions

#tracks all active peer handler instances

#polls all peers completion status to know when to shut down

