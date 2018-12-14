#!/usr/bin/env python

# Copyright (C) 2017, 2018
#               Free Software Foundation, Inc.
# This file is part of Chisel.
#
# Chisel is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# Chisel is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Chisel; see the file COPYING.  If not, write to the
# Free Software Foundation, 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.
#
# Author Gaius Mulley <gaius@gnu.org>
#

import getopt, sys, string

inputFile = None
defines = {}
verbose = False
debugging = False
autoLights = False
floor = []
rooms = {}
maxx, maxy = 0, 0
doorValue, wallValue, emptyValue = 0, -1, -2
versionNumber = 0.2
lightFrequency = 5
defaultColour = None


def mycut (l, i):
    if i == 0:
        if len (l) > 1:
            return None, l[i], l[i+1:]
        return None, l[i], None
    if len (l) > i+1:
        return l[:i], l[i], l[i+1:]
    return l[:i], l[i], None


def mystitch (a, b, c):
    if a == None:
        d = b
    else:
        d = a + b
    if c == None:
        return d
    return d + c


def setFloor (x, y, value):
    global floor
    a, b, c = mycut (floor, y)
    x, y, z = mycut (b, x)
    b = mystitch (x, [value], z)
    floor = mystitch (a, [b], c)


def getFloor (x, y):
    global floor
    return floor[y][x]


def initFloor (x, y, value):
    global floor
    floor = []
    for j in range (y+1):
        row = [value] * (x+1)
        floor += [row]


class roomInfo:
    def __init__ (self, w, d):
        self.walls = w
        self.doors = d
        self.doorLeadsTo = []
        self.monsters = []
        self.weapons = []
        self.ammo = []
        self.lights = []
        self.autoLights = []
        self.worldspawn = []
        self.inside = None
        self.defaultColour = {}
        self.sounds = []


#
#  printf - keeps C programmers happy :-)
#

def printf (format, *args):
    print str(format) % args,


#
#  vprintf - printf if verbose was set.
#

def vprintf (format, *args):
    global verbose
    if verbose:
        print str(format) % args,
        sys.stdout.flush ()


#
#  error - issues an error message and exits.
#

def error (format, *args):
    print str (format) % args,
    sys.exit (1)


#
#  debugf - issues prints if debugging is set
#

def debugf (format, *args):
    global debugging
    if debugging:
        print str (format) % args,


def usage (code):
    print "Usage: txt2pen [-dhlvV] [-f frequency] [-o outputfile] inputfile"
    print "  -d debugging"
    print "  -h help"
    print "  -l automatic lighting"
    print "  -f frequency    (every frequency squares place a light)"
    print "  -V verbose"
    print "  -v version"
    print "  -o outputfile name"
    sys.exit (code)


#
#  handleOptions -
#

def handleOptions ():
    global debugging, verbose, outputName, autoLights, lightFrequency

    outputName = None
    try:
        optlist, l = getopt.getopt(sys.argv[1:], ':df:hlo:vV')
        for opt in optlist:
            if opt[0] == '-d':
                debugging = True
            elif opt[0] == '-h':
                usage (0)
            elif opt[0] == '-l':
                autoLights = True
            elif opt[0] == '-f':
                lightFrequency = int (opt[1])
            elif opt[0] == '-o':
                outputName = opt[1]
            elif opt[0] == '-v':
                printf ("txt2pen version " + str (versionNumber) + "\n")
                sys.exit (0)
            elif opt[0] == '-V':
                verbose = True
        if l != []:
            return (l[0], outputName)

    except getopt.GetoptError:
        usage (1)
    return (None, outputName)


#
#  errorLine - display an error in GNU format.
#

def errorLine (n, line, text):
    global inputFile
    full = "%s:%d:%s\n%s:%d:%s\n" % (inputFile, n, text, inputFile, n, line)
    sys.stderr (full)


def addDef (c, line, l):
    global defines
    w = c.split ()
    a = w[0]
    if len (c) > len (w[0]):
        c = c[len (w[0]):]
        c = c.lstrip ()
        defines[a] = c
    else:
        errorLine (l, line, 'define must have a full definition')


#
#  isSubstr - safely test whether the start of string, s, is, c.
#             return True if this is the case.  s can be any length.
#

