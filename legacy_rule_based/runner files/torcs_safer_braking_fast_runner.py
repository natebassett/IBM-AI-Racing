
import socket
import sys
import getopt
import os
import time
PI= 3.14159265359

data_size = 2**17

ophelp=  'Options:\n'
ophelp+= ' --host, -H <host>    TORCS server host. [localhost]\n'
ophelp+= ' --port, -p <port>    TORCS port. [3001]\n'
ophelp+= ' --id, -i <id>        ID for server. [SCR]\n'
ophelp+= ' --steps, -m <#>      Maximum simulation steps. 1 sec ~ 50 steps. [100000]\n'
ophelp+= ' --episodes, -e <#>   Maximum learning episodes. [1]\n'
ophelp+= ' --track, -t <track>  Your name for this track. Used for learning. [unknown]\n'
ophelp+= ' --stage, -s <#>      0=warm up, 1=qualifying, 2=race, 3=unknown. [3]\n'
ophelp+= ' --debug, -d          Output full telemetry.\n'
ophelp+= ' --help, -h           Show this help.\n'
ophelp+= ' --version, -v        Show current version.'
usage= 'Usage: %s [ophelp [optargs]] \n' % sys.argv[0]
usage= usage + ophelp
version= "20130505-2"

def clip(v,lo,hi):
    if v<lo: return lo
    elif v>hi: return hi
    else: return v

def bargraph(x,mn,mx,w,c='X'):
    '''Draws a simple asciiart bar graph. Very handy for
    visualizing what's going on with the data.
    x= Value from sensor, mn= minimum plottable value,
    mx= maximum plottable value, w= width of plot in chars,
    c= the character to plot with.'''
    if not w: return '' # No width!
    if x<mn: x= mn      # Clip to bounds.
    if x>mx: x= mx      # Clip to bounds.
    tx= mx-mn # Total real units possible to show on graph.
    if tx<=0: return 'backwards' # Stupid bounds.
    upw= tx/float(w) # X Units per output char width.
    if upw<=0: return 'what?' # Don't let this happen.
    negpu, pospu, negnonpu, posnonpu= 0,0,0,0
    if mn < 0: # Then there is a negative part to graph.
        if x < 0: # And the plot is on the negative side.
            negpu= -x + min(0,mx)
            negnonpu= -mn + x
        else: # Plot is on pos. Neg side is empty.
            negnonpu= -mn + min(0,mx) # But still show some empty neg.
    if mx > 0: # There is a positive part to the graph
        if x > 0: # And the plot is on the positive side.
            pospu= x - max(0,mn)
            posnonpu= mx - x
        else: # Plot is on neg. Pos side is empty.
            posnonpu= mx - max(0,mn) # But still show some empty pos.
    nnc= int(negnonpu/upw)*'-'
    npc= int(negpu/upw)*c
    ppc= int(pospu/upw)*c
    pnc= int(posnonpu/upw)*'_'
    return '[%s]' % (nnc+npc+ppc+pnc)

