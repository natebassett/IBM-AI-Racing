
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
# TORCS RULE-BASED ANTI-SPIN RACING RUNNER V1.7
#############################################

import math
import csv
import os
from datetime import datetime

# ================= SPEED TARGETS =================

TARGET_SPEED = 216
FAST_BEND_SPEED = 202
SHALLOW_BEND_SPEED = 180
MEDIUM_CORNER_SPEED = 138
TIGHT_CORNER_SPEED = 106
HAIRPIN_SPEED = 82

# ================= STEERING CONTROL =================

ANGLE_STEER_GAIN = 17.0
CENTERING_GAIN = 0.38
SENSOR_STEER_GAIN = 0.082

# Racing line offset: conservative but allows better use of track.
MAX_OUTSIDE_OFFSET = 0.40
MEDIUM_OUTSIDE_OFFSET = 0.28
TIGHT_OUTSIDE_OFFSET = 0.14

STEER_SMOOTHING = 0.845
MAX_STEER_CHANGE = 0.060
STEER_DEADZONE = 0.010

SAFE_TRACK_LIMIT = 0.76
HARD_TRACK_LIMIT = 0.92

# Anti-spin / lateral stability tuning.
LATERAL_SPEED_LIMIT = 14.0
HIGH_LATERAL_SPEED_LIMIT = 24.0
LATERAL_STEER_DAMPING = 0.012

ENABLE_TRACTION_CONTROL = True
ENABLE_DEBUG_OUTPUT = True
ENABLE_CSV_LOGGING = True
LOG_EVERY_N_STEPS = 1

GEAR_SPEEDS = [0, 45, 85, 125, 165, 205]

TRACK_SENSOR_ANGLES = [-45, -19, -12, -7, -4, -2.5, -1.7, -1, -0.5,
                       0, 0.5, 1, 1.7, 2.5, 4, 7, 12, 19, 45]


# ================= STARTUP =================

def validate_parameters():
    print("\n========== TORCS RULE-BASED ANTI-SPIN RACING RUNNER V1.7 ==========")
    print(f"TARGET_SPEED:        {TARGET_SPEED}")
    print("Control model:       approach -> apex -> exit")
    print("Stability layer:     enabled")
    print("CSV logging:         enabled")
    print("Failsafe shutdown:   enabled")
    print("==========================================================\n")


def clamp(value, lower, upper):
    return max(lower, min(upper, value))


def sign(value):
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


# ================= CSV LOGGING =================

def create_csv_logger():
    if not ENABLE_CSV_LOGGING:
        return None, None

    script_dir = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.join(
        script_dir,
        "torcs_antispin_racing_log_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv"
    )

    logfile = open(filename, "w", newline="")
    writer = csv.writer(logfile)

    writer.writerow([
        "step", "speedX", "speedY", "speedZ", "angle", "trackPos", "damage",
        "rpm", "gear", "accel", "brake", "steer", "targetSpeed",
        "section", "phase", "front", "front_delta", "best_i", "best_distance",
        "anglePlan", "severity", "desired_track_pos", "emergency_front_brake",
        "stability_mode", "stuck_counter",
        "track_0", "track_1", "track_2", "track_3", "track_4", "track_5",
        "track_6", "track_7", "track_8", "track_9", "track_10", "track_11",
        "track_12", "track_13", "track_14", "track_15", "track_16",
        "track_17", "track_18"
    ])

    print(f"[CSV] Logging telemetry to: {filename}")
    return logfile, writer


def write_csv_log(writer, S, R, step, stuck_counter, prev_front):
    if writer is None or step % LOG_EVERY_N_STEPS != 0:
        return

    plan = plan_next_curve(S, prev_front)
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
        get_dynamic_target_speed(S, prev_front),
        plan["section"],
        plan["phase"],
        plan["front"],
        plan["front_delta"],
        plan["best_i"],
        plan["best_distance"],
        plan["best_angle"],
        plan["severity"],
        get_desired_track_pos(S, plan),
        get_emergency_front_brake(S),
        is_stability_mode(S),
        stuck_counter,
    ] + track)