def isSubstr (s, c):
    return (s == c) or ((len (s) > len (c)) and (s[:len(c)] == c))


#
#  readDefines - read the defines and store the definitions into the dictionary.
#

def readDefines (i):
    l = 1
    for line in i:
        c = line.lstrip ()
        if isSubstr (c, 'define'):
            c = c[len ('define'):]
            c = c.lstrip ()
            addDef (c, line, l)
        l += 1
    return i


#
#  readMap - read in the map component of the txt file
#

def readMap (i):
    mapGrid = []
    inMap = False
    s = 0
    for line in i:
        s += 1
        c = line.rstrip ()
        if c.find ('#') != -1:
            inMap = True
        if inMap:
            mapGrid += [c]
    return mapGrid, s


#
#  macro - return string, t, after decoding the macro definitions.
#

def macro (t):
    if t != "":
        s = 0
        i = 0
        while i < len (t):
            c = t[i]
            if c == '[':
                s = i
                i += 1
            elif c == ']':
                if s < i:
                    k = macro (t[s+1:i])
                    if defines.has_key (k):
                        k = defines[k]
                        k = k.strip () + " "
                    t = t[:s] + k + t[i+1:]
                    i = 0
                else:
                    i += 1
            else:
                i += 1
    return t


#
#  getListOfRooms - returns the number of rooms declared.
#

def getListOfRooms (mapGrid, start, i):
    global defines
    listOfRooms = []
    pos = []
    for y, r in enumerate (mapGrid, start=1):
        for x, c in enumerate (r, start=1):
            if defines.has_key (c):
                k = macro (defines[c])
                if isSubstr (k, 'room'):
                    pos += [[x, y]]
                    k = k.split ()[1:]
                    k = string.join (k)
                    k = k.split ()[0]
                    listOfRooms += [k]
    return listOfRooms, pos


def isWall (pos, grid):
    return grid[pos[1]][pos[0]] == '#'


def isDoor (pos, grid):
    return (grid[pos[1]][pos[0]] == '-') or (grid[pos[1]][pos[0]] == '|') or (grid[pos[1]][pos[0]] == '.')


def isPlane (pos, grid):
    return isWall (pos, grid) or isDoor (pos, grid)


def addVec (pos, vec):
    return [pos[0]+vec[0], pos[1]+vec[1]]


#
#  moveBy - keep moving, pos, by either component of vec so long as it does not hit a plane.
#

def moveBy (pos, vec, grid):
    movingx, movingy = True, True
    while movingx or movingy:
        if vec[0] != 0:
            while not isPlane (addVec (pos, [vec[0], 0]), grid):
                pos = addVec (pos, [vec[0], 0])
                movingy = True
            movingx = False
        if vec[1] != 0:
            while not isPlane (addVec (pos, [0, vec[1]]), grid):
                pos = addVec (pos, [0, vec[1]])
                movingx = True
            movingy = False
    return pos


#
#  addWall - return the walls list and current point.
#            Providing that the start is different to the current
#            point then a new wall is added to the walls list.
#

def addWall (walls, start, current):
    if start != current:
        walls += [[start, current]]
    return walls, current


def lookingLeft (pos, left, grid, s):
    if debugging:
        print pos, left, s
    if s[1] == ' ' and isPlane (pos, grid):
        return False
    if s[1] == 'x' and (not isPlane (pos, grid)):
        return False
    if s[1] == '.' and (not isDoor (pos, grid)):
        if debugging:
            print "no door at", pos
        return False
    if s[0] == ' ' and isPlane (addVec (pos, left), grid):
        return False
    if s[0] == 'x' and (not isPlane (addVec (pos, left), grid)):
        return False
    if s[0] == '.' and (not isDoor (addVec (pos, left), grid)):
        return False
    return True

def mystop ():
    pass

