# -*- coding: cp1252 -*-
from twisted.internet.protocol import Protocol
from twisted.internet.protocol import ClientFactory
from twisted.internet import reactor
from twisted.internet import task

from numpy import zeros
from numpy import uint8

import os
import struct
import sys
sys.path.append(os.path.abspath(os.path.dirname(sys.executable)))

# Bravo Libraries (~dab755a0b118b5125e4b)
from packets import make_packet
from packets import parse_packets

import mechanize

try:
    conf = open("crafti.config").read().splitlines()
    username = conf[0].strip()  # Username that owns Minecraft Alpha
    password = conf[1].strip()  # Password for the above account
    version = conf[2].strip()   # Version reported to minecraft.net

    automatic = conf[3].strip() # Connect, execute rules, leave.
    silent = conf[4].strip()    # Never speak, unless "SAY" used.

    server = conf[5].strip()    # Server (IP:PORT) last connected...
    print ("INFO:  crafti.config loaded!")
except:
    print ("WARN:  crafti.config not loaded!")
    print ("INFO:  Prompting for settings...")
    username = raw_input("\tMinecraft Username: ").strip()
    password = raw_input("\tMinecraft Password: ").strip()
    version = "12"
    automatic = "no"
    silent = "no"
    server = ""
finally:
    print ("\nConfiguration for Run:")
    print ("\tUsername:  %s"%username)
    print ("\tPassword:  %s"%password)
    print ("\tVersion:   %s"%version)
    print ("\tAutomated: %s"%automatic)
    print ("\tSilent:    %s"%silent)
#End of try, catch, finally

print ("\n\nINFO:  Attempting to login to minecraft.net ...")
login = mechanize.Browser()
loginResult = login.open("http://www.minecraft.net/game/getversion.jsp?user=%s&password=%s&version=%s"%(username,password,version)).read()

# Get the values from the response, hopefully.
print ("DEBUG: Parsing loginResult...")
try:
    loggedIn = False
    if "Bad" in loginResult:
        print ("CRIT:  minecraft.net says: %s.  Please try again."%loginResult)
    elif "Error" in loginResult:
        print ("CRIT:  minecraft.net says: %s.  This normally indicates a fatal error, OH NO!"%loginResult)
    elif "Old" in loginResult:
        print ("CRIT:  minecraft.net says: &s.  This means CharlesBroughton has not yet updated Crafti since Minecraft was last updated.  Please wait for an update to be released."%loginResult)
    else:
        print ("DEBUG: Extracting variables from loginResult...")
        loginResult = loginResult.split(":")
        cl_version  = loginResult[0]
        dl_ticket   = loginResult[1]
        username    = loginResult[2]
        session_id  = loginResult[3]
        loggedIn    = True
    #End of if, elif, else
except:
    print ("ERROR: Unable to parse login response, invalid login perhaps?")
#End of try, except

if loggedIn:
    print ("DEBUG: cl_version  = %s"%cl_version)
    print ("DEBUG: dl_ticket   = %s"%dl_ticket)
    print ("INFO:  Logged in as: %s"%username)
    print ("DEBUG: session_id  = %s"%session_id)

    print ("\n-------------------------------------\n")
    raw = raw_input("Connect to [%s]: "%server)
    if not raw.strip() == "":
        server = raw.strip()
    #End of if
    
    #SAVE CONFIG
    try:
        f = open("crafti.config", "w")
        f.write("%s\n%s\n%s\n%s\n%s\n%s"%(username, password, version, automatic, silent, server))
        f.close()
    except:
        print ("ERROR: Unable to save to crafti.config.  Please make sure the file exists, and is writable.")
    #End of try, except
    
    try:
        connect = server.split(":")
        server  = connect[0]
        port    = connect[1]
    except:
        port = 25565
    #End of try, except
#End of if

class Chunk():
    def __init__(self, x, z):
        self.x = int(x)
        self.z = int(z)

        self.blocks = zeros((16, 16, 128), dtype=uint8)
    #End of __init__

    def __repr__(self):
        return "Chunk(%d, %d)" % (self.x, self.z)
    #End of __repr__

    __str__ = __repr__

    def load_from_packet(self, packet):
        print ("PACKET: ", packet)
        
#        array = [chr(i) for i in self.blocks.ravel()]
#        array += pack_nibbles(self.metadata)
#        array += pack_nibbles(self.skylight)
#        array += pack_nibbles(self.blocklight)
#        packet = make_packet("chunk", x=self.x * 16, y=0, z=self.z * 16,
#            x_size=15, y_size=127, z_size=15, data="".join(array))
#        return packet

    def get_block(self, coords):
        x, y, z = coords

        return self.blocks[x, z, y]
    #End of get_block

    def set_block(self, coords, block):
        x, y, z = coords

        if self.blocks[x, z, y] != block:
            self.blocks[x, z, y] = block

            for y in range(127, -1, -1):
                if self.blocks[x, z, y]:
                    break
                #End of if
            #End of for y
        #End of if
    #End of set_block
    
