#!/usr/bin/python

#   dwm-pytus is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   dwm-pytus is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with dwm-pytus.  If not, see <http://www.gnu.org/licenses/>.

import sys
sys.path.append(sys.path[0] + "/python-xlib")

from Xlib import display, error
import subprocess
from optparse import OptionParser
import signal
import datetime
import time
import re

VPN_SERVER_LOCATION_FILE = "/tmp/vpn_server_location"
BATTERY_STATUS_FILE = "/sys/class/power_supply/BAT0/uevent"
MEMORY_STATUS_FILE = "/proc/meminfo"
UPTIME_FILE = "/proc/uptime"
INTERVAL = 3.0 # seconds

VERSION = "1.0"

class Status:
    '''
        A class to manage setting the WM_NAME of the X server root window.
        This in dwm has the effect to set the text of the status bar.
    '''
    def __init__(self):
        try :
            self.display = display.Display()
            # the root window, i.e. the screen.
            self.rootw = self.display.screen()['root']
            self.bad = False
        except error.DisplayConnectionError as e:
            print("Failed to connect to display '" + e.display + "': " + e.msg)
            self.bad = True
    def update(self, status):
        if not self.bad:
            self.rootw.set_wm_name_utf8(status)
            self.display.sync()
        else :
            print("Can't update status, display is not connected.")

class Info:
    '''
        A class that retrieves and holds all the info that will go in the status bar.
    '''
    def __init__(self):
        self.volume = -1
        self.now = None
        self.vpnserverlocation = ""
        self.mem = {}
        self.bat = {}
        self.uptime = None
        self.data = {}

        self.refresh()

    def getvolume(self):
        '''
            Returns an integer from 0 to 100.
            If volume is muted return 0.
            It is assumed that right and left channels have the same volume, because we are only measuring one.
        '''
        command = "amixer sget Master"
        proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc.wait() # wait for proc to finish
        amixer_output = proc.stdout.read().decode('ascii')
        amixer_err = proc.stderr.read().decode('ascii')
        volume = -1
        if not amixer_err:
            rx = re.search('\[(\d+)%\] \[(\w+)\]', amixer_output)
            if rx:
                mutestr = rx.group(2)
                if mutestr == "off":
                    volume = 0
                else :
                    volume = int(rx.group(1))
        return volume

    def getdate(self):
        '''
            Returns a datetime object.
        '''
        return datetime.datetime.now()

    def getVPNserverlocation(self):
        '''
            Read an existing file, containing the nation where the VPN Server currently being used resides.
        '''
        try :
            with open(VPN_SERVER_LOCATION_FILE, 'r') as f:
                res = f.read().strip()
        except OSError as ose:
            res = "Error"
            print('Error opening file ' + ose.filename + '\nDescription:\n' + ose.strerror)
        return res

    def getmem(self):
        '''
            Get information on system memory by parsing the /proc/meminfo file and returns it as a dictionary.
            GNU/Linux only.
        '''
        res = {}
        try :
            with open(MEMORY_STATUS_FILE, 'r') as f:
                mem = f.read()
            failed = False
            entries = {'total': 'MemTotal', 'free': 'MemFree', 'buffers': 'Buffers', 'cached': 'Cached'}
            for k in entries:
                rx = re.search(entries[k] + ':\W+(\d+)\W+(.+)', mem)
                if rx:
                    unit = rx.group(2) # Unit of measurement.
                    number = int(rx.group(1))
                    if unit.lower() == "kb":
                        bytesnum = 1000 * number
                    elif unit.lower() == "mb":
                        bytesnum = (10**6) * number
                    elif unit.lower() == "gb":
                        bytesnum = (10**9) * number
                    res[k] = bytesnum
                else :
                    failed = True
                    break
            assert not failed
            res['used'] = res['total'] - res['free'] - res['buffers'] - res['cached'] # as calculated in coreutils' "free"
        except OSError as ose:
            print('Error opening file ' + ose.filename + '\nDescription:\n' + ose.strerror)
        except AssertionError :
            res = {}
            print('An error occurred while parsing file ' + MEMORY_STATUS_FILE + ' for memory info.')
        return res

    def getbat(self):
        '''
            Get information on laptop battery by parsing the BATTERY_STATUS_FILE and returns it as a dictionary.
            GNU/Linux only.
        '''
        res = {}
        try :
            with open(BATTERY_STATUS_FILE, 'r') as f:
                bat = f.read()
            failed = False
            entries = {'status': 'POWER_SUPPLY_STATUS', 'charge': 'POWER_SUPPLY_CAPACITY'}
            # status can be:
            # - Full
            # - Discharging
            # - Charging
            # - Unknown
            # charge is the integer percentage of charge.
            for k in entries:
                rx = re.search(entries[k] + '=(\w+)', bat)
                if rx:
                    res[k] = rx.group(1)
                else :
                    failed = True
                    break
            assert not failed
        except OSError as ose:
            print('Error opening file ' + ose.filename + '\nDescription:\n' + ose.strerror)
        except AssertionError :
            res = {}
            print('An error occurred while parsing file ' + BATTERY_STATUS_FILE + ' for battery info.')
        return res

    def getuptime(self):
        '''
            Get uptime by parsing the UPTIME_FILE and returns it as a timedelta object.
            GNU/Linux only.
        '''
        res = None
        try :
            with open(UPTIME_FILE, 'r') as f:
                uptime = f.read()
            failed = False
            rx = re.search('(\d+)?\.\d+\W.*', uptime)
            if rx:
                secs = int(rx.group(1))
                res = datetime.timedelta(seconds=secs)
            else :
                failed = True
            assert not failed
        except OSError as ose:
            print('Error opening file ' + ose.filename + '\nDescription:\n' + ose.strerror)
        except AssertionError :
            res = ""
            print('An error occurred while parsing file ' + UPTIME_FILE + ' for battery info.')
        return res

    def refresh(self):
        self.volume = self.getvolume()
        self.now = datetime.datetime.now()
        self.vpnserverlocation = self.getVPNserverlocation()
        self.mem = self.getmem()
        self.bat = self.getbat()
        self.uptime = self.getuptime()

        self.data = {'volume': self.volume, 'now': self.now, 'vpnserverlocation': self.vpnserverlocation, 'mem': self.mem, 'bat': self.bat, 'uptime': self.uptime}