def scanRoom (topleft, p, mapGrid, walls, doors):
    global debuging
    if debugging:
        print "scanning room, start pos in room = ", p
    s = addVec (p, [0, 0])
    a = addVec (p, [-1, -1])
    d = 1  # 0 up, 1 right, 2 down, 3 left
    leftVec = [[-1, 0], [0, -1], [1, 0], [0, 1]]
    forwardVec = [[0, -1], [1, 0], [0, 1], [-1, 0]]
    if debugging:
        print "wall corner", p

    doorStartPoint = None
    doorEndPoint = None
    while True:
        if debugging:
            print "point currently at", p, d
        if (doorStartPoint == None) and lookingLeft (p, leftVec[d], mapGrid, '. '):
            if debugging:
                print "seen first point", p
            # first point on the wall is a door
            doorStartPoint = addVec (p, leftVec[d])
            doorEndPoint = doorStartPoint
        if lookingLeft (addVec (p, forwardVec[d]), leftVec[d], mapGrid, '. '):
            if debugging:
                print "seen a door point", p,
            if doorStartPoint == None:
                doorStartPoint = addVec (addVec (p, forwardVec[d]), leftVec[d])
            doorEndPoint = addVec (addVec (p, forwardVec[d]), leftVec[d])
        else:
            # end of door?
            if doorEndPoint != None:
                doors += [[doorStartPoint, doorEndPoint]]
                doorStartPoint = None
                doorEndPoint = None
        if lookingLeft (addVec (p, forwardVec[d]), leftVec[d], mapGrid, 'x '):
            # carry on
            p = addVec (p, forwardVec[d])
        elif lookingLeft (addVec (p, forwardVec[d]), leftVec[d], mapGrid, 'x.'):
            if debugging:
                print "wall corner (x.)", p
            walls, a = addWall (walls, a, addVec (addVec (p, forwardVec[d]), leftVec[d]))
            # end of door?
            if doorEndPoint != None:
                doors += [[doorStartPoint, doorEndPoint]]
            doorStartPoint = None
            doorEndPoint = None
            # turn right
            d = (d + 1) % 4
            if s == p:
                # back to the start
                return walls, doors
        elif lookingLeft (addVec (p, forwardVec[d]), leftVec[d], mapGrid, 'xx'):
            if debugging:
                print "wall corner (xx)", p
            walls, a = addWall (walls, a, addVec (addVec (p, forwardVec[d]), leftVec[d]))
            # end of door?
            if doorEndPoint != None:
                doors += [[doorStartPoint, doorEndPoint]]
            doorStartPoint = None
            doorEndPoint = None
            # turn right
            d = (d + 1) % 4
            if s == p:
                # back to the start
                return walls, doors
        elif lookingLeft (addVec (p, forwardVec[d]), leftVec[d], mapGrid, '  '):
            if debugging:
                print "wall corner (  )", p,
            # walls, a = addWall (walls, a, addVec (addVec (p, forwardVec[d]), leftVec[d]))
            walls, a = addWall (walls, a, addVec (p, leftVec[d]))
            if debugging:
                print "at point", a
            # turn left
            p = addVec (p, forwardVec[d])
            d = (d + 3) % 4
            if s == p:
                # back to the start
                return walls, doors
        else:
            error ("scanning room at %s has gone wrong, maybe the room is too small\n", p)

#
#  checkLight - add a mid light if lightCount == lightFrequency
#

def checkLight (p, l, lightCount):
    if lightCount == lightFrequency:
        li = light ()      # create light
        li.settype ('MID') # on a pillar
        l += [p + [li]]    # [position and light]
        lightCount = 0
    else:
        lightCount += 1
    return l, lightCount


