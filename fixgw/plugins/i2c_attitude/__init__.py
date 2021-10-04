# coding: utf8
#!/usr/bin/env python

#  Copyright (c) 2017 Jean-Manuel Gagnon
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

import logging
import sys
import threading
import traceback
import time
import math
import smbus2 as smbus#,smbus2
import struct
from collections import OrderedDict
import fixgw.plugin as plugin

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
        self.sleep_time = 1.0/25 # 3 x .005 give +/-60Hz refresh rate

        self.i2c_bus = smbus.SMBus(1)

    def run(self):
        while True:
            try:
                if self.getout:
                    break
                time.sleep(self.sleep_time)
                self.count += 1

                data = bytearray(self.i2c_bus.read_i2c_block_data(0x0D,0x00,4*3))
                # print(struct.unpack('f', data[:4]), struct.unpack('f', data[4:8]), struct.unpack('f', data[8:12]))
                roll = struct.unpack('f', data[0:4])[0] 
                pitch = struct.unpack('f', data[4:8])[0] 
                yaw = struct.unpack('f', data[8:12])[0] 
                # print(roll, pitch, yaw)
                self.parent.db_write("ROLL", -roll)
                self.parent.db_write("PITCH", pitch)
                self.parent.db_write("HEAD", yaw)



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
        print('constucting')
        super(Plugin, self).__init__(name, config)
        print('super done')
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