class Client():
    def __init__(self,H=None,p=None,i=None,e=None,t=None,s=None,d=None,vision=False):
        self.vision = vision

        self.host= 'localhost'
        self.port= 3001
        self.sid= 'SCR'
        self.maxEpisodes=1 # "Maximum number of learning episodes to perform"
        self.trackname= 'unknown'
        self.stage= 3 # 0=Warm-up, 1=Qualifying 2=Race, 3=unknown <Default=3>
        self.debug= False
        self.maxSteps= 100000  # 50steps/second
        self.parse_the_command_line()
        if H: self.host= H
        if p: self.port= p
        if i: self.sid= i
        if e: self.maxEpisodes= e
        if t: self.trackname= t
        if s: self.stage= s
        if d: self.debug= d
        self.S= ServerState()
        self.R= DriverAction()
        self.setup_connection()

    def setup_connection(self):
        try:
            self.so= socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except socket.error as emsg:
            print('Error: Could not create socket...')
            sys.exit(-1)
        self.so.settimeout(1)

        n_fail = 5
        while True:
            a= "-45 -19 -12 -7 -4 -2.5 -1.7 -1 -.5 0 .5 1 1.7 2.5 4 7 12 19 45"

            initmsg='%s(init %s)' % (self.sid,a)

            try:
                self.so.sendto(initmsg.encode(), (self.host, self.port))
            except socket.error as emsg:
                sys.exit(-1)
            sockdata= str()
            try:
                sockdata,addr= self.so.recvfrom(data_size)
                sockdata = sockdata.decode('utf-8')
            except socket.error as emsg:
                print("Waiting for server on %d............" % self.port)
                print("Count Down : " + str(n_fail))
                if n_fail < 0:
                    print("relaunch torcs")
                    os.system('pkill torcs')
                    time.sleep(1.0)
                    if self.vision is False:
                        os.system('torcs -nofuel -nodamage -nolaptime &')
                    else:
                        os.system('torcs -nofuel -nodamage -nolaptime -vision &')

                    time.sleep(1.0)
                    os.system('sh autostart.sh')
                    n_fail = 5
                n_fail -= 1

            identify = '***identified***'
            if identify in sockdata:
                print("Client connected on %d.............." % self.port)
                break

    def parse_the_command_line(self):
        try:
            (opts, args) = getopt.getopt(sys.argv[1:], 'H:p:i:m:e:t:s:dhv',
                       ['host=','port=','id=','steps=',
                        'episodes=','track=','stage=',
                        'debug','help','version'])
        except getopt.error as why:
            print('getopt error: %s\n%s' % (why, usage))
            sys.exit(-1)
        try:
            for opt in opts:
                if opt[0] == '-h' or opt[0] == '--help':
                    print(usage)
                    sys.exit(0)
                if opt[0] == '-d' or opt[0] == '--debug':
                    self.debug= True
                if opt[0] == '-H' or opt[0] == '--host':
                    self.host= opt[1]
                if opt[0] == '-i' or opt[0] == '--id':
                    self.sid= opt[1]
                if opt[0] == '-t' or opt[0] == '--track':
                    self.trackname= opt[1]
                if opt[0] == '-s' or opt[0] == '--stage':
                    self.stage= int(opt[1])
                if opt[0] == '-p' or opt[0] == '--port':
                    self.port= int(opt[1])
                if opt[0] == '-e' or opt[0] == '--episodes':
                    self.maxEpisodes= int(opt[1])
                if opt[0] == '-m' or opt[0] == '--steps':
                    self.maxSteps= int(opt[1])
                if opt[0] == '-v' or opt[0] == '--version':
                    print('%s %s' % (sys.argv[0], version))
                    sys.exit(0)
        except ValueError as why:
            print('Bad parameter \'%s\' for option %s: %s\n%s' % (
                                       opt[1], opt[0], why, usage))
            sys.exit(-1)
        if len(args) > 0:
            print('Superflous input? %s\n%s' % (', '.join(args), usage))
            sys.exit(-1)

    def get_servers_input(self):
        '''Server's input is stored in a ServerState object'''
        if not self.so: return
        sockdata= str()

        while True:
            try:
                sockdata,addr= self.so.recvfrom(data_size)
                sockdata = sockdata.decode('utf-8')
            except socket.error as emsg:
                print('.', end=' ')
            if '***identified***' in sockdata:
                print("Client connected on %d.............." % self.port)
                continue
            elif '***shutdown***' in sockdata:
                print((("Server has stopped the race on %d. "+
                        "You were in %d place.") %
                        (self.port,self.S.d['racePos'])))
                self.shutdown()
                return
            elif '***restart***' in sockdata:
                print("Server has restarted the race on %d." % self.port)
                self.shutdown()
                return
            elif not sockdata: # Empty?
                continue       # Try again.
            else:
                self.S.parse_server_str(sockdata)
                if self.debug:
                    sys.stderr.write("\x1b[2J\x1b[H") # Clear for steady output.
                    print(self.S)
                break # Can now return from this function.

    def respond_to_server(self):
        if not self.so: return
        try:
            message = repr(self.R)
            self.so.sendto(message.encode(), (self.host, self.port))
        except socket.error as emsg:
            print("Error sending to server: %s Message %s" % (emsg[1],str(emsg[0])))
            sys.exit(-1)
        if self.debug: print(self.R.fancyout())

    def shutdown(self):
        if not self.so: return
        print(("Race terminated or %d steps elapsed. Shutting down %d."
               % (self.maxSteps,self.port)))
        self.so.close()
        self.so = None