def introduceLights (topleft, pos, mapGrid, walls, doors):
    global debuging
    
    s = pos
    a = addVec (pos, [-1, -1])
    d = 1  # 0 up, 1 right, 2 down, 3 left
    leftVec = [[-1, 0], [0, -1], [1, 0], [0, 1]]
    forwardVec = [[0, -1], [1, 0], [0, 1], [-1, 0]]
    if debugging:
        print "wall corner", pos
    lightCount = 0
    lights = []
    doorStartPoint = None
    doorEndPoint = None
    needToAvoidDoor = False

    while True:
        if debugging:
            print "point currently at", pos, d

        if (doorStartPoint == None) and lookingLeft (pos, leftVec[d], mapGrid, '. '):
            if debugging:
                print "seen first point", pos
            # first point on the wall is a door
            doorStartPoint = addVec (pos, leftVec[d])
            doorEndPoint = doorStartPoint
            needToAvoidDoor = True

        if lookingLeft (addVec (pos, forwardVec[d]), leftVec[d], mapGrid, '. '):
            if debugging:
                print "seen a door point", pos,
            if doorStartPoint == None:
                doorStartPoint = addVec (addVec (pos, forwardVec[d]), leftVec[d])
            doorEndPoint = addVec (addVec (pos, forwardVec[d]), leftVec[d])
            needToAvoidDoor = True
        else:
            # end of door?
            if doorEndPoint != None:
                doorStartPoint = None
                doorEndPoint = None
                needToAvoidDoor = True

        if lookingLeft (addVec (pos, forwardVec[d]), leftVec[d], mapGrid, 'x '):
            # carry on
            if needToAvoidDoor:
                li = light ()
                li.settype ('FLOOR')
                lights += [pos + [li]]
            else:
                lights, lightCount = checkLight (pos, lights, lightCount)
            needToAvoidDoor = False
            pos = addVec (pos, forwardVec[d])
        elif lookingLeft (addVec (pos, forwardVec[d]), leftVec[d], mapGrid, 'x.'):
            if debugging:
                print "wall corner (x.)", pos
            doorStartPoint = None
            doorEndPoint = None
            # turn right
            d = (d + 1) % 4
            if s == pos:
                # back to the start
                return lights
        elif lookingLeft (addVec (pos, forwardVec[d]), leftVec[d], mapGrid, 'xx'):
            if debugging:
                print "wall corner (xx)", pos
            doorStartPoint = None
            doorEndPoint = None
            # turn right
            d = (d + 1) % 4
            if s == pos:
                # back to the start
                return lights
        elif lookingLeft (addVec (pos, forwardVec[d]), leftVec[d], mapGrid, '  '):
            if debugging:
                print "wall corner (  )", pos,
            # turn left
            pos = addVec (pos, forwardVec[d])
            d = (d + 3) % 4
            if s == pos:
                # back to the start
                return lights
        else:
            printf ("something went wrong here\n")
            
    return [] # and replaces this line

def printCoord (c, o):
    global maxy
    o.write (str (c[0]+1) + " " + str ((maxy-c[1])+1))
    return o


def printMonsters (mlist, o):
    if mlist != []:
        for kind, pos in mlist:
            o.write ("   MONSTER " + kind + " AT ")
            printCoord (pos, o)
            o.write ("\n")
    return o


def printSpawnPlayer (m, o):
    if m != []:
        for pos in m:
            o.write ("   SPAWN PLAYER AT ")
            printCoord (pos, o)
            o.write ("\n")
    return o


def printInside (inside, o):
    if inside != None:
        o.write ("   INSIDE AT ")
        printCoord (inside, o)
        o.write ("\n")
    return o


def printSounds (sounds, o):
    if sounds != []:
        for s in sounds:
            o = s.write (o)
    return o


def printAmmo (m, o):
    if m != []:
        for name, amount, pos in m:
            o.write ("   AMMO " + name + " AMOUNT " + str (amount) + " AT ")
            printCoord (pos, o)
            o.write ("\n")
    return o


def printWeapons (w, o):
    if w != []:
        for name, pos in w:
            o.write ("   WEAPON " + str(name) + " AT ")
            printCoord (pos, o)
            o.write ("\n")
    return o


#
#  printLights - write out the light position and characteristics.
#

def printLights (l, o):
    if l != []:
        for i in l:
            o.write ("   LIGHT AT ")
            printCoord (i, o)
            i[2].write (o)
            o.write ("\n")
    return o


#
#  printDefaults - generate pen format default colour which are applied per room.
#

def printDefaults (r, o):
    for k in rooms[r].defaultColour:
        o.write ("   DEFAULT ")
        o.write (k)
        o.write (" COLOUR ")
        c = rooms[r].defaultColour[k]
        o.write ("%d %d %d\n" % (c[0], c[1], c[2]))


