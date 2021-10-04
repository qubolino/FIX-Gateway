#!/usr/bin/env python

#  Copyright (c) 2014 Phil Birkelbach
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
#  USA.import plugin

#  This file serves as a starting point for a plugin.  This is a Thread based
#  plugin where the main Plugin class creates a thread and starts the thread
#  when the plugin's run() function is called.

import threading
import time
from collections import OrderedDict
import fixgw.plugin as plugin
import traceback

import smbus2 as smbus#,smbus2
import struct
import math


class MainThread(threading.Thread):
    def __init__(self, parent):
        """The calling object should pass itself as the parent.
           This gives the thread all the plugin goodies that the
           parent has."""
        super(MainThread, self).__init__()
        self.getout = False   # indicator for when to stop
        self.parent = parent  # parent plugin object
        self.log = parent.log  # simplifies logging
        self.count = 0
        self.sleep_time = 1.0/10 # 3 x .005 give +/-60Hz refresh rate

        self.i2c_bus = smbus.SMBus(1)


    def run(self):
        while True:
            try:
                if self.getout:
                    break
                time.sleep(self.sleep_time)
                self.count += 1


                data = bytearray(self.i2c_bus.read_i2c_block_data(0x08,0x00,8))
                # print(data)
                pressure = struct.unpack('f', data[0:4])[0]
                temperature = struct.unpack('f', data[4:8])[0]
                # print(pressure, temperature)

                currentbaro = self.parent.db_read("BARO")[0]
                currentRefPressure = currentbaro * 100 * 1000 / 29.5333727

                altitude = (1 - math.pow(pressure / currentRefPressure, .190284)) * 145366.45


                # print(altitude, temperature, pressure)

                self.parent.db_write("ALT", altitude)
                self.parent.db_write("CAT", temperature)
                self.parent.db_write("AIRPRESS", pressure)

            except Exception as e:
                tb = traceback.format_exc()
                self.log.error("Exception - {}".format(e))
                self.log.error(tb)

        self.running = False

    def stop(self):
        self.getout = True


class Plugin(plugin.PluginBase):
    """ All plugins for FIX Gateway should implement at least the class
    named 'Plugin.'  They should be derived from the base class in
    the plugin module.

    The run and stop methods of the plugin should be overridden but the
    base module functions should be called first."""
    def __init__(self, name, config):
        super(Plugin, self).__init__(name, config)
        self.thread = MainThread(self)

    def run(self):
        """ The run method should return immediately.  The main routine will
        block when calling this function.  If the plugin is simply a collection
        of callback functions, those can be setup here and no thread will be
        necessary"""
        self.thread.start()

    def stop(self):
        """ The stop method should not return until the plugin has completely
        stopped.  This generally means a .join() on a thread.  It should
        also undo any callbacks that were set up in the run() method"""
        self.thread.stop()
        if self.thread.is_alive():
            self.thread.join(1.0)
        if self.thread.is_alive():
            raise plugin.PluginFail

    def get_status(self):
        """ The get_status method should return a dict or OrderedDict that
        is basically a key/value pair of statistics"""
        return OrderedDict({"Count":self.thread.count})