class ServerState():
    '''What the server is reporting right now.'''
    def __init__(self):
        self.servstr= str()
        self.d= dict()

    def parse_server_str(self, server_string):
        '''Parse the server string.'''
        self.servstr= server_string.strip()[:-1]
        sslisted= self.servstr.strip().lstrip('(').rstrip(')').split(')(')
        for i in sslisted:
            w= i.split(' ')
            self.d[w[0]]= destringify(w[1:])

    def __repr__(self):
        return self.fancyout()
        out= str()
        for k in sorted(self.d):
            strout= str(self.d[k])
            if type(self.d[k]) is list:
                strlist= [str(i) for i in self.d[k]]
                strout= ', '.join(strlist)
            out+= "%s: %s\n" % (k,strout)
        return out

    def fancyout(self):
        '''Specialty output for useful ServerState monitoring.'''
        out= str()
        sensors= [ # Select the ones you want in the order you want them.
        'stucktimer',
        'fuel',
        'distRaced',
        'distFromStart',
        'opponents',
        'wheelSpinVel',
        'z',
        'speedZ',
        'speedY',
        'speedX',
        'targetSpeed',
        'rpm',
        'skid',
        'slip',
        'track',
        'trackPos',
        'angle',
        ]

        for k in sensors:
            if type(self.d.get(k)) is list: # Handle list type data.
                if k == 'track': # Nice display for track sensors.
                    strout= str()
                    raw_tsens= ['%.1f'%x for x in self.d['track']]
                    strout+= ' '.join(raw_tsens[:9])+'_'+raw_tsens[9]+'_'+' '.join(raw_tsens[10:])
                elif k == 'opponents': # Nice display for opponent sensors.
                    strout= str()
                    for osensor in self.d['opponents']:
                        if   osensor >190: oc= '_'
                        elif osensor > 90: oc= '.'
                        elif osensor > 39: oc= chr(int(osensor/2)+97-19)
                        elif osensor > 13: oc= chr(int(osensor)+65-13)
                        elif osensor >  3: oc= chr(int(osensor)+48-3)
                        else: oc= '?'
                        strout+= oc
                    strout= ' -> '+strout[:18] + ' ' + strout[18:]+' <-'
                else:
                    strlist= [str(i) for i in self.d[k]]
                    strout= ', '.join(strlist)
            else: # Not a list type of value.
                if k == 'gear': # This is redundant now since it's part of RPM.
                    gs= '_._._._._._._._._'
                    p= int(self.d['gear']) * 2 + 2  # Position
                    l= '%d'%self.d['gear'] # Label
                    if l=='-1': l= 'R'
                    if l=='0':  l= 'N'
                    strout= gs[:p]+ '(%s)'%l + gs[p+3:]
                elif k == 'damage':
                    strout= '%6.0f %s' % (self.d[k], bargraph(self.d[k],0,10000,50,'~'))
                elif k == 'fuel':
                    strout= '%6.0f %s' % (self.d[k], bargraph(self.d[k],0,100,50,'f'))
                elif k == 'speedX':
                    cx= 'X'
                    if self.d[k]<0: cx= 'R'
                    strout= '%6.1f %s' % (self.d[k], bargraph(self.d[k],-30,300,50,cx))
                elif k == 'speedY': # This gets reversed for display to make sense.
                    strout= '%6.1f %s' % (self.d[k], bargraph(self.d[k]*-1,-25,25,50,'Y'))
                elif k == 'speedZ':
                    strout= '%6.1f %s' % (self.d[k], bargraph(self.d[k],-13,13,50,'Z'))
                elif k == 'z':
                    strout= '%6.3f %s' % (self.d[k], bargraph(self.d[k],.3,.5,50,'z'))
                elif k == 'trackPos': # This gets reversed for display to make sense.
                    cx='<'
                    if self.d[k]<0: cx= '>'
                    strout= '%6.3f %s' % (self.d[k], bargraph(self.d[k]*-1,-1,1,50,cx))
                elif k == 'stucktimer':
                    if self.d[k]:
                        strout= '%3d %s' % (self.d[k], bargraph(self.d[k],0,300,50,"'"))
                    else: strout= 'Not stuck!'
                elif k == 'rpm':
                    g= self.d['gear']
                    if g < 0:
                        g= 'R'
                    else:
                        g= '%1d'% g
                    strout= bargraph(self.d[k],0,10000,50,g)
                elif k == 'angle':
                    asyms= [
                          "  !  ", ".|'  ", "./'  ", "_.-  ", ".--  ", "..-  ",
                          "---  ", ".__  ", "-._  ", "'-.  ", "'\.  ", "'|.  ",
                          "  |  ", "  .|'", "  ./'", "  .-'", "  _.-", "  __.",
                          "  ---", "  --.", "  -._", "  -..", "  '\.", "  '|."  ]
                    rad= self.d[k]
                    deg= int(rad*180/PI)
                    symno= int(.5+ (rad+PI) / (PI/12) )
                    symno= symno % (len(asyms)-1)
                    strout= '%5.2f %3d (%s)' % (rad,deg,asyms[symno])
                elif k == 'skid': # A sensible interpretation of wheel spin.
                    frontwheelradpersec= self.d['wheelSpinVel'][0]
                    skid= 0
                    if frontwheelradpersec:
                        skid= .5555555555*self.d['speedX']/frontwheelradpersec - .66124
                    strout= bargraph(skid,-.05,.4,50,'*')
                elif k == 'slip': # A sensible interpretation of wheel spin.
                    frontwheelradpersec= self.d['wheelSpinVel'][0]
                    slip= 0
                    if frontwheelradpersec:
                        slip= ((self.d['wheelSpinVel'][2]+self.d['wheelSpinVel'][3]) -
                              (self.d['wheelSpinVel'][0]+self.d['wheelSpinVel'][1]))
                    strout= bargraph(slip,-5,150,50,'@')
                else:
                    strout= str(self.d[k])
            out+= "%s: %s\n" % (k,strout)
        return out