def printRoom (r, o):
    o.write ("ROOM " + str (r) + "\n")
    printDefaults (r, o)
    o.write ("   WALL\n")
    for p in rooms[r].walls:
        o.write ("   ")
        for c in p:
            o.write ("  ")
            printCoord (c, o)
        o.write ("\n")
    for i, d in enumerate (rooms[r].doors):
        o.write ("   DOOR ")
        for c in d:
            printCoord (c, o)
            o.write (" ")
        o.write ("STATUS OPEN LEADS TO " + str (rooms[r].doorLeadsTo[i]) + "\n")
    o = printMonsters (rooms[r].monsters, o)
    o = printAmmo (rooms[r].ammo, o)
    o = printWeapons (rooms[r].weapons, o)
    if autoLights and (rooms[r].lights == []):
        o = printLights (rooms[r].autoLights, o)
    else:
        o = printLights (rooms[r].lights, o)
    o = printSpawnPlayer (rooms[r].worldspawn, o)
    o = printInside (rooms[r].inside, o)
    o = printSounds (rooms[r].sounds, o)
    o.write ("END\n\n")
    return o


def generateRoom (room, pos, mapGrid, start, i):
    global verbose, rooms, debugging

    inside = pos
    pos = moveBy (pos, [-1, -1], mapGrid)
    if debugging:
        print "top left is", pos
    s = pos
    walls, doors = scanRoom (s, pos, mapGrid, [], [])
    if debugging:
        print walls
    rooms[room] = roomInfo (walls, doors)
    rooms[room].autoLights += introduceLights (s, pos, mapGrid, [], [])
    rooms[room].inside = inside


def plot (w, value):
    x0 = min (w[0][0], w[1][0])
    x1 = max (w[0][0], w[1][0])
    y0 = min (w[0][1], w[1][1])
    y1 = max (w[0][1], w[1][1])
    if x0 == x1:
        for j in range (y0, y1+1):
            setFloor (x0, j, value)
    else:
        for i in range (x0, x1+1):
            setFloor (i, y0, value)


def onFloor (r):
    global verbose, rooms, maxx, maxy, wallValue, doorValue

    for w in rooms[r].walls:
        plot (w, wallValue)
    for d in rooms[r].doors:
        plot (d, doorValue)


def findMax (r):
    global rooms, maxx, maxy
    for w in rooms[r].walls:
        for c in w:
            maxx = max (c[0], maxx)
            maxy = max (c[1], maxy)


def dumpFloor ():
    print "the map"
    for r in floor:
        for c in r:
            if c == emptyValue:
                print " ",
            elif c == doorValue:
                print ".",
            elif c == wallValue:
                print "#",
            else:
                print str (c),
        print " "
    print " "


def floodFloor (r, p):
    if p[0] >= 0 and p[1] >= 0:
        if getFloor (p[0], p[1]) == emptyValue:
            setFloor (p[0], p[1], r)
            floodFloor (r, [p[0]-1, p[1]])
            floodFloor (r, [p[0]+1, p[1]])
            floodFloor (r, [p[0], p[1]-1])
            floodFloor (r, [p[0], p[1]+1])


def floodRoom (r, p):
    floodFloor (int (r), p)


#
#  isVertical - return True if, c, is a vertical line.
#

def isVertical (c):
    return c[0][0] == c[1][0]

#
#  isHorizontal - return True if, c, is a horizontal line.
#

def isHorizontal (c):
    return c[0][1] == c[1][1]


#
#  isUpon - returns true if line, d, is upon, w.
#

def isUpon (d, w):
    if isVertical (w):
        if w[0][0] != d[0][0]:
            return False
        d0 = min (d[0][1], d[1][1])
        d1 = max (d[0][1], d[1][1])
        w0 = min (w[0][1], w[1][1])
        w1 = max (w[0][1], w[1][1])
    else:
        if w[0][1] != d[0][1]:
            return False
        d0 = min (d[0][0], d[1][0])
        d1 = max (d[0][0], d[1][0])
        w0 = min (w[0][0], w[1][0])
        w1 = max (w[0][0], w[1][0])
    return (d0 > w0) and (d1 < w1)


#
#  findWall - return the wall which door, d, is upon.
#

def findWall (r, d):
    for w in rooms[r].walls:
        if isUpon (d, w):
            return w