# ================= PLANNING =================

def get_best_sensor(S):
    track = S["track"]
    front = track[9]

    # Wider search when road ahead is closing, narrower search on straights.
    if front < 65:
        candidate_indices = range(4, 15)
    else:
        candidate_indices = range(6, 13)

    best_i = 9
    best_score = track[9] * 1.12

    for i in candidate_indices:
        distance = track[i]
        offset = abs(i - 9)

        if front < 65:
            centre_penalty = 1.0 - (offset * 0.035)
        else:
            centre_penalty = 1.0 - (offset * 0.10)

        score = distance * centre_penalty

        if score > best_score:
            best_score = score
            best_i = i

    return best_i


def is_controlled_low_speed_bend(S):
    """
    True when the car is already slow enough, stable, and inside the legal
    track limits. In this state, a short centre sensor does not always mean
    panic-brake; it can simply be the car looking across the inside of a bend.
    """
    return (
        S["speedX"] < 92
        and abs(S["trackPos"]) < 0.56
        and abs(S["angle"]) < 0.46
        and abs(S["speedY"]) < 5.2
        and not is_stability_mode(S)
    )


def is_slow_tight_rotation_zone(S, plan):
    """
    Hairpin/slow-bend rotation helper.

    V1.6 became safer through the bend, but it sometimes under-rotated and
    almost drove straight on. This detects the stable low-speed tight section
    where we can safely ask for quicker steering without changing the rest of
    the runner's logic.
    """
    return (
        plan["section"] in ["TIGHT", "HAIRPIN"]
        and plan["front"] < 42
        and S["speedX"] < 105
        and abs(S["trackPos"]) < 0.74
        and abs(S["speedY"]) < 7.2
        and abs(S["angle"]) < 0.70
        and not is_stability_mode(S)
    )


def get_emergency_front_brake(S):
    speed = S["speedX"]
    front = S["track"][9]
    controlled_bend = is_controlled_low_speed_bend(S)

    # V1.5 was panic-braking this section down to ~40 km/h because front
    # briefly sits around 10-14m. If the car is stable and centred, use a
    # lighter safety brake instead of a full stop.
    if front < 8 and speed > 30:
        return 0.42 if controlled_bend and speed < 72 else 1.00
    if front < 14 and speed > 55:
        return 0.28 if controlled_bend and speed < 84 else 1.00
    if front < 22 and speed > 85:
        return 0.75 if controlled_bend else 1.00
    if front < 32 and speed > 110:
        return 0.90
    if front < 45 and speed > 138:
        return 0.70

    return 0.0


def classify_section(front, planned_angle_abs, best_distance):
    closing = max(0.0, (145.0 - front) / 145.0)
    angle_factor = planned_angle_abs / 19.0
    distance_factor = max(0.0, (125.0 - best_distance) / 125.0)

    severity = (
        0.40 * angle_factor
        + 0.45 * closing
        + 0.15 * distance_factor
    )

    if front > 155 and planned_angle_abs <= 7:
        section = "STRAIGHT"
    elif front > 125 and planned_angle_abs <= 10:
        section = "FAST_BEND"
    elif severity < 0.28:
        section = "FAST_BEND"
    elif severity < 0.46:
        section = "SHALLOW"
    elif severity < 0.66:
        section = "MEDIUM"
    elif severity < 0.88:
        section = "TIGHT"
    else:
        section = "HAIRPIN"

    if front < 18:
        section = "HAIRPIN"
    elif front < 34 and planned_angle_abs >= 4:
        section = "TIGHT"
    elif front < 55 and planned_angle_abs >= 7 and section in ["STRAIGHT", "FAST_BEND", "SHALLOW"]:
        section = "MEDIUM"
    elif front < 55 and planned_angle_abs < 7 and section == "MEDIUM":
        # The old runner treated very shallow bends as medium corners here,
        # which caused an unnecessary drop to roughly 120-165 km/h.
        section = "SHALLOW"

    if front > 145 and section in ["TIGHT", "HAIRPIN"]:
        section = "MEDIUM"

    return section, severity


