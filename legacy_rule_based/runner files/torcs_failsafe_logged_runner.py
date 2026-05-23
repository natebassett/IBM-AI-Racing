
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
# TORCS SAFE LOOKAHEAD PLANNER RUNNER
#############################################

import math
import csv
import os
from datetime import datetime

TARGET_SPEED = 210
FAST_BEND_SPEED = 195
SHALLOW_BEND_SPEED = 175
MEDIUM_CORNER_SPEED = 135
TIGHT_CORNER_SPEED = 95
HAIRPIN_SPEED = 68

# Lower steering gain than the failed planner.
STEER_GAIN = 0.55
ANGLE_GAIN = 0.72
TRACK_POS_GAIN = 0.42

STEER_SMOOTHING = 0.86
MAX_STEER_CHANGE = 0.040
STEER_DEADZONE = 0.015

SAFE_TRACK_LIMIT = 0.70
HARD_TRACK_LIMIT = 0.86

ENABLE_TRACTION_CONTROL = True
ENABLE_DEBUG_OUTPUT = True
ENABLE_CSV_LOGGING = True
LOG_EVERY_N_STEPS = 1

GEAR_SPEEDS = [0, 45, 85, 125, 165, 205]

TRACK_SENSOR_ANGLES = [-45, -19, -12, -7, -4, -2.5, -1.7, -1, -0.5,
                       0, 0.5, 1, 1.7, 2.5, 4, 7, 12, 19, 45]


def validate_parameters():
    print("\n========== TORCS SAFE LOOKAHEAD PLANNER ==========")
    print(f"TARGET_SPEED:        {TARGET_SPEED}")
    print(f"FAST_BEND_SPEED:     {FAST_BEND_SPEED}")
    print(f"SHALLOW_BEND_SPEED:  {SHALLOW_BEND_SPEED}")
    print(f"MEDIUM_CORNER_SPEED: {MEDIUM_CORNER_SPEED}")
    print(f"TIGHT_CORNER_SPEED:  {TIGHT_CORNER_SPEED}")
    print(f"HAIRPIN_SPEED:       {HAIRPIN_SPEED}")
    print("==================================================\n")
    print("[SUCCESS] Parameter sanity checks passed.\n")


def clamp(value, lower, upper):
    return max(lower, min(upper, value))


def plan_next_curve(S):
    """
    Centre-biased lookahead planner.

    This fixes the previous version that aimed too hard at side sensors
    and hit the wall at the start.
    """
    track = S["track"]
    front = track[9]

    # Only use forward-ish sensors. Do not use extreme side sensors for steering.
    candidate_indices = list(range(6, 13))

    best_i = 9
    best_score = track[9] * 1.15  # centre gets a bonus

    for i in candidate_indices:
        distance = track[i]
        offset = abs(i - 9)

        # Heavy centre penalty: side path must be much better to win.
        centre_penalty = 1.0 - (offset * 0.16)
        score = distance * centre_penalty

        if score > best_score * 1.10:
            best_score = score
            best_i = i

    best_distance = track[best_i]
    best_angle = TRACK_SENSOR_ANGLES[best_i]
    planned_angle_abs = abs(best_angle)

    # Better straight detection.
    centre_open = front > 120
    side_not_needed = planned_angle_abs <= 2.5

    closing = max(0.0, (135.0 - front) / 135.0)
    angle_factor = planned_angle_abs / 12.0
    distance_factor = max(0.0, (120.0 - best_distance) / 120.0)

    severity = (
        0.50 * angle_factor
        + 0.35 * closing
        + 0.15 * distance_factor
    )

    if centre_open and side_not_needed:
        section = "STRAIGHT"
    elif front > 145 and planned_angle_abs <= 4:
        section = "STRAIGHT"
    elif front > 120 and planned_angle_abs <= 7:
        section = "FAST_BEND"
    elif severity < 0.26:
        section = "FAST_BEND"
    elif severity < 0.44:
        section = "SHALLOW"
    elif severity < 0.64:
        section = "MEDIUM"
    elif severity < 0.86:
        section = "TIGHT"
    else:
        section = "HAIRPIN"

    # Do not allow hairpin unless genuinely closing.
    if section == "HAIRPIN" and not (front < 50 and planned_angle_abs >= 7):
        section = "TIGHT"

    if front > 135 and section in ["TIGHT", "HAIRPIN"]:
        section = "MEDIUM"

    return {
        "front": front,
        "best_i": best_i,
        "best_distance": best_distance,
        "best_angle": best_angle,
        "planned_angle_abs": planned_angle_abs,
        "severity": severity,
        "section": section,
    }


