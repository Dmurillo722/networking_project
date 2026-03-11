#Handles one neighbor per connection thread in its lifetime

#Handshake Phase:
#Sends and receives handshake, then validates header and peer ID
#Sends bitfield and receives bitfield if neighbor has pieces
#Declares interest based on bitfield diff
#choke-> stop sending requests
#unchoke->pick a random needed piece and send request
#interested-> mark neighbor as interested
#not interested-> mark neighbor as not interested
#if has piece -> update neighbor's bitfield and re-evaluate interest
#bitfield->store neighbor's bitfield and evaluate interest
#request-> if neighbor is unchoked by us, respond with piece
#piece -> write to piece manager, update rate, and send next request
#broadcast "have" to all other neighbors
#re-evaluate interest for all other neighbors