def get_corner_phase(S, section, front, front_delta):
    speed = S["speedX"]
    angle_abs = abs(S["angle"])

    if section in ["STRAIGHT", "FAST_BEND"]:
        return "STRAIGHT"

    # Before/apex/exit style logic.
    if front_delta < -1.0 and speed > get_section_speed(section) + 8:
        return "APPROACH"

    if front < 42 or angle_abs > 0.42:
        return "APEX"

    if front_delta > 0.5 and angle_abs < 0.32:
        return "EXIT"

    if speed > get_section_speed(section) + 12:
        return "APPROACH"

    return "APEX"


def plan_next_curve(S, prev_front=None):
    track = S["track"]
    front = track[9]

    if prev_front is None:
        front_delta = 0.0
    else:
        front_delta = front - prev_front

    best_i = get_best_sensor(S)
    best_distance = track[best_i]
    best_angle = TRACK_SENSOR_ANGLES[best_i]
    planned_angle_abs = abs(best_angle)

    section, severity = classify_section(front, planned_angle_abs, best_distance)
    phase = get_corner_phase(S, section, front, front_delta)

    return {
        "front": front,
        "front_delta": front_delta,
        "best_i": best_i,
        "best_distance": best_distance,
        "best_angle": best_angle,
        "planned_angle_abs": planned_angle_abs,
        "severity": severity,
        "section": section,
        "phase": phase,
    }


def get_section_speed(section):
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


def is_stability_mode(S):
    """
    Detect loss of control earlier.

    The previous log showed the car accelerating out of a corner while speedY
    was already rising. This catches that before the full spin happens.
    """
    lateral_speed = abs(S["speedY"])
    forward_speed = max(abs(S["speedX"]), 1.0)
    angle_abs = abs(S["angle"])

    if angle_abs > 0.72:
        return True

    if lateral_speed > HIGH_LATERAL_SPEED_LIMIT:
        return True

    if lateral_speed > LATERAL_SPEED_LIMIT and angle_abs > 0.22:
        return True

    if lateral_speed > forward_speed * 0.32 and forward_speed > 45:
        return True

    return False


def get_predictive_front_speed_cap(S, prev_front=None):
    """
    High-speed look-ahead cap.

    V1.1 was still arriving at the first big bend at ~190-200 km/h while
    the centre distance was falling by about 1m per tick. The normal section
    classifier still called that a fast/shallow bend until it was too late.
    This cap only activates when the road ahead is closing and speed is high,
    so it keeps straights quick but forces earlier braking before the wall.
    """
    front = S["track"][9]
    speed = S["speedX"]

    if prev_front is None:
        front_delta = 0.0
    else:
        front_delta = front - prev_front

    # V1.2 was safe but a little too eager to call shallow bends dangerous.
    # Only cap speed early when the centre distance is genuinely collapsing,
    # or when the car is already very quick and the bend is now close.
    closing_fast = front_delta < -0.85
    closing_near_fast = front_delta < -0.58 and front < 78 and speed > 158

    if not (closing_fast or closing_near_fast) or speed < 125:
        return TARGET_SPEED

    # Progressive look-ahead cap. These values are intentionally softer than
    # V1.2 above 55m so the car can keep speed through wide/shallow bends,
    # but still force braking before the wall at the first big corner.
    if front < 22:
        return 58
    if front < 32:
        return 80
    if front < 44:
        return 104
    if front < 58:
        return 126
    if front < 76:
        return 150
    if front < 98:
        return 170
    if front < 122:
        return 188

    return TARGET_SPEED


def get_high_speed_entry_risk(S, prev_front=None):
    front = S["track"][9]
    speed = S["speedX"]

    if prev_front is None:
        front_delta = 0.0
    else:
        front_delta = front - prev_front

    # This is deliberately not based only on anglePlan because the problem
    # bend can still look shallow through the centre sensor until late.
    # Tightened versus V1.2 so normal fast bends do not get over-braked.
    return speed > 155 and front < 102 and front_delta < -0.72