def get_dynamic_target_speed(S):
    plan = plan_next_curve(S)
    section = plan["section"]

    if abs(S["trackPos"]) > HARD_TRACK_LIMIT:
        return 50
    if abs(S["trackPos"]) > SAFE_TRACK_LIMIT:
        return 80

    if section == "STRAIGHT":
        return TARGET_SPEED
    if section == "FAST_BEND":
        return FAST_BEND_SPEED
    if section == "SHALLOW":
        return SHALLOW_BEND_SPEED
    if section == "MEDIUM":
        return MEDIUM_CORNER_SPEED
    if section == "TIGHT":
        return TIGHT_CORNER_SPEED
    return HAIRPIN_SPEED


def calculate_steering(S, previous_steer=0.0):
    plan = plan_next_curve(S)
    speed = S["speedX"]

    # Low-speed / edge recovery mode.
    # This prevents the start-line wall crash caused by side-sensor oversteer.
    if speed < 80 or abs(S["trackPos"]) > SAFE_TRACK_LIMIT:
        raw_steer = (S["angle"] * 10.0 / math.pi) - (S["trackPos"] * 0.90)

        if S["trackPos"] > HARD_TRACK_LIMIT:
            raw_steer -= 1.00
        elif S["trackPos"] < -HARD_TRACK_LIMIT:
            raw_steer += 1.00

        raw_steer = clamp(raw_steer, -0.75, 0.75)
    else:
        sensor_steer = clamp(plan["best_angle"] / 19.0, -0.65, 0.65)

        raw_steer = (
            sensor_steer * STEER_GAIN
            - S["angle"] * ANGLE_GAIN
            - S["trackPos"] * TRACK_POS_GAIN
        )

        if S["trackPos"] > HARD_TRACK_LIMIT:
            raw_steer -= 1.00
        elif S["trackPos"] < -HARD_TRACK_LIMIT:
            raw_steer += 1.00
        elif S["trackPos"] > SAFE_TRACK_LIMIT:
            raw_steer -= 0.60
        elif S["trackPos"] < -SAFE_TRACK_LIMIT:
            raw_steer += 0.60

        raw_steer = clamp(raw_steer, -1.0, 1.0)

    if abs(raw_steer) < STEER_DEADZONE:
        raw_steer = 0.0

    smoothed = (
        STEER_SMOOTHING * previous_steer
        + (1.0 - STEER_SMOOTHING) * raw_steer
    )

    delta = clamp(smoothed - previous_steer, -MAX_STEER_CHANGE, MAX_STEER_CHANGE)
    return clamp(previous_steer + delta, -1.0, 1.0)

def calculate_brake(S, steer):
    speed = S["speedX"]
    target = get_dynamic_target_speed(S)

    if abs(S["trackPos"]) > HARD_TRACK_LIMIT and speed > 35:
        return 1.00
    if abs(S["trackPos"]) > SAFE_TRACK_LIMIT and speed > 50:
        return 0.80

    if speed > target + 42:
        return 1.00
    if speed > target + 26:
        return 0.78
    if speed > target + 12:
        return 0.45

    return 0.0


def calculate_throttle(S, brake, steer):
    speed = S["speedX"]
    target = get_dynamic_target_speed(S)

    if brake > 0:
        return 0.0

    if abs(S["trackPos"]) > SAFE_TRACK_LIMIT:
        return 0.02

    if speed < 30:
        if abs(S["angle"]) > 0.25 or abs(S["trackPos"]) > 0.45:
            return 0.20
        return 0.45

    if speed < 80:
        if abs(S["angle"]) > 0.30:
            return 0.25
        return 0.60

    if speed < target - 35:
        return 1.00
    if speed < target - 15:
        return 0.65
    if speed < target - 5:
        return 0.30

    return 0.10

def apply_traction_control(S, accel):
    if not ENABLE_TRACTION_CONTROL:
        return accel

    rear_spin = S["wheelSpinVel"][2] + S["wheelSpinVel"][3]
    front_spin = S["wheelSpinVel"][0] + S["wheelSpinVel"][1]
    slip = rear_spin - front_spin

    if slip > 2.5:
        accel -= 0.12

    return clamp(accel, 0.0, 1.0)