def findDoors (r, p):
    for d in rooms[r].doors:
        w = findWall (r, d)
        if isVertical (w):
            # vertical door as it is on a vertical wall
            if getFloor (d[0][0]+1, d[0][1]) != int (r):
                rooms[r].doorLeadsTo += [getFloor (d[0][0]+1, d[0][1])]
            else:
                rooms[r].doorLeadsTo += [getFloor (d[0][0]-1, d[0][1])]
        else:
            # horizontal door as it is on a horizontal wall
            if getFloor (d[0][0], d[0][1]+1) != int (r):
                rooms[r].doorLeadsTo += [getFloor (d[0][0], d[0][1]+1)]
            else:
                rooms[r].doorLeadsTo += [getFloor (d[0][0], d[0][1]-1)]

#
#  light - define the characteristics of the light
#

class light:
    def __init__ (self):
        self.r = None
        self.g = None
        self.b = None
        self.orientation = None
    def write (self, f):
        if self.r != None:
            f.write (" COLOUR ")
            f.write ("%d %d %d" % (self.r, self.g, self.b))
        if self.orientation != None:
            f.write (" ON ")
            f.write (self.orientation)
    def setcolour (self, r, g, b):
        self.r = r
        self.g = g
        self.b = b
    def settype (self, t):
        self.orientation = t
    def gettype (self):
        return self.orientation

class sound:
    def __init__ (self, pos, filename):
        self.pos = pos
        self.filename = filename
        self.volume = None
        self.looping = False
        self.wait = None
    def setVolume (self, volume):
        self.volume = volume
    def setLooping (self):
        self.looping = True
    def setWait (self, wait):
        self.wait = wait
    def write (self, f):
        f.write ("   SOUND AT ")
        printCoord (self.pos, f)
        f.write (" %s " % self.filename)
        if self.volume != None:
            f.write ("VOLUME %d " % self.volume)
        if self.looping != None:
            f.write ("LOOPING ")
        if self.wait != None:
            f.write ("WAIT %d " % self.wait)
        f.write ("\n")
        return f


#
#  ebnf := worldSpawn | ammoDef | lightDef | defaultDef | monsterDef | weaponDef | soundDef =:
#
#  worldSpawn := 'worldspawn' =:
#  ammoDef := 'ammo' string int =:
#  lightDef := { 'light' [ 'type' ( 'floor' | 'mid' | 'ceil' ) ] [ colourDef ] } =:
#  defaultDef := 'default' ( 'floor' | 'mid' | 'ceil' ) colourDef =:
#  colourDef := 'colour int int int' =:
#  monsterDef := 'monster' string =:
#  weaponDef := 'weapon' int =:
#  soundDef := 'sound' filename { "volume" int | "looping" | "wait" int } =:
#

def parseColour (l, room, x, y):
    expect ('colour', room, x, y)
    r = expectInt (room, x, y, "red colour component")
    g = expectInt (room, x, y, "green colour component")
    b = expectInt (room, x, y, "blue colour component")
    l.setcolour (r, g, b)
    if debugging:
        print "colour complete", l.r, l.g, l.b
    return l


#
#  parseLight - lightDef := 'light' [ 'type' ( 'floor' | 'mid' | 'ceil' ) ] [ colourDef ] =:
#

def parseLight (room, x, y):
    global tokens
    expect ('light', room, x, y)
    l = light ()
    if expecting (['type']):
        expect ('type', room, x, y)
        if expecting (['floor']):
            expect ('floor', room, x, y)
            l.settype ('FLOOR')
        elif expecting (['mid']):
            expect ('mid', room, x, y)
            l.settype ('MID')
        elif expecting (['ceil']):
            expect ('ceil', room, x, y)
            l.settype ('CEIL')
    if expecting (['colour']):
        l = parseColour (l, room, x, y)
    return l


#
#  tokenise - return string, k, after tokenising all the keywords.
#

def tokenise (k):
    k = k.rstrip()
    k = k.split("#")[0]
    k = " " + k + " <eoln>"
    for w in ['worldspawn', 'ammo', 'light', 'type', 'floor', 'mid', 'ceil', 'default', 'colour', 'monster', 'weapon', 'room', 'sound', 'volume', 'looping', 'wait']:
        k = k.replace(" " + w + " ", " <" + w + "> ")
    return k.lstrip ()


#
#  expecting - return True if any keyword in, l, matches the start token in tokens.
#

