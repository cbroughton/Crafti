# -*- coding: cp1252 -*-
from twisted.internet.protocol import Protocol, ClientFactory
from twisted.internet import reactor, task

import os
import struct
import sys
sys.path.append(os.path.abspath(os.path.dirname(sys.executable)))

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

class MinecraftBot:
    def __init__(self):
        pass
    #End of __init__
    
    def onPing(self, payload):
        print ("DEBUG: Received Keepalive packet.")
        print ("DEBUG: Sending Keepalive packet.")
        self.protocol.send(p00Keepalive())
    #End of onPing
    
    def onLoginResponse(self, payload):
        print ("DEBUG: Received Login Response packet.")
    #End of onLoginResponse
    
    def onHandshake(self, payload):
        print ("DEBUG: Received Handshake packet.  payload = %s"%payload)
        print ("DEBUG: Sending Login Response packet.")
        self.protocol.send(p01LoginResponse(username))
    #End of onHandshake
#End of MinecraftBot

def p00Keepalive():
    pkt = struct.pack('B', 0x00)
    return pkt
#End of 00Keepalive
    
def p01LoginResponse(username, password = "Password"):
    pkt = struct.pack('B', 0x01)   # Packet ID
    pkt+= packString(username)     # Useranme
    pkt+= packString(password)     # Password
    pkt+= packLong()               # Map Seed
    pkt+= struct.pack('B', 0x00)   # Position
    return pkt
#End of 01Login
    
def p02Handshake(username):
    pkt = struct.pack('B', 0x02)   # Packet ID
    pkt+= packString(username)     # Username
    return pkt
#End of 02Handshake
    
def packLong():
    pkt = struct.pack('B', 0x00)
    pkt+= struct.pack('B', 0x00)
    pkt+= struct.pack('B', 0x00)
    pkt+= struct.pack('B', 0x00)
    pkt+= struct.pack('B', 0x00)
    pkt+= struct.pack('B', 0x00)
    pkt+= struct.pack('B', 0x00)
    pkt+= struct.pack('B', 0x00)
    return pkt
#End of packLong
    
def packString(string):
    pkt = struct.pack('>H', len(string))
    pkt+= struct.pack('>%ds'%len(string), string)
    return pkt
#End of packString

class MinecraftProtocol(Protocol):
    def __init__(self, bot):
        self.bot = bot
        self.buffer = ''
        self.packet_length = {"\x00": 1,
                              "\x01": 18, # VARIABLE
                              "\x02": 3,  # VARIABLE
                              "\x03": 3,  # VARIABLE
                              "\x04": 9,
                              "\x05": 9,
                              "\x06": 13,
                              "\x08": 3,
                              "\x09": 1,
                              "\x0D": 42,
                              "\x10": 3,
                              "\x12": 6,
                              "\x14": 23, # VARIABLE
                              "\x15": 23,
                              "\x16": 9,
                              "\x17": 18,
                              "\x18": 20,
                              "\x1C": 11,
                              "\x1D": 5,
                              "\x1E": 5,
                              "\x1F": 8,
                              "\x20": 7,
                              "\x21": 10,
                              "\x22": 19,
                              "\x26": 6,
                              "\x27": 9,
                              "\x32": 10,
                              "\x33": 18, # VARIABLE
                              "\x34": 11, # VARIABLE
                              "\x35": 12,
                              "\x3C": 33, # VARIABLE
                              "\x67": 6,  # VARIABLE
                              "\x68": 4,  # VARIABLE
                              "\x69": 6,
                              "\x6A": 5,
                              "\x82": 11, # VARIABLE
                              "\xFF": 3   # VARIABLE
                              }
        self.StoC = {"\x00": 'keep alive',
                     "\x01": 'login response',
                     "\x02": 'handshake',
                     "\x03": 'chat message',
                     "\x04": 'time update',             #IGNORE THIS
                     "\x05": 'entity equipment',        #IGNORE THIS
                     "\x06": 'spawn position',
                     #07 (Client to Server ONLY)
                     "\x08": 'update health',
                     "\x09": 'respawn',
                     #0A - 0C (Client to Server ONLY)
                     "\x0D": 'player look and position',
                     #0E - 0F (Client to Server ONLY)
                     "\x10": 'holding change',          #IGNORE THIS
                     "\x12": 'animation',               #IGNORE THIS
                     "\x14": 'named entity spawn',
                     "\x15": 'pickup spawn',
                     "\x16": 'collect item',
                     "\x17": 'add object / vehicle',
                     "\x18": 'mob spawn',               #IGNORE THIS
                     "\x1C": 'entity velocity (?)',     #IGNORE THIS
                     "\x1D": 'destroy entity',          #IGNORE THIS
                     "\x1E": 'entity',                  #IGNORE THIS
                     "\x1E": 'entity relative move',    #IGNORE THIS
                     "\x20": 'entity look',             #IGNORE THIS
                     "\x21": 'entity look and rel.move',#IGNORE THIS
                     "\x26": 'entity status',           #IGNORE THIS
                     "\x27": 'attach entity',           #IGNORE THIS
                     "\x32": 'pre-chunk',
                     "\x33": 'map chunk',
                     "\x34": 'multi block change',
                     "\x35": 'block change',            #IGNORE THIS (?)
                     "\x3C": 'explosion (?)',           #IGNORE THIS (?)
                     #64 - 66 (Client to Server ONLY)
                     "\x67": 'set slot',                #IGNORE THIS (?)
                     "\x68": 'window item',             #IGNORE THIS (?)
                     "\x69": 'update progress bar',     #IGNORE THIS
                     "\x6A": 'transaction',             #IGNORE THIS (?)
                     "\x82": 'sign update',             #IGNORE THIS
                     "\xFF": 'kick'
                     }

        handlers[0] = self.bot.onPing
    #    handlers[1] = self.bot.onLoginResponse
    #    handlers[2] = self.bot.onHandshake
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
        print ("DEBUG: Sending Packet: ", pkt)
        self.transport.write(pkt)
    #End of send
    
    def connectionMade(self):
            print("DEBUG: Sending a Handshake!")
            self.send(p02Handshake(username))
    #End of connectionMade
#End of MinecraftProtocol

class Connection(ClientFactory):
    def __init__(self):
        self.bot = MinecraftBot()
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