def get_dynamic_target_speed(S, prev_front=None):
    plan = plan_next_curve(S, prev_front)
    front = plan["front"]
    section = plan["section"]
    phase = plan["phase"]

    if is_stability_mode(S):
        return 45

    if abs(S["trackPos"]) > HARD_TRACK_LIMIT:
        return 50

    if abs(S["trackPos"]) > SAFE_TRACK_LIMIT:
        return 82

    # Direct speed cap from front distance.
    # If the car is stable/centred in a slow bend, do not overreact to a short
    # centre ray; otherwise V1.5 falls to ~40 km/h on the bend shown.
    controlled_bend = is_controlled_low_speed_bend(S)
    if front < 10:
        return 64 if controlled_bend else 42
    if front < 18:
        return 86 if controlled_bend else 60
    if front < 28:
        return 100 if controlled_bend else 82
    if front < 42:
        return 118 if controlled_bend else 105

    base_speed = get_section_speed(section)
    predictive_cap = get_predictive_front_speed_cap(S, prev_front)

    # Corner phases:
    # - approach: slow into the corner
    # - apex: hold/coast
    # - exit: accelerate out
    if phase == "APPROACH":
        phase_speed = max(HAIRPIN_SPEED, base_speed - 18)
    elif phase == "APEX":
        phase_speed = max(HAIRPIN_SPEED, base_speed - 8)
    elif phase == "EXIT":
        phase_speed = min(TARGET_SPEED, base_speed + 12)
    else:
        phase_speed = base_speed

    return min(phase_speed, predictive_cap)


def get_corner_direction(plan):
    return sign(plan["best_angle"])


def get_desired_track_pos(S, plan):
    """
    Conservative pseudo racing line:
    - approach: move slightly outside
    - apex: come closer to centre/small inside, not enough to cut
    - exit: unwind back toward centre
    """
    section = plan["section"]
    phase = plan["phase"]
    direction = get_corner_direction(plan)

    if direction == 0 or section == "STRAIGHT":
        return 0.0

    # Use more of the track instead of constantly forcing the car to centre.
    # Sign convention: positive trackPos is one side of the road; for a right
    # corner, the outside is the opposite side.
    if section == "FAST_BEND":
        outside = 0.18
    elif section == "SHALLOW":
        outside = MAX_OUTSIDE_OFFSET
    elif section == "MEDIUM":
        outside = MEDIUM_OUTSIDE_OFFSET
    else:
        outside = TIGHT_OUTSIDE_OFFSET

    outside_pos = -direction * outside

    # Tight bends need a clearer rotation command. V1.6 kept this too small,
    # so the car sometimes turned shallow and crawled through the bend.
    if section in ["TIGHT", "HAIRPIN"]:
        apex_pos = direction * min(0.22, outside * 0.95)
    else:
        apex_pos = direction * min(0.14, outside * 0.48)

    if phase == "APPROACH":
        return outside_pos

    if phase == "APEX":
        return apex_pos

    if phase == "EXIT":
        # Don't snap back to centre; hold a mild exit line and let speed build.
        return -direction * min(0.10, outside * 0.25)

    return 0.0


# ================= DRIVER CONTROL =================