class Formatter:
    '''
        A class to provide a nice formatting of the data produced by Info.
        This class scope is to produce the string that will be displayed in the status bar.
    '''
    def __init__(self, data=None, volumebounds={"maxvolume": 66, "halfvolume": 33, "lowvolume": 0}, batbounds={"fullbat": 75, "almostfullbat": 50, "halfbat": 25, "lowbat": 0}, order=['volume', 'uptime', 'vpnserverlocation', 'mem', 'bat', 'date', 'time'], omitonerror=True):
        '''
            The bounds have to be intended in the following way. If the interval is partitioned in n parts, the bounds are the n-1 separators of the components.
            The following examples clarifies what happens at the extremal points:
            100 <= ---- <= 66 ---- <= 33 ---- < 0
        '''
        self.data = data
        self.volumebounds = volumebounds
        self.batbounds = batbounds
        self.order = order
        self.omitonerror = omitonerror
        self.icons = {"chargingbat": "", "fullbat": "", "almostfullbat": "", "halfbat": "", "lowbat": "", "date": "", "time": "", "mem": "", "vpnserverlocation": "🔑", "uptime":"", "maxvolume": "", "halfvolume": "", "lowvolume": "", "mute": ""}
    
    def setdata(self, data):
        self.data = data

    def formatvolume(self):
        icon = self.icons['mute']
        try :
            assert self.data
            assert not self.data['volume'] == -1
            if 100 >= self.data['volume'] and self.data['volume'] > self.volumebounds['maxvolume']:
                icon = self.icons['maxvolume']
            elif self.volumebounds['maxvolume'] >= self.data['volume'] and self.data['volume'] > self.volumebounds['halfvolume']:
                icon = self.icons['halfvolume']
            elif self.volumebounds['halfvolume'] >= self.data['volume'] and self.data['volume'] > self.volumebounds['lowvolume']:
                icon = self.icons['lowvolume']
            if icon == self.icons['mute']:
                res = icon
            else :
                res = icon + " " + str(self.data['volume']) + '%'
        except AssertionError :
            if self.omitonerror :
                res = ""
            else :
                res = icon + " err!"
        return res

    def formatbat(self):
        icon = self.icons['lowbat']
        try :
            assert self.data
            assert self.data['bat']
            status = self.data['bat']['status']
            charge = int(self.data['bat']['charge'])
            if status == "Discharging" or status == "Unknown":
                if 100 >= charge and charge > self.batbounds['fullbat']:
                    icon = self.icons['fullbat']
                elif self.batbounds['fullbat'] >= charge and charge > self.batbounds['almostfullbat']:
                    icon = self.icons['almostfullbat']
                elif self.batbounds['almostfullbat'] >= charge and charge > self.batbounds['halfbat']:
                    icon = self.icons['halfbat']
                elif self.batbounds['halfbat'] >= charge and charge > self.batbounds['lowbat']:
                    icon = self.icons['lowbat']
            elif status == "Charging" or status == "Full":
                icon = self.icons['chargingbat']
            res = icon + " " + str(charge) + '%'
        except AssertionError :
            if self.omitonerror:
                res = ""
            else :
                res = icon + ' err!'
        return res

    def formatdate(self):
        try :
            assert self.data
            assert self.data['now']
            fmt = "%a %d %b" # e.g. Wed 21 Jun
            date = self.data['now'].strftime(fmt)
            res = self.icons['date'] + ' ' + date
        except AssertionError :
            if self.omitonerror:
                res = ""
            else :
                res = self.icons['date'] + ' err!'
        return res

    def formattime(self):
        try :
            assert self.data
            assert self.data['now']
            fmt = "%H:%M" # e.g. 12:03
            time = self.data['now'].strftime(fmt)
            res = self.icons['time'] + ' ' + time
        except AssertionError :
            if self.omitonerror:
                res = ""
            else :
                res = self.icons['time'] + ' err!'
        return res

    def formatuptime(self):
        try :
            assert self.data
            assert self.data['uptime']
            delta = self.data['uptime']
            # timedelta doesn't have strftime(fmt), and only stores days, seconds and microseconds.
            deltasecs = delta.seconds
            deltadays = delta.days
            manymins, secs = divmod(deltasecs, 60)
            hours, mins = divmod(manymins, 60)
            hoursstr = str(hours)
            minsstr = str(mins)
            secsstr = str(secs)
            if len(hoursstr) == 1 :
                hoursstr = '0' + hoursstr
            if len(minsstr) == 1 :
                minsstr = '0' + minsstr
            if len(secsstr) == 1 :
                secsstr = '0' + secsstr
            if deltadays > 0 :
                uptime = str(deltadays) + 'days, ' + hoursstr + ":" + minsstr
            else :
                uptime = hoursstr + ":" + minsstr
            res = self.icons['uptime'] + ' ' + uptime
        except AssertionError :
            if self.omitonerror:
                res = ""
            else :
                res = self.icons['uptime'] + ' err!'
        return res

    def formatmem(self):
        try :
            assert self.data
            assert self.data['mem']
            mem = self.data['mem']['used'] # in bytes
            magnitude = 1
            while not (mem // magnitude > 0 and mem // (magnitude * 1000) == 0):
            # e.g. if mem is 580M we want to stop when order is 10^6. so 580M // 10^6 >0, but 580M // 10^9 = 0.
                magnitude *= 1000
            if magnitude == 1 :
                unit = 'b'
            elif magnitude == 1000 :
                unit = 'K'
            elif magnitude == 10**6 :
                unit = 'M'
            elif magnitude == 10**9 :
                unit = 'G'
            elif magnitude == 10**12 :
                unit = 'T'
            # keep megabytes integer, but display 1 decimal digit for other units
            if unit == 'M':
                mem = mem // magnitude
            else :
                mem = round(mem / magnitude, 1) 
            res = self.icons['mem'] + ' ' + str(mem) + unit
        except AssertionError :
            if self.omitonerror:
                res = ""
            else :
                res = self.icons['mem'] + ' err!'
        return res

    def formatvpnserverlocation(self):
        try :
            assert self.data
            assert self.data['vpnserverlocation']
            vpnserverlocation = self.data['vpnserverlocation']
            res = self.icons['vpnserverlocation'] + ' ' + vpnserverlocation
        except AssertionError :
            if self.omitonerror:
                res = ""
            else :
                res = self.icons['vpnserverlocation'] + ' err!'
        return res

    def getstatusstring(self):
        '''
            Put together all the formatted info produced in the other methods of this class, to get the complete status string, with the order specified in self.order
        '''
        items = {'volume': self.formatvolume(), 'date': self.formatdate(), 'time': self.formattime(), 'vpnserverlocation': self.formatvpnserverlocation(), 'mem': self.formatmem(), 'bat': self.formatbat(), 'uptime': self.formatuptime()}
        res = ""
        separator = '  '
        for it in self.order:
            res += separator + items[it]
        res = res.strip()
        return res

Xstatus = Status()
sysinfo = Info()
formatter = Formatter()
quiet = False
nosetxwm = False
debug = False

def getfreshinfoandsetstatus(signum=None, frame=None):
    if signum and not quiet:
        print("Caught SIGHUP: refreshing!")
    sysinfo.refresh()
    data = sysinfo.data
    if debug:
        print(data)
    formatter.setdata(data)
    statusstr = formatter.getstatusstring()
    if nosetxwm:
        if not quiet:
            print(statusstr)
    else :
        Xstatus.update(statusstr)

def main_loop():
    while True :
        try :
            getfreshinfoandsetstatus()
            time.sleep(INTERVAL)
        except KeyboardInterrupt :
            break
        
if __name__ == "__main__":
    optparser = OptionParser(description="A statusbar python script for dwm.", epilog="dwm-pytus refreshes when it catches a SIGHUP: use this to your advantage, i.e. you can make it more responsive without increasing the interval.", version=VERSION)
    optparser.add_option("-d", "--debug", help="Print the raw data on stdout.", action="store_true", dest="debug")
    optparser.add_option("-n", "--nosetxwm", help="Don't set the statusbar text. Only print it on stdout.", action="store_true", dest="nosetxwm")
    optparser.add_option("-q", "--quiet", help="Whisper to me, baby.", action="store_true", dest="quiet")
    optparser.add_option("-i", "--interval", help=str("Specify how frequently the status string will be updated. Accepts a floating point number of seconds. The default value is " + str(INTERVAL) + "."), action="store", type="float", dest="interval")
    (options, args) = optparser.parse_args()
    if options.quiet and options.debug:
        optparser.error("You can't debug quietly. Quitting.")
    quiet = options.quiet
    nosetxwm = options.nosetxwm
    debug = options.debug
    if options.interval:
        INTERVAL = options.interval
    # Trap SIGHUP and cause it to force a refresh of the status bar.
    signal.signal(signal.SIGHUP, getfreshinfoandsetstatus)
    main_loop()