def shift_gears(S):
    speed = S["speedX"]
    gear = 1

    for i, threshold in enumerate(GEAR_SPEEDS):
        if speed > threshold:
            gear = i + 1

    return int(clamp(gear, 1, 6))



def create_csv_logger():
    if not ENABLE_CSV_LOGGING:
        return None, None

    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.join(
        SCRIPT_DIR,
        "torcs_run_log_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv"
    )
    logfile = open(filename, "w", newline="")
    writer = csv.writer(logfile)

    writer.writerow([
        "step", "speedX", "speedY", "speedZ", "angle", "trackPos", "damage",
        "rpm", "gear", "accel", "brake", "steer", "targetSpeed",
        "section", "front", "best_i", "best_distance", "anglePlan", "severity",
        "track_0", "track_1", "track_2", "track_3", "track_4", "track_5",
        "track_6", "track_7", "track_8", "track_9", "track_10", "track_11",
        "track_12", "track_13", "track_14", "track_15", "track_16",
        "track_17", "track_18"
    ])

    print(f"[CSV] Logging telemetry to: {filename}")
    return logfile, writer


def write_csv_log(writer, S, R, step):
    if writer is None or step % LOG_EVERY_N_STEPS != 0:
        return

    plan = plan_next_curve(S)
    track = S["track"]

    writer.writerow([
        step,
        S.get("speedX", 0),
        S.get("speedY", 0),
        S.get("speedZ", 0),
        S.get("angle", 0),
        S.get("trackPos", 0),
        S.get("damage", 0),
        S.get("rpm", 0),
        R.get("gear", 0),
        R.get("accel", 0),
        R.get("brake", 0),
        R.get("steer", 0),
        get_dynamic_target_speed(S),
        plan["section"],
        plan["front"],
        plan["best_i"],
        plan["best_distance"],
        plan["best_angle"],
        plan["severity"],
    ] + track)




def should_shutdown(S, stuck_counter):
    """
    Emergency shutdown conditions.

    Prevents the AI from endlessly crashing and producing useless telemetry.
    """

    # Massive wall impact / unrecoverable damage.
    if S.get("damage", 0) > 500:
        return True, "damage limit exceeded"

    # Completely off-track.
    if abs(S.get("trackPos", 0)) > 1.10:
        return True, "out of bounds"

    # Facing mostly the wrong direction.
    if abs(S.get("angle", 0)) > 1.6:
        return True, "wrong direction"

    # Stuck for too long.
    if stuck_counter > 120:
        return True, "car stuck"

    return False, ""


def print_drive_debug(S, R, step):
    if not ENABLE_DEBUG_OUTPUT or step % 10 != 0:
        return

    plan = plan_next_curve(S)

    print(
        f"step={step:05d} | "
        f"speed={S['speedX']:6.1f} | "
        f"target={get_dynamic_target_speed(S):6.1f} | "
        f"section={plan['section']:9s} | "
        f"front={plan['front']:6.1f} | "
        f"best={plan['best_i']:02d}:{plan['best_distance']:5.1f} | "
        f"anglePlan={plan['best_angle']:5.1f} | "
        f"severity={plan['severity']:5.2f} | "
        f"trackPos={S['trackPos']:7.3f} | "
        f"angle={S['angle']:7.3f} | "
        f"steer={R['steer']:6.3f} | "
        f"accel={R['accel']:5.2f} | "
        f"brake={R['brake']:5.2f}"
    )


def drive_planner(c, step, csv_writer=None):
    S = c.S.d
    R = c.R.d

    # Track if the car is stuck.
    if S["speedX"] < 5:
        c.stuck_counter += 1
    else:
        c.stuck_counter = 0

    shutdown, reason = should_shutdown(S, c.stuck_counter)

    if shutdown:
        print(f"\n[FAILSAFE] Shutdown triggered: {reason}")
        R["meta"] = 1
        return True

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
    write_csv_log(csv_writer, S, R, step)

    return False


if __name__ == "__main__":
    validate_parameters()

    logfile, csv_writer = create_csv_logger()

    C = Client(p=3001)
    C.prev_steer = 0.0
    C.stuck_counter = 0

    try:
        for step in range(C.maxSteps, 0, -1):
            C.get_servers_input()

            should_stop = drive_planner(C, step, csv_writer)

            C.respond_to_server()

            if should_stop:
                break
    finally:
        C.shutdown()

        if logfile is not None:
            logfile.close()
            print("[CSV] Telemetry log saved.")