class DriverAction():
    '''What the driver is intending to do (i.e. send to the server).
    Composes something like this for the server:
    (accel 1)(brake 0)(gear 1)(steer 0)(clutch 0)(focus 0)(meta 0) or
    (accel 1)(brake 0)(gear 1)(steer 0)(clutch 0)(focus -90 -45 0 45 90)(meta 0)'''
    def __init__(self):
       self.actionstr= str()
       self.d= { 'accel':0.2,
                   'brake':0,
                  'clutch':0,
                    'gear':1,
                   'steer':0,
                   'focus':[-90,-45,0,45,90],
                    'meta':0
                    }

    def clip_to_limits(self):
        """There pretty much is never a reason to send the server
        something like (steer 9483.323). This comes up all the time
        and it's probably just more sensible to always clip it than to
        worry about when to. The "clip" command is still a snakeoil
        utility function, but it should be used only for non standard
        things or non obvious limits (limit the steering to the left,
        for example). For normal limits, simply don't worry about it."""
        self.d['steer']= clip(self.d['steer'], -1, 1)
        self.d['brake']= clip(self.d['brake'], 0, 1)
        self.d['accel']= clip(self.d['accel'], 0, 1)
        self.d['clutch']= clip(self.d['clutch'], 0, 1)
        if self.d['gear'] not in [-1, 0, 1, 2, 3, 4, 5, 6]:
            self.d['gear']= 0
        if self.d['meta'] not in [0,1]:
            self.d['meta']= 0
        if type(self.d['focus']) is not list or min(self.d['focus'])<-180 or max(self.d['focus'])>180:
            self.d['focus']= 0

    def __repr__(self):
        self.clip_to_limits()
        out= str()
        for k in self.d:
            out+= '('+k+' '
            v= self.d[k]
            if not type(v) is list:
                out+= '%.3f' % v
            else:
                out+= ' '.join([str(x) for x in v])
            out+= ')'
        return out
        return out+'\n'

    def fancyout(self):
        '''Specialty output for useful monitoring of bot's effectors.'''
        out= str()
        od= self.d.copy()
        od.pop('gear','') # Not interesting.
        od.pop('meta','') # Not interesting.
        od.pop('focus','') # Not interesting. Yet.
        for k in sorted(od):
            if k == 'clutch' or k == 'brake' or k == 'accel':
                strout=''
                strout= '%6.3f %s' % (od[k], bargraph(od[k],0,1,50,k[0].upper()))
            elif k == 'steer': # Reverse the graph to make sense.
                strout= '%6.3f %s' % (od[k], bargraph(od[k]*-1,-1,1,50,'S'))
            else:
                strout= str(od[k])
            out+= "%s: %s\n" % (k,strout)
        return out