def expecting (l):
    global tokens
    tokens = tokens.lstrip ()
    if debugging:
        print "expecting", tokens
    for w in l:
        if isSubstr (tokens, "<" + w + ">"):
            return True
    return False


#
#  expect - expect to see symbol, w, as the next token.
#

def expect (w, r, x, y):
    global tokens

    tokens = tokens.lstrip ()
    w = w.lstrip ()
    if debugging:
        print "expect", w
    if isSubstr (tokens, "<" + w + ">"):
        if tokens != "":
            tokens = tokens[len (w) + 2:]
    else:
        if debugging:
            print w, tokens
        error ("expecting token " + w + " in room " +
               str (r) + " at " + str (x) + " " + str (y))

#
#  expectInt - return an integer from the token stream.
#

def expectInt (r, x, y, message):
    global tokens
    tokens = tokens.lstrip ()
    if tokens[0] == '<':
        w = tokens.split ()[0]
        error ("expecting integer " + message + ", not the token " + w + " in room " +
               str (r) + " at " + str (x) + " " + str (y))
        return 0
    elif tokens[0].isdigit () or (tokens[0] == '-') or (tokens[0] == '+'):
        w = tokens.split ()[0]
        tokens = tokens[len (w):]
        return int (w)
    else:
        w = tokens.split ()[0]
        error ("expecting integer " + message + ", not " + w + " in room " +
               str (r) + " at " + str (x) + " " + str (y))
        return 0

#
#  expectString - return a string in the token stream.
#

def expectString (r, x, y, message):
    global tokens
    tokens = tokens.lstrip ()
    if tokens[0] == '<':
        w = tokens.split ()[0]
        error ("expecting string " + message + ", not the token " + w + " in room " +
               str (r) + " at " + str (x) + " " + str (y))
        return ""
    elif tokens[0].isdigit ():
        w = tokens.split ()[0]
        error ("expecting a string, not an integer " + message + " in room " +
               str (r) + " at " + str (x) + " " + str (y))
        return ""
    else:
        w = tokens.split ()[0]
        tokens = tokens[len (w):]
        return w


#
#  parseDefault - 'default' ( 'floor' | 'mid' | 'ceil' ) colourDef
#

def parseDefault (room, x, y):
    expect ('default', room, x, y)
    if expecting (['floor']):
        expect ('floor', room, x, y)
        l = parseColour (light (), room, x, y)
        l.settype ('FLOOR')
    elif expecting (['mid']):
        expect ('mid', room, x, y)
        l = parseColour (light (), room, x, y)
        l.settype ('MID')
    elif expecting (['ceil']):
        if debugging:
            print "seen ceil"
        expect ('ceil', room, x, y)
        if debugging:
            print "eat ceil"
        l = parseColour (light (), room, x, y)
        if debugging:
            print "finished parseColour"
        l.settype ('CEIL')
    else:
        error ("expecting floor, mid or ceil after default in room " +
               str (r) + " at " + str (x) + " " + str (y))
    rooms[room].defaultColour[l.gettype ()] = [l.r, l.g, l.b]


def parseSound (room, x, y):
    filename = expectString (room, x, y, 'a filename after the sound keyword')
    s = sound ([x, y], filename)
    while expecting (['volume', 'looping', 'wait']):
        if expecting (['volume']):
            expect ('volume', room, x, y)
            n = expectInt (room, x, y, 'a number and quantity after the volume keyword')
            s.setVolume (n)
        elif expecting (['looping']):
            expect ('looping', room, x, y)
            s.setLooping ()
        elif expecting (['wait']):
            expect ('wait', room, x, y)
            n = expectInt (room, x, y, 'a number and quantity after the wait keyword')
            s.setWait (n)
    rooms[room].sounds += [s]


#
#  parseEntity -
#