class MinecraftBot:
    def __init__(self, stats):
        self.chunk_cache = {}
        self.stats = stats
        self.delay = 0
    #End of __init__

    def init_chunk(self, x, z):
        self.chunk_cache[x, z] = Chunk(x, z)
    #End of init_chunk
    
    def onPing(self, payload):
        self.protocol.send(make_packet("ping"))
    #End of onPing
    
    def onHandshake(self, payload):
        print ("DEBUG: Received Handshake packet.")
        print ("INFO:  Asking minecraft.net to join...")
        login = mechanize.Browser()
        url = "http://www.minecraft.net/game/joinserver.jsp?user="
        url+= username + "&sessionId=" + session_id
        url+= "&serverId=" + payload['username']
        login.open(url)
        
        print ("DEBUG: Sending Login Response packet.")
        self.protocol.send(make_packet("login", {"protocol": 8,
                                                 "username": username,
                                                 "unused": "Password",
                                                 "seed": 0,
                                                 "dimension": 0}))
    #End of onHandshake

    def onChat(self, payload):
        print("INFO:  Received chat message: %s"%payload)
    #End of onChat

    def onSpawn(self, payload):
        print("INFO:  Got spawn packet, sending location...")
   #     print(payload)
   #     self.protocol.send(make_packet("location", {"position": {"x": -532,
   #                                                              "y": 70,
   #                                                              "stance": 69,
   #                                                              "z": -2850
   #                                                             },
   #                                                 "look": {"rotation": 0,
   #                                                          "pitch": 0},
   #                                                 "flying": {"flying": 0}}))
    #End of onSpawn
    
    def onIGNORED(self, payload):
        pass
    #End of onIGNORED

    def onLocation(self, payload):
        self.location = payload
    #End of onLocation

    def nextLoc(self):
        if self.delay > 10:
            self.delay = 0
            if hasattr(self, 'location'):
                print (self.location)
                self.location['position']['x'] += 100
                print (self.location)
                self.protocol.send(make_packet("location", self.location))
        else:
            self.delay += 1
    #End of nextLoc

    def onPreChunk(self, payload):
        self.init_chunk(payload['x'], payload['z'])
    #End of onPreChunk
    
    def onBlockUpdate(self, payload):
        if ("blocks_received") not in self.stats:
            self.stats['blocks_received'] = 0
        self.stats['blocks_received'] += 1
        x = payload['x']
        y = payload['y']
        z = payload['z']
        block = payload['type']
        xChunk, localX = divmod(x, 16)
        zChunk, localZ = divmod(z, 16)
        if (xChunk, zChunk) not in self.chunk_cache:
            self.init_chunk(xChunk, zChunk)
        self.chunk_cache[xChunk, zChunk].set_block({0: localX,1: y,2: localZ}, block)
    #End of onBlockUpdate
        
    def onLargeUpdate(self, payload):
        size = (payload['x_size'] + 1) * (payload['y_size'] + 1) * (payload['z_size'] + 1)
        blocks = payload.data[:size]
        
        x, y, z, pointer = payload['x'], payload['y'], payload['z'], 0
        while x < payload['x'] + payload['x_size'] + 1:
            x += 1
            xChunk, localX = divmod(x, 16)
            while z < payload['z'] + payload['z_size'] + 1:
                z += 1
                zChunk, localZ = divmod(z, 16)
                if (xChunk, zChunk) not in self.chunk_cache:
                    self.init_chunk(xChunk, zChunk)
                while y < payload['y'] + payload['y_size'] + 1:
                    y += 1
                    if ("blocks_received") not in self.stats:
                        self.stats['blocks_received'] = 0
                    self.stats['blocks_received'] += 1
                    block = blocks[pointer][0]
                    block = struct.unpack('B', block)
                    block = int(block[0])
                    if block == 14:
                        print ("== GOLDORE FOUND == X: %d, Y: %d, Z: %d"%(x, y, z))
                    if block == 15:
                        print ("== IRONORE FOUND == X: %d, Y: %d, Z: %d"%(x, y, z))
                    if block == 16:
                        print ("== COALORE FOUND == X: %d, Y: %d, Z: %d"%(x, y, z))
                    if block == 46:
                        print ("== --TNT-- FOUND == X: %d, Y: %d, Z: %d"%(x, y, z))
                    if block == 54:
                        print ("== -CHEST- FOUND == X: %d, Y: %d, Z: %d"%(x, y, z))
                    if block == 56:
                        print ("== DIAMOND FOUND == X: %d, Y: %d, Z: %d"%(x, y, z))
                    self.chunk_cache[xChunk, zChunk].set_block({0: localX, 1: y, 2: localZ}, block)
                    pointer += 1
                #End while z
            #End while y
        #End while x
        self.nextLoc()
    #End of onLargeUpdate
    
    def onNOTIMPLEMENTED(self, payload):
        print ("WARN:  Packet not yet implemted!  (map data)")
    #End of onNOTIMPLEMENTED

    def onKicked(self, payload):
        print ("ERROR: You were kicked from the server.  Reason: %s"%payload['message'])
    #End of onKicked

    def sendMessage(self, message):
        self.protocol.send(make_packet("chat", {"message": "/tell uyuyuy99" + message}))
    #End of sendMessage
