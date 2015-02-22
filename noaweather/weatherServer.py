#!/usb/bin/python
'''
Noa weather daemon server
'''

from conf import Conf
from gfs import  GFS

import SocketServer
import cPickle
import threading
import os, sys

class clientHandler(SocketServer.BaseRequestHandler):

    def getWeatherData(self, data):
        '''
        Prepares weather response
        '''
        lat, lon = float(data[0]), float(data[1])
        
        response = {
            'gfs': {},
            'wafs': {},
            'metar': {},
            'info': {'lat': lat,
                     'lon': lon,
                     'wafs_cycle': 'na',
                     'gfs_cycle': 'na'
                     }
            }
        
        lat, lon = float(data[0]), float(data[1])
        
        # Parse gfs and wfas
        if gfs.lastgrib:
            response['gfs'] = gfs.parseGribData(gfs.lastgrib, lat, lon)
            response['info']['gfs_cycle'] = gfs.lastgrib
        if gfs.wafs.lastgrib:
            response['wafs'] = gfs.wafs.parseGribData(gfs.wafs.lastgrib, lat, lon)
            response['info']['wafs_cycle'] = gfs.wafs.lastgrib
            
        # Parse metar
        apt = gfs.metar.getClosestStation(gfs.metar.connection, lat, lon)
        if apt and len(apt) > 4:
            response['metar'] = gfs.metar.parseMetar(apt[0], apt[5], apt[3])
        
        return response
    
    def shutdown(self):
        # Shutdown server. Needs to be from a different thread
        def shutNow(srv):
            srv.shutdown()
            
        th = threading.Thread(target = shutNow, args = (self.server, ))
        th.start()
    
    def handle(self):
        response = False
        data = self.request[0].strip("\n\c\t ")
        
        if len(data) > 1:
            if data[0] == '?':
                # weather data request
                sdata = data[1:].split('|')
                if len(sdata) > 1:
                    response = self.getWeatherData(sdata)
                elif len(data) == 5:
                    # Icao
                    response = gfs.metar.getMetar(gfs.metar.connection, data[1:])
            elif data == '!shutdown':
                self.shutdown()
            elif data == '!reload':
                # reload config
                conf.load()
            else:
                return
        
        socket = self.request[1]
        nbytes = 0
        
        if response:
            response = cPickle.dumps(response)
            socket.sendto(response, self.client_address)   
            nbytes = sys.getsizeof(response)
            
        print '%s:%s : %d bytes sent.' % (self.client_address[0], data, nbytes)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        # Joanpc's personal debuggin options
        if sys.platform == 'win32':
            path = 'G:'
        else:
            path = '/Volumes/TO_GO/X-Plane 10'
        
        
    
    conf = Conf(path)
    gfs = GFS(conf)
    gfs.start()
    
    # Open logfile for POSIX systems (windows users can look at the msdows windows)
    if not conf.win32:
        logfile = open(os.sep.join([conf.respath, 'weatherServerLog.txt']), 'a')
        sys.stderr = logfile
        sys.stdout = logfile

    server = SocketServer.UDPServer(("localhost", conf.server_port), clientHandler)
    
    print 'Server started.'
    # Server loop
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    
    # Close gfs worker and save config
    gfs.die.set()
    conf.save()
    print 'Server stoped.'
    if not conf.win32:
        logfile.close()
    
    
    
    