#!/usr/bin/env python
#
# Copyright 2013 Cornelis Gotschelm <gotschelm gmail com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import ImageFont, Image, ImageDraw
import pygeoip
#import psutil
import os
import time
import math
import socket
import re
import string

class Ikna(object):
    def __init__(self,  srcimg=None, 
                        dstimg=None, 
                        geoipdb=None,
                        font=None,
                        width=None,
                        height=None,
                        radius=5,
                        fontsize=20,
                        projection=None,
                        xshift=0,
                        yshift=0,
                        datasource=None,
                        statefilter=None,
                        fwlog=None,
                        template="$ip",
                        layer=False,
                        showonlythelast=0,
                        setbg=True):
        
        self.dstimg = dstimg or "/dev/shm/ikna.png"
        self.srcimg = srcimg or "/tmp/worldmap_nolegend_16to9_3200x1800.png"
        self.geoipdb = geoipdb or "/usr/share/GeoIP/GeoLiteCity.dat"
        self.font = font or "/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf"
        self.fontsize = fontsize
        self.imagefont = ImageFont.truetype(self.font, self.fontsize)
        self.statefilter = statefilter
        self.radius = radius
        self.projection = projection or "mercator"
        self.xshift = xshift
        self.yshift = yshift
        self.datasource = datasource or "firewall"
        self.cleanimage = Image.open(self.srcimg)
        self.drawimage = self.cleanimage.copy()
        self.imagewidth, self.imageheight = self.cleanimage.size
        #override size if given
        if width: self.imagewidth = width
        if height: self.imageheight = height
        self.gi = pygeoip.GeoIP(self.geoipdb)
        self.fwlog = fwlog or "/var/log/messages"
        self.setbg=setbg
        self.template=template
        self.layer=layer
        self.rdnscache={}
        self.showonlythelast=showonlythelast
        
    def ip_to_latlon(self, ip):
        """
            Returns latitude, longitude of IP address
        """
        query = self.gi.record_by_addr(ip)
        lat,lon = query['latitude'], query['longitude']
        return (lat,lon)
                
    def coord_to_xy(self, coord):
        """
            Converts latitude and longitude to X,Y coordinates
        """
        lat,lon = coord
        
        if self.projection == "mercator":
            x = (self.imagewidth) * (180 + lon) / 360
            def lat2y(a):
                return math.log(math.tan(((lat*math.pi/180)*.5)+(math.pi*0.25)))
            y = lat2y(lat)
            y = (self.imageheight*.5) - (self.imagewidth*y/(2*math.pi))
        elif projection == "equirectangular":
            x = (self.imagewidth) * (180 + lon) / 360
            y = (self.imageheight) * (90 - lat) / 180
        else:
            print "Unknown map projection type"
            exit()
            
        x = x + self.xshift
        y = y + self.yshift
        return (x,y)
        
    def draw(self, data, layer=False):
        """
            data:
            [((x,y),label),...]
            (x,y) is the coordinate produced by self.ip_to_xy
            label is a string that will be drawn on the coordinate (usually an IP address)
        """
        if not layer: #then get a fresh image
            self.drawimage = self.cleanimage.copy()
        
        #### !! SLICES 
        slce=-self.showonlythelast
        draw = ImageDraw.Draw(self.drawimage)
        num_nodes = len(data[slce:])
        if num_nodes == 0: num_nodes = 1
        colorstep = math.sqrt(255)/num_nodes
        colorx = 0.0
        for node in data[slce:]:
            x,y = node[0]
            text = node[1]
            radius = self.radius
            w,h = self.imagefont.getsize(text)
            draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=(255,0,0))
            #draw.arc((0,0,200,200), 180, 360, fill=(0,255,0))
            if text is not "_blank": #then draw text !
                draw.rectangle((x,y,x+w,y+h), fill=(int(math.pow(colorx,2.0)),0,0))
                draw.text((x,y), text, font=self.imagefont)
            colorx+=colorstep
        
    def get_netstat(self):
        """
            Get active connections using psutil
            Uncomment "#import psutil" above to make this work
        """
        remote_ips = []
        for p in psutil.process_iter():
            try:
                cons = p.get_connections(kind='inet4')
            except psutil.AccessDenied:
                pass
            else:
                for c in cons:
                    if c.remote_address:
                        ip = c.remote_address[0]
                        if ip not in remote_ips:
                            remote_ips.append(ip)
        return remote_ips
        
    def parse_netstat(self):
        """
            Get active connections using netstat
            Return list of dicts, this allows for ordering and easy access
            [ { 'ip': ip, 'port': port }, ]
        """
        remote_ips=[]
        if self.statefilter:
            netout = os.popen("netstat -nt4 | grep " + self.statefilter)
            _data = netout.read()
            data = _data.split("\n")[:-1]
        else:
            netout = os.popen("netstat -nt4")
            _data = netout.read()
            data = _data.split("\n")[2:-1]
        netout.close()
                
        for line in data:
            ip = line.split()[4].split(':')[0]
            port = line.split()[4].split(':')[-1]
            if ip not in remote_ips:
                remote_ips.append( { 'ip' : ip , 'port' : port } )
        return remote_ips
        
    def parse_firewall(self):
        """
            Returns [ {'ip': ip, 'proto': proto, 'port' : port},]
        """
        templist = []
        pat = re.compile(r"^.*SRC=(\d+\.\d+\.\d+\.\d+).*PROTO=([A-Z]*).*DPT=([0-9]*).*$")
        with open(self.fwlog, 'r') as fd:
            for line in fd:
                try:
                    (srcip, proto, dport) = pat.search(line).groups()
                    templist.append( { 'ip' : srcip, 'proto': proto, 'port': dport } )
                except:
                    pass
        #reverse the list before uniqifying so the last log entry will stick
        uniqlist = self._uniqify(templist[::-1]) 
        #if not uniqlist: 
            #print "No firewall data found. Quitting."
            #exit()
        return uniqlist[::-1] #reverse back to the proper order

    def ip_to_xy(self, ip):
        """
            Wrapper function that returns X,Y coords for a given IP
        """
        return self.coord_to_xy(self.ip_to_latlon(ip))

    def makedrawdata(self, data=None, template=None):
        """
            Accepts a list of dicts:
            For example:
            [ { 'ip': '8.8.8.8', 'port': 53 },
              { 'ip': '4.2.2.1', 'customfield': "My custom field 1" } ]
            You can define any custom field and use them in your template
            The 'ip' field is required, note that is has to be a string
              
            Creates [((x,y),label),] to give to self.draw()
        """
        rdns=False
        if template:
            if "$host" in template:
                rdns=True 
        else:
            template=self.template

        tmpl = string.Template(template)
        
        def _apply_template(node):
            subst = {}
            for key,value in node.items():   
                subst[key] = value #this allows all keys to be used as template variables
            for key,value in self.gi.record_by_addr(node['ip']).items():
                subst[key] = value #add pygeoip fields as template variables
            if rdns: #reverse dns takes time... 
                subst['host'] = self.rlookup(node['ip'])
            return tmpl.substitute(subst)
        
        if data:
            return [(self.ip_to_xy(node['ip']), 
                    _apply_template(node)) for node in data]
        if self.datasource == "netstat":
            return [(self.ip_to_xy(node['ip']), 
                    _apply_template(node)) for node in self.parse_netstat()]
        elif self.datasource == "firewall":
            return [(self.ip_to_xy(node['ip']), 
                    _apply_template(node)) for node in self.parse_firewall()]
        else:
            return [((0,0), """Add data yourself with netpaper.update(data=yourdata)  or choose a valid NetPaper.datasource, 'netstat' or 'firewall'""")]
        
    def update(self, data=None, template=None, layer=None):
        """
            Collects data from the datasource (self.datasource) if no data is given.
            Draws the data and sets the background if self.setbg = True
        """
        drawdata = self.makedrawdata(data,template) #this allows templating
        self.draw(drawdata, layer) 
        self.drawimage.save(self.dstimg)
        if self.setbg==True:
            os.popen("feh --bg-max " + self.dstimg)

    def rlookup(self, ip):
        """
            Simple reverse lookup of IP with caching, falls back to IP address
        """
        #Check our simple cache
        hname = self.rdnscache.get(ip)
        if not hname: #then look it up
            try:
                hname = socket.gethostbyaddr(ip)[0]
            except: #fall back to ip
                hname = ip
            #put it in the cache for later
            self.rdnscache[ip] = hname
        return hname
    
    def _uniqify(self,seq):
        """
            This function makes sure that dicts in a list are unique while preserving order
            The first occurrence will stick, feed a reverse list to make the last occurrence stick (then unreverse the output)
        """
        seen = {}
        result = []
        for item in seq:
            if hash(repr(item)) in seen: continue
            seen[hash(repr(item))] = 1
            result.append(item)
        return result


#

def main():
    ikna = Ikna(fontsize=20, yshift=125, datasource="firewall", showonlythelast=20)
    while True:
        ikna.update(template="$ip $port $proto $country_code")
        #a.update( data=[ { 'ip': '8.8.8.8' , 'someinfo': 'Google DNS server'} ])
        time.sleep(30)

if __name__ == "__main__":
    main()

