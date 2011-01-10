# -*- coding: cp1252 -*-
from twisted.internet.protocol import Protocol
from twisted.internet.protocol import ClientFactory
from twisted.internet import reactor
from twisted.internet import task

import os
import struct
import sys
sys.path.append(os.path.abspath(os.path.dirname(sys.executable)))
import weakref

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
        self.heightmap = zeros((16, 16), dtype=uint8)
        self.metadata = zeros((16, 16, 128), dtype=uint8)

        self.tiles = {}

    def __repr__(self):
        return "Chunk(%d, %d)" % (self.x, self.z)

    __str__ = __repr__

    def regenerate_heightmap(self):
        for x, z in product(xrange(16), repeat=2):
            for y in range(127, -1, -1):
                if self.blocks[x, z, y]:
                    break

            self.heightmap[x, z] = y

    def regenerate_metadata(self):
        pass

    def regenerate(self):
        self.regenerate_heightmap()
        self.regenerate_metadata()

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

    def set_block(self, coords, block):
        x, y, z = coords

        if self.blocks[x, z, y] != block:
            self.blocks[x, z, y] = block

            for y in range(127, -1, -1):
                if self.blocks[x, z, y]:
                    break
            self.heightmap[x, z] = y

    def get_metadata(self, coords):
        x, y, z = coords

        return self.metadata[x, z, y]

    def set_metadata(self, coords, metadata):
        x, y, z = coords

        if self.metadata[x, z, y] != metadata:
            self.metadata[x, z, y] = metadata

    def height_at(self, x, z):
        return self.heightmap[x, z]

    def sed(self, search, replace):
        if (self.blocks == search).any():
            self.blocks = where(self.blocks == search, replace, self.blocks)

    def get_column(self, x, z):
        return self.blocks[x, z]

    def set_column(self, x, z, column):
        self.blocks[x, z] = column

def BravoWorld():
    def __init__(self):
        self.chunk_cache = weakref.WeakValueDictionary()
    #End of __init__
    
    def load_chunk(self, x, z):
        if (x, z) in self.chunk_cache:
            return self.chunk_cache[x, z]

        chunk = Chunk(x, z)
        return chunk
    #End of load_chunk
    
class MinecraftBot:
    def __init__(self, world):
        self.world = world
    #End of __init__
    
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
    
    def onIGNORED(self, payload):
        pass
    #End of onIGNORED

    def onPreChunk(self, payload):
        print ("INFO:  INIT ON CHUNK AT %d x %d"%(payload['x'], payload['y']))
        self.world.load_chunk(payload['x'], payload['y'])
    #End of onPreChunk
    
    def onNOTIMPLEMENTED(self, payload):
        print ("WARN:  Not yet implemted!  %s"%payload)
    #End of onNOTIMPLEMENTED

    def onKicked(self, payload):
        print ("ERROR: You were kicked from the server.  Reason: %s"%payload['message'])
    #End of onKicked

    def sendMessage(self, message):
        self.protocol.send(make_packet("chat", {"message": message}))
    #End of sendMessage
#End of MinecraftBot

class MinecraftProtocol(Protocol):
    def __init__(self, bot):
        self.bot = bot
        self.buffer = ''

        self.handlers = {0: self.bot.onPing,
                         2: self.bot.onHandshake,
                         3: self.bot.onChat,
                         4: self.bot.onIGNORED,  # Time Updates
                         5: self.bot.onIGNORED,  # Equipment update
                         18: self.bot.onIGNORED, # Arm Animations...
                         24: self.bot.onIGNORED, # Entities
                         28: self.bot.onIGNORED, # Entities
                         29: self.bot.onIGNORED, # Entities
                         30: self.bot.onIGNORED, # Entities
                         31: self.bot.onIGNORED, # Entities
                         32: self.bot.onIGNORED, # Entities
                         33: self.bot.onIGNORED, # Entities
                         38: self.bot.onIGNORED, # Unused
                         50: self.bot.onPreChunk,
                         52: self.bot.onNOTIMPLEMENTED, # Block Updates
                         53: self.bot.onNOTIMPLEMENTED, # Block Updates
                         255: self.bot.onKicked
                         }
    #End of __init__
    
    def dataReceived(self, data):
        self.buffer += data

        packets, self.buffer = parse_packets(self.buffer)

        for header, payload in packets:
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
    #End of send
    
    def connectionMade(self):
        self.send(make_packet("handshake", {"username": username}))
    #End of connectionMade
#End of MinecraftProtocol

class Connection(ClientFactory):
    def __init__(self):
        world = BravoWorld()
        self.bot = MinecraftBot(world)
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
