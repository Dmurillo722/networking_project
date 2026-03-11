#This file handles message encoding and decoding

#Handshake: 18-byte header (string) + 10-byte zero bits + 4 byte peer ID (int)

#Actual messages : 4 byte msg length field + 1 byte message type field + Message payload of variable size
#type chart:
#message type  |value
#choke         | 0
#unchoke       | 1
#interested    | 2
#not interested| 3
#have          | 4
#bitfield      | 5
#request       | 6
#piece         | 7

#'choke’, ‘unchoke’, ‘interested’ and ‘not interested’ messages have no payload.

#‘have’ messages have a payload that contains a 4-byte piece index field.

#‘bitfield’ messages is only sent as the first message right after handshaking is done when
#a connection is established. ‘bitfield’ messages have a bitfield as its payload. 
# (see page 2 on project description for more info)


#read message on corresponding socket