#End of MinecraftBot

class MinecraftProtocol(Protocol):
    def __init__(self, bot):
        self.bot = bot
        self.stats = bot.stats
        self.buffer = ''

        self.handlers = {0: self.bot.onPing,
                         2: self.bot.onHandshake,
                         3: self.bot.onChat,
                         4: self.bot.onIGNORED,  # Time Updates
                         5: self.bot.onIGNORED,  # Equipment update
                         6: self.bot.onSpawn,
                         13: self.bot.onLocation,
                         18: self.bot.onIGNORED, # Arm Animations...
                         20: self.bot.onIGNORED, # Player Locations, come back later!
                         21: self.bot.onIGNORED, # Entities (?)
                         22: self.bot.onIGNORED, # Entities (?)
                         23: self.bot.onIGNORED, # Vehicles
                         24: self.bot.onIGNORED, # Entities
                         28: self.bot.onIGNORED, # Entities
                         29: self.bot.onIGNORED, # Entities
                         30: self.bot.onIGNORED, # Entities
                         31: self.bot.onIGNORED, # Entities
                         32: self.bot.onIGNORED, # Entities
                         33: self.bot.onIGNORED, # Entities
                         34: self.bot.onIGNORED, # Entities
                         38: self.bot.onIGNORED, # Unused
                         50: self.bot.onPreChunk,
                         51: self.bot.onLargeUpdate,
                         52: self.bot.onIGNORED, # Block Updates, come back later!
                         53: self.bot.onBlockUpdate,
                         103: self.bot.onIGNORED, # Inventory, come back later!
                         104: self.bot.onIGNORED, # Inventory, come back later!
                         255: self.bot.onKicked
                         }
    #End of __init__
    
    def dataReceived(self, data):
        self.buffer += data
        if ("data_received") not in self.stats:
            self.stats['data_received'] = 0
        self.stats['data_received'] += len(data)
        
        packets, self.buffer = parse_packets(self.buffer)

        for header, payload in packets:
            if ("packets_received") not in self.stats:
                self.stats['packets_received'] = 0
            self.stats['packets_received'] += 1
            if header in self.handlers:
                self.handlers[header](payload)
            else:
                print "Didn't handle parseable packet %d!"%header
                print payload
            #End of if, elif, else
        #End of for
    #End of dataReceived
    
    def send(self, pkt):
        self.transport.write(pkt)
        if ("packets_sent") not in self.stats:
            self.stats['packets_sent'] = 0
        self.stats['packets_sent'] += 1
        if ("data_sent") not in self.stats:
            self.stats['data_sent'] = 0
        self.stats['data_sent'] += len(pkt)
    #End of send
    
    def connectionMade(self):
        self.send(make_packet("handshake", {"username": username}))
    #End of connectionMade
#End of MinecraftProtocol

class Connection(ClientFactory):
    def __init__(self):
        self.stats = {}
        self.bot = MinecraftBot(self.stats)
    #End of __init__

    def startedConnecting(self, connector):
        print ("DEBUG: startedConnecting...")
    #End of startedConnecting

    def buildProtocol(self, addr):
        print ("INFO:  Connected to %s"%addr)
        print ("DEBUG: Initialising Protocol")
        protocol = MinecraftProtocol(self.bot)
        self.bot.protocol = protocol
        return protocol
    #End of buildProtocol

    def clientConnectionLost(self, connector, reason):
        print ("CRIT:  Lost connection.  Reason: %s"%reason)
    #End of clientConnectionLost

    def clientConnectionFailed(self, connector, reason):
        print ("CRIT:  Connection Failed.  Reason: %s"%reason)
    #End of clientConnectionFailed
#End of Connection

if loggedIn:
    print ("DEBUG: Initialising ClientFactory...")
    reactor.connectTCP(server, port, Connection())
    reactor.run()
else:
    print ("CRIT:  You never successfully logged in, exiting.")
#End of if, else