def destringify(s):
    '''makes a string into a value or a list of strings into a list of
    values (if possible)'''
    if not s: return s
    if type(s) is str:
        try:
            return float(s)
        except ValueError:
            print("Could not find a value in %s" % s)
            return s
    elif type(s) is list:
        if len(s) < 2:
            return destringify(s[0])
        else:
            return [destringify(i) for i in s]


#############################################
# CLEAN TORCS RUNNER - SAFE PARAM CONTROLLER
#############################################

import math

# ================= USER CONFIGURABLE PARAMETERS =================

TARGET_SPEED = 205          # Safer starting target speed in km/h.
STEER_GAIN = 13             # Steering sensitivity. 20-30 is a safer range.
CENTERING_GAIN = 0.18       # How strongly the car returns to track centre.
BRAKE_THRESHOLD = 0.10      # Higher = brakes less often. Lower = brakes earlier.
ENABLE_TRACTION_CONTROL = True
ENABLE_DEBUG_OUTPUT = True

# Higher values make the car less twitchy but slower to react.
STEER_SMOOTHING = 0.86

# Maximum amount of track offset we deliberately allow.
# + means right side of track, - means left side of track.
MAX_RACING_LINE_OFFSET = 0.24

# Tiny steering changes cause wobble. Ignore them.
STEER_DEADZONE = 0.025

# Limits how much steering can change per simulation step.
MAX_STEER_CHANGE = 0.045

# Keep the car legal. TORCS trackPos near +/-1 means edge/off-track.
SAFE_TRACK_LIMIT = 0.76

# If the track directly ahead starts shrinking, brake earlier.
EARLY_BRAKE_FRONT_DISTANCE = 115

# Prevent invalid laps by being stricter near the edge.
HARD_TRACK_LIMIT = 0.88

GEAR_SPEEDS = [0, 40, 80, 125, 170, 210]


# ================= PARAMETER CHECKS =================

def validate_parameters():
    print("\n========== TORCS AI PARAMETERS ==========")
    print(f"TARGET_SPEED:             {TARGET_SPEED} km/h")
    print(f"STEER_GAIN:               {STEER_GAIN}")
    print(f"CENTERING_GAIN:           {CENTERING_GAIN}")
    print(f"BRAKE_THRESHOLD:          {BRAKE_THRESHOLD}")
    print(f"GEAR_SPEEDS:              {GEAR_SPEEDS}")
    print(f"TRACTION_CONTROL:         {ENABLE_TRACTION_CONTROL}")
    print("=========================================\n")

    if not 40 <= TARGET_SPEED <= 260:
        raise ValueError("TARGET_SPEED should be between 40 and 260 km/h.")

    if not 5 <= STEER_GAIN <= 60:
        raise ValueError("STEER_GAIN should be between 5 and 60.")

    if not 0.0 <= CENTERING_GAIN <= 2.0:
        raise ValueError("CENTERING_GAIN should be between 0.0 and 2.0.")

    if not 0.0 <= BRAKE_THRESHOLD <= 1.0:
        raise ValueError("BRAKE_THRESHOLD should be between 0.0 and 1.0.")

    if GEAR_SPEEDS != sorted(GEAR_SPEEDS):
        raise ValueError("GEAR_SPEEDS must be in ascending order.")

    if not isinstance(ENABLE_TRACTION_CONTROL, bool):
        raise TypeError("ENABLE_TRACTION_CONTROL must be True or False.")

    print("[SUCCESS] Parameter sanity checks passed.\n")


# ================= CONTROL HELPERS =================

def clamp(value, lower, upper):
    return max(lower, min(upper, value))


def detect_corner_direction(S):
    """
    Estimate upcoming corner direction from TORCS track sensors.
    Returns:
    -1 = left corner ahead
     0 = mostly straight
     1 = right corner ahead
    """
    track = S["track"]

    left_space = track[5] + track[6] + track[7] + track[8]
    right_space = track[10] + track[11] + track[12] + track[13]

    difference = right_space - left_space

    if difference > 25:
        return 1

    if difference < -25:
        return -1

    return 0