def calculate_steering(S, previous_steer=0.0, prev_front=None):
    plan = plan_next_curve(S, prev_front)
    speed = S["speedX"]

    if is_stability_mode(S):
        # Stability recovery: stop following racing line, straighten the car.
        lateral_damping = -S["speedY"] * LATERAL_STEER_DAMPING
        raw_steer = (S["angle"] * 8.0 / math.pi) - (S["trackPos"] * 0.9) + lateral_damping
        raw_steer = clamp(raw_steer, -0.85, 0.85)
    else:
        desired_pos = get_desired_track_pos(S, plan)

        angle_gain = ANGLE_STEER_GAIN
        if is_slow_tight_rotation_zone(S, plan):
            angle_gain = 19.5

        angle_correction = S["angle"] * angle_gain / math.pi

        # Correct towards racing-line target, not always centre.
        abs_pos = abs(S["trackPos"])

        if abs_pos > HARD_TRACK_LIMIT:
            pos_gain = 1.25
        elif abs_pos > SAFE_TRACK_LIMIT:
            pos_gain = 0.95
        elif speed > 170:
            pos_gain = CENTERING_GAIN * 0.46
        elif speed > 120:
            pos_gain = CENTERING_GAIN * 0.62
        else:
            pos_gain = CENTERING_GAIN * 0.86

        # If we deliberately asked for an outside/apex position, do not fight it
        # too hard. This is the main racing-line change from V1.4.
        if abs(desired_pos) > 0.05 and abs(S["trackPos"]) < SAFE_TRACK_LIMIT:
            pos_gain *= 0.82
        if is_slow_tight_rotation_zone(S, plan):
            # Let the steering rotate the car instead of dragging it back to
            # centre while it is trying to make the tight bend.
            pos_gain *= 0.68

        position_correction = (S["trackPos"] - desired_pos) * pos_gain

        # Sensor steering only small, and disabled near edge.
        sensor_steer = 0.0
        if abs_pos < 0.68:
            sensor_steer = clamp(plan["best_angle"] / 19.0, -1.0, 1.0) * SENSOR_STEER_GAIN
            if is_slow_tight_rotation_zone(S, plan):
                sensor_steer = clamp(plan["best_angle"] / 19.0, -1.0, 1.0) * 0.19
            elif plan["section"] in ["FAST_BEND", "SHALLOW"] and speed > 95:
                sensor_steer *= 0.75

        # Lateral damping stops the car from continuing to rotate into a spin.
        # If speedY is large, reduce/oppose steering that is feeding the slide.
        lateral_damping = -S["speedY"] * LATERAL_STEER_DAMPING

        raw_steer = angle_correction - position_correction + sensor_steer + lateral_damping

        if is_slow_tight_rotation_zone(S, plan):
            # Commit to the visible opening of the bend. This is deliberately
            # capped so it helps rotation without becoming a spin command.
            raw_steer += clamp(plan["best_angle"] / 19.0, -1.0, 1.0) * 0.16

        # Legal edge recovery override.
        if S["trackPos"] > HARD_TRACK_LIMIT:
            raw_steer -= 0.85
        elif S["trackPos"] < -HARD_TRACK_LIMIT:
            raw_steer += 0.85
        elif S["trackPos"] > SAFE_TRACK_LIMIT:
            raw_steer -= 0.48
        elif S["trackPos"] < -SAFE_TRACK_LIMIT:
            raw_steer += 0.48

        raw_steer = clamp(raw_steer, -1.0, 1.0)

    if abs(raw_steer) < STEER_DEADZONE:
        raw_steer = 0.0

    smoothing = 0.78 if is_slow_tight_rotation_zone(S, plan) else STEER_SMOOTHING
    smoothed = (
        smoothing * previous_steer
        + (1.0 - smoothing) * raw_steer
    )

    plan_front = plan["front"]
    if is_stability_mode(S):
        max_delta = 0.095
    elif abs(S["trackPos"]) > SAFE_TRACK_LIMIT:
        max_delta = 0.080
    elif is_slow_tight_rotation_zone(S, plan):
        max_delta = 0.118
    elif plan_front < 35:
        max_delta = 0.088
    else:
        max_delta = MAX_STEER_CHANGE

    delta = clamp(smoothed - previous_steer, -max_delta, max_delta)
    return clamp(previous_steer + delta, -1.0, 1.0)