def parseEntity (room, x, y):
    if expecting (['room']):
        expect ('room', room, x, y)
        i = expectInt (room, x, y, "room number")
        assert (i == int (room))
    elif expecting (['worldspawn']):
        expect ('worldspawn', room, x, y)
        rooms[room].worldspawn += [[x, y]]
    elif expecting (['ammo']):
        if debugging:
            print "before", tokens
        expect ('ammo', room, x, y)
        if debugging:
            print "after", tokens
        s = expectString (room, x, y, 'describing ammo')
        n = expectInt (room, x, y, 'amount of ammo')
        rooms[room].ammo += [[s, n, [x, y]]]
    elif expecting (['weapon']):
        expect ('weapon', room, x, y)
        n = expectInt (room, x, y, 'a number and quantity after the keyword weapon')
        rooms[room].weapons += [[n, [x, y]]]
    elif expecting (['monster']):
        expect ('monster', room, x, y)
        name = expectString (room, x, y, 'a string after the keyword monster')
        rooms[room].monsters += [[name, [x, y]]]
    elif expecting (['light']):
        while expecting (['light']):
            l = parseLight (room, x, y)
            rooms[room].lights += [[x, y, l]]
    elif expecting (['default']):
        parseDefault (room, x, y)
    elif expecting (['sound']):
        expect ('sound', room, x, y)
        parseSound (room, x, y)
    else:
        w = tokens.split ()[0]
        error ("unexpected token " + w + " in room " +
               str (room) + " at " + str (x) + " " + str (y))


#
#  parseEntities - parse the entities described in, k, in, room, at position, x, y.
#

def parseEntities (k, room, x, y):
    global tokens

    tokens = tokenise (k)
    if debugging:
        print tokens
    while not expecting (['eoln']):
        parseEntity (room, x, y)


#
#  findEntities - scan a room and use the definitions to yield a string
#                 which is then parsed.
#

def findEntities (g, room, p):
    if debugging:
        for l in g:
            print l,
        for l in floor:
            print l
    for y, r in enumerate (g):
        for x in range (maxx+1):
            if getFloor (x, y) == int (room):
                c = r[x]
                if defines.has_key (c):
                    if debugging:
                        print "seen", c, "at", x, y
                        print "pos", x, y, c, "=>",
                    k = macro (defines[c])
                    if debugging:
                        print k
                    parseEntities (k, room, x, y)


#
#  generatePen - generate penguin tower map from, mapGrid.
#                start is the line number in file, i, where
#                the map grid commences.  o is the outputfile.
#

def generatePen (mapGrid, start, i, o):
    global maxx, maxy
    listOfRooms, pos = getListOfRooms (mapGrid, start, i)
    if listOfRooms == []:
        errorLine (start, mapGrid[0], "the map must have at least one room defined")
    else:
        for r, p in zip (listOfRooms, pos):
            vprintf ("[%s]", r)
            generateRoom (r, p, mapGrid, start, i)
        vprintf ("\n")
        for r in listOfRooms:
            findMax (r)
        initFloor (maxx, maxy, emptyValue)
        for r in listOfRooms:
            onFloor (r)
        vprintf ("floor: ")
        for r, p in zip (listOfRooms, pos):
            vprintf ("[%s]", r)
            floodRoom (r, p)
        vprintf ("\n")
        vprintf ("doors: ")
        for r, p in zip (listOfRooms, pos):
            vprintf ("[%s]", r)
            findDoors (r, p)
        vprintf ("\n")
        vprintf ("entities: ")
        for r, p in zip (listOfRooms, pos):
            vprintf ("[%s]", r)
            findEntities (mapGrid, r, p)
        vprintf ("\n")
        for r in listOfRooms:
            o = printRoom (r, o)
        o.write ("END.\n")
    return o


#
#  processMap
#

def processMap (i, o):
    global verbose
    vprintf ("reading defines: ")
    i = readDefines (i)
    vprintf ("done\n")
    vprintf ("reading map: ")
    g, s = readMap (i)
    vprintf ("done\n")
    vprintf ("generate pen map: ")
    generatePen (g, s, i, o)
    vprintf ("done\n")
    return o


#
#  main - handle the input/output file options and call processMap.
#

def main ():
    global inputFile
    io = handleOptions ()
    if io[0] == None:
        # input file not set so use stdin
        inputFile = 'stdin'
        i = sys.stdin
    else:
        inputFile = io[0]
        i = open (io[0], 'r')
    if io[1] == None:
        # output file not set so use stdout
        o = sys.stdout
    else:
        o = open (io[1], 'w')
    o = processMap (i.readlines (), o)
    o.flush ()


main ()