def get_racing_line_target_pos(S):
    """
    Safer pseudo racing line.

    The car can still use track width, but it will not aim too close
    to the inside/outside on tight corners. This helps avoid invalid laps.
    """
    track = S["track"]
    front = track[9]

    corner_direction = detect_corner_direction(S)

    # On very tight corners, reduce offset so we do not cut the track.
    if front < 45:
        offset = 0.10
    elif front < 70:
        offset = 0.18
    else:
        offset = MAX_RACING_LINE_OFFSET

    # Right corner: prepare from left side, but not too far.
    if corner_direction == 1:
        return -offset

    # Left corner: prepare from right side, but not too far.
    if corner_direction == -1:
        return offset

    return 0.0


def calculate_steering(S, previous_steer=0.0):
    """
    Smooth steering controller with pseudo racing-line positioning.

    Main anti-wobble changes:
    - weaker steering gain
    - weaker centre correction at high speed
    - deadzone for tiny steering changes
    - rate limiter so steering cannot snap left/right instantly
    """
    speed = S["speedX"]
    target_track_pos = get_racing_line_target_pos(S)

    # At high speed, aggressive corrections create wobble.
    # So we reduce track-position correction as speed rises.
    if speed > 180:
        speed_correction_scale = 0.35
    elif speed > 140:
        speed_correction_scale = 0.50
    elif speed > 100:
        speed_correction_scale = 0.70
    else:
        speed_correction_scale = 1.00

    angle_correction = S["angle"] * STEER_GAIN / math.pi
    racing_line_correction = (
        (S["trackPos"] - target_track_pos)
        * CENTERING_GAIN
        * speed_correction_scale
    )

    raw_steer = angle_correction - racing_line_correction

    # Legal-track recovery.
    # If the car gets close to the edge, override racing-line freedom and pull it back.
    if S["trackPos"] > HARD_TRACK_LIMIT:
        raw_steer -= 0.70
    elif S["trackPos"] < -HARD_TRACK_LIMIT:
        raw_steer += 0.70
    elif S["trackPos"] > SAFE_TRACK_LIMIT:
        raw_steer -= 0.45
    elif S["trackPos"] < -SAFE_TRACK_LIMIT:
        raw_steer += 0.45

    raw_steer = clamp(raw_steer, -1.0, 1.0)

    # Ignore tiny changes around zero because they cause straight-line twitching.
    if abs(raw_steer) < STEER_DEADZONE:
        raw_steer = 0.0

    # Low-pass filter.
    smoothed_steer = (
        STEER_SMOOTHING * previous_steer
        + (1.0 - STEER_SMOOTHING) * raw_steer
    )

    # Rate limiter: steering can only change a little per frame.
    steer_delta = smoothed_steer - previous_steer
    steer_delta = clamp(steer_delta, -MAX_STEER_CHANGE, MAX_STEER_CHANGE)

    final_steer = previous_steer + steer_delta

    return clamp(final_steer, -1.0, 1.0)


def estimate_corner_severity(S, steer):
    """
    Combines current car angle and steering demand.
    This is reactive, so we also use track sensors below for lookahead.
    """
    return max(abs(S["angle"]), abs(steer))


def get_dynamic_target_speed(S):
    """
    Fast but safer dynamic speed target.

    Key change:
    - High speed is still allowed on real straights.
    - If the forward sensor distance drops, the car assumes a tightening bend
      and starts slowing earlier.
    """
    track = S["track"]

    front = track[9]
    near_left = track[7] + track[8]
    near_right = track[10] + track[11]
    wide_left = track[5] + track[6] + track[7] + track[8]
    wide_right = track[10] + track[11] + track[12] + track[13]

    near_imbalance = abs(near_left - near_right) / max(front, 1.0)
    wide_imbalance = abs(wide_left - wide_right) / max(front, 1.0)

    corner_strength = max(near_imbalance, wide_imbalance)

    # Very tight / wall approaching.
    if front < 42 or corner_strength > 1.35:
        return 68

    # Tight corner.
    if front < 62 or corner_strength > 0.95:
        return 92

    # This catches the high-speed tightening bend that caused the invalid lap.
    if front < 90 or corner_strength > 0.62:
        return 120

    # Fast bend, but not full throttle.
    if front < EARLY_BRAKE_FRONT_DISTANCE or corner_strength > 0.38:
        return 150

    # Open straight.
    return TARGET_SPEED