def calculate_brake(S, steer, prev_front=None):
    speed = S["speedX"]
    target = get_dynamic_target_speed(S, prev_front)
    plan = plan_next_curve(S, prev_front)

    if is_stability_mode(S):
        # Do not always slam full brake during a slide; that made the car spiral.
        if abs(S["speedY"]) > HIGH_LATERAL_SPEED_LIMIT:
            return 0.45
        return 0.30

    emergency = get_emergency_front_brake(S)
    if emergency > 0:
        return emergency

    if abs(S["trackPos"]) > HARD_TRACK_LIMIT and speed > 30:
        return 1.00

    if abs(S["trackPos"]) > SAFE_TRACK_LIMIT and speed > 50:
        return 0.80

    # High-speed entry risk: brake earlier, but do not over-brake shallow
    # bends. This should hold speed better than V1.2 while still catching the
    # first big corner before it becomes a panic stop.
    if get_high_speed_entry_risk(S, prev_front):
        if speed > target + 38:
            return 0.76
        if speed > target + 23:
            return 0.54
        if speed > target + 10:
            return 0.30

    # Trail braking into corner approach.
    if plan["phase"] == "APPROACH" and speed > target + 8:
        return 0.56

    if speed > target + 42:
        return 1.00

    if speed > target + 26:
        return 0.78

    if speed > target + 14:
        return 0.40

    return 0.0


def calculate_throttle(S, brake, steer, prev_front=None):
    speed = S["speedX"]
    target = get_dynamic_target_speed(S, prev_front)
    plan = plan_next_curve(S, prev_front)

    if brake > 0:
        return 0.0

    # Do not accelerate while the car is still sliding sideways.
    if is_stability_mode(S):
        return 0.0

    if abs(S["speedY"]) > 10.0:
        return 0.0

    if abs(S["speedY"]) > 6.0:
        return 0.12

    if get_high_speed_entry_risk(S, prev_front) and speed > target + 2:
        return 0.0

    if plan["front"] < 18:
        # In a stable tight bend, feed a little throttle to stop the car
        # bogging down; still coast if unsettled or too close to the edge.
        if is_controlled_low_speed_bend(S) and speed < target - 6:
            if speed < 55:
                return 0.40
            return 0.26
        return 0.0

    if abs(S["trackPos"]) > SAFE_TRACK_LIMIT:
        return 0.02

    # Safer launch.
    if speed < 30:
        if abs(S["angle"]) > 0.25 or abs(S["trackPos"]) > 0.45:
            return 0.20
        return 0.45

    if speed < 80:
        if abs(S["angle"]) > 0.30:
            return 0.25
        return 0.60

    # Apex: still cautious, but do not over-coast on wide/fast corners.
    if plan["phase"] == "APEX":
        if plan["section"] in ["TIGHT", "HAIRPIN"] and is_controlled_low_speed_bend(S):
            if speed < target - 12:
                return 0.28
            if speed < target - 4:
                return 0.16
            return 0.06
        if plan["section"] in ["FAST_BEND", "SHALLOW"] and abs(S["angle"]) < 0.25 and abs(S["speedY"]) < 4.5:
            # Carry a bit more throttle on settled wide bends instead of
            # coasting too much; this is where V1.2 lost time.
            if plan["front"] > 70 and speed < target - 8:
                return 0.42
            return 0.34 if speed < target - 10 else 0.16
        if speed < target - 15 and abs(S["angle"]) < 0.35:
            return 0.30
        return 0.10

    # Exit: accelerate only when the car is settled, but a little harder
    # than the original so straights are not capped around 165 km/h.
    if plan["phase"] == "EXIT":
        if abs(S["angle"]) > 0.24 or abs(S["speedY"]) > 5.8:
            return 0.12
        if speed < target - 25:
            return 0.85
        if speed < target - 8:
            return 0.45
        return 0.16

    if speed < target - 35:
        return 1.00

    if speed < target - 15:
        return 0.65

    if speed < target - 5:
        return 0.30

    return 0.10



def smooth_accel(previous_accel, desired_accel, brake, S, plan):
    """
    Light throttle smoothing. V1.4 smoothed too much and lost corner speed;
    this only removes the harsh pulses while still letting the car accelerate
    out of stable corners.
    """
    if brake > 0:
        return 0.0

    if plan["section"] in ["TIGHT", "HAIRPIN"] or is_stability_mode(S):
        max_up = 0.13
        max_down = 0.24
    elif plan["phase"] in ["APEX", "EXIT"]:
        max_up = 0.14
        max_down = 0.26
    else:
        max_up = 0.24
        max_down = 0.34

    delta = desired_accel - previous_accel
    if delta > max_up:
        return previous_accel + max_up
    if delta < -max_down:
        return previous_accel - max_down
    return desired_accel

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


# ================= FAILSAFE =================

def should_shutdown(S, stuck_counter):
    if S.get("damage", 0) > 500:
        return True, "damage limit exceeded"

    if abs(S.get("trackPos", 0)) > 1.15:
        return True, "out of bounds"

    # Allow the stability layer a chance before killing.
    if abs(S.get("angle", 0)) > 2.2:
        return True, "wrong direction"

    if stuck_counter > 180:
        return True, "car stuck"

    return False, ""


# ================= OUTPUT =================

def print_drive_debug(S, R, step, prev_front=None):
    if not ENABLE_DEBUG_OUTPUT or step % 10 != 0:
        return

    plan = plan_next_curve(S, prev_front)

    print(
        f"step={step:05d} | "
        f"speed={S['speedX']:6.1f} | "
        f"target={get_dynamic_target_speed(S, prev_front):6.1f} | "
        f"section={plan['section']:9s} | "
        f"phase={plan['phase']:8s} | "
        f"front={plan['front']:6.1f} | "
        f"dFront={plan['front_delta']:6.2f} | "
        f"best={plan['best_i']:02d}:{plan['best_distance']:5.1f} | "
        f"anglePlan={plan['best_angle']:5.1f} | "
        f"trackPos={S['trackPos']:7.3f} | "
        f"desired={get_desired_track_pos(S, plan):6.2f} | "
        f"angle={S['angle']:7.3f} | "
        f"stab={is_stability_mode(S)} | "
        f"steer={R['steer']:6.3f} | "
        f"accel={R['accel']:5.2f} | "
        f"brake={R['brake']:5.2f}"
    )


def drive_rule_based(c, step, csv_writer=None):
    S = c.S.d
    R = c.R.d

    if S["speedX"] < 5:
        c.stuck_counter += 1
    else:
        c.stuck_counter = 0

    prev_front = getattr(c, "prev_front", None)

    shutdown, reason = should_shutdown(S, c.stuck_counter)

    if shutdown:
        print(f"\n[FAILSAFE] Shutdown triggered: {reason}")
        R["accel"] = 0.0
        R["brake"] = 1.0
        R["meta"] = 1
        write_csv_log(csv_writer, S, R, step, c.stuck_counter, prev_front)
        return True

    previous_steer = getattr(c, "prev_steer", 0.0)

    steer = calculate_steering(S, previous_steer, prev_front)
    brake = calculate_brake(S, steer, prev_front)
    plan = plan_next_curve(S, prev_front)
    desired_accel = calculate_throttle(S, brake, steer, prev_front)
    desired_accel = apply_traction_control(S, desired_accel)
    previous_accel = getattr(c, "prev_accel", 0.0)
    accel = smooth_accel(previous_accel, desired_accel, brake, S, plan)
    gear = shift_gears(S)

    R["steer"] = steer
    R["brake"] = brake
    R["accel"] = accel
    R["gear"] = gear

    c.prev_steer = steer
    c.prev_accel = accel

    print_drive_debug(S, R, step, prev_front)
    write_csv_log(csv_writer, S, R, step, c.stuck_counter, prev_front)

    c.prev_front = S["track"][9]

    return False


# ================= MAIN LOOP =================

if __name__ == "__main__":
    validate_parameters()

    logfile, csv_writer = create_csv_logger()

    C = Client(p=3001)
    C.prev_steer = 0.0
    C.prev_accel = 0.0
    C.prev_front = None
    C.stuck_counter = 0

    try:
        for step in range(C.maxSteps, 0, -1):
            C.get_servers_input()

            should_stop = drive_rule_based(C, step, csv_writer)

            C.respond_to_server()

            if should_stop:
                break

    finally:
        C.shutdown()

        if logfile is not None:
            logfile.close()
            print("[CSV] Telemetry log saved.")