def calculate_brake(S, steer):
    speed = S["speedX"]
    dynamic_target = get_dynamic_target_speed(S)
    corner_severity = estimate_corner_severity(S, steer)
    track_pos = abs(S["trackPos"])

    # Very close to leaving/cutting the track: slow hard.
    if track_pos > HARD_TRACK_LIMIT and speed > 45:
        return 1.00

    # Near legal limit: controlled braking.
    if track_pos > SAFE_TRACK_LIMIT and speed > 60:
        return 0.80

    # Emergency stability braking.
    if speed > 115 and corner_severity > 0.78:
        return 1.00

    # Brake based on how far above dynamic target we are.
    # This is stricter than the previous version.
    if speed > dynamic_target + 35:
        return 1.00

    if speed > dynamic_target + 22:
        return 0.78

    if speed > dynamic_target + 10:
        return 0.48

    return 0.0

def calculate_throttle(S, brake, steer):
    speed = S["speedX"]
    dynamic_target = get_dynamic_target_speed(S)
    corner_severity = estimate_corner_severity(S, steer)
    track_pos = abs(S["trackPos"])

    # Do not fight the brakes.
    if brake > 0.0:
        return 0.0

    # If near track limits, stop accelerating.
    if track_pos > SAFE_TRACK_LIMIT:
        return 0.0

    # If heavily angled at high speed, stabilise.
    if speed > 120 and corner_severity > 0.50:
        return 0.05

    # Fast, safe acceleration below dynamic target.
    if speed < dynamic_target - 35:
        return 1.00

    if speed < dynamic_target - 15:
        return 0.60

    if speed < dynamic_target - 5:
        return 0.25

    return 0.08

def apply_traction_control(S, accel):
    if not ENABLE_TRACTION_CONTROL:
        return accel

    rear_spin = S["wheelSpinVel"][2] + S["wheelSpinVel"][3]
    front_spin = S["wheelSpinVel"][0] + S["wheelSpinVel"][1]
    slip = rear_spin - front_spin

    if slip > 2.0:
        accel -= 0.15

    return clamp(accel, 0.0, 1.0)


def shift_gears(S):
    speed = S["speedX"]
    gear = 1

    for i, speed_threshold in enumerate(GEAR_SPEEDS):
        if speed > speed_threshold:
            gear = i + 1

    return clamp(gear, 1, 6)


def print_drive_debug(S, R, step):
    if not ENABLE_DEBUG_OUTPUT:
        return

    # Print every 10 simulation steps to keep the console readable.
    if step % 10 != 0:
        return

    print(
        f"step={step:05d} | "
        f"speed={S['speedX']:6.1f} | "
        f"angle={S['angle']:7.3f} | "
        f"trackPos={S['trackPos']:7.3f} | "
        f"steer={R['steer']:6.3f} | "
        f"accel={R['accel']:5.2f} | "
        f"brake={R['brake']:5.2f} | "
        f"gear={int(R['gear'])} | "
        f"target={get_dynamic_target_speed(S):5.1f} | "
        f"front={S['track'][9]:5.1f} | "
        f"linePos={get_racing_line_target_pos(S):5.2f}"
    )


# ================= MAIN DRIVE FUNCTION =================

def drive_safe(c, step):
    S = c.S.d
    R = c.R.d

    previous_steer = getattr(c, "prev_steer", 0.0)

    steer = calculate_steering(S, previous_steer)
    brake = calculate_brake(S, steer)
    accel = calculate_throttle(S, brake, steer)
    accel = apply_traction_control(S, accel)
    gear = shift_gears(S)

    R["steer"] = steer
    R["brake"] = brake
    R["accel"] = accel
    R["gear"] = gear

    c.prev_steer = steer

    print_drive_debug(S, R, step)


# ================= MAIN LOOP =================

if __name__ == "__main__":
    validate_parameters()

    C = Client(p=3001)
    C.prev_steer = 0.0

    for step in range(C.maxSteps, 0, -1):
        C.get_servers_input()
        drive_safe(C, step)
        C.respond_to_server()

    C.shutdown()

