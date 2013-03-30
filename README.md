Ikna
====

Ikna is a simple python script for GNU/Linux that can plot IP addresses 
from netstat or your firewall log on a world map. 

This is a toy and a work in progress. See this readme and ikna.py for help.


Some features
--------------
* Mercator or equirectangular map projection

* Templating (eg "$ip $country_code" -> "8.8.8.8 US" )

* Automatically sets background (using feh)

* Simple color coding


Dependencies
------------

pygeoip  
https://pypi.python.org/pypi/pygeoip/

GeoIP database: Maxmind GeoLite City  
http://geolite.maxmind.com/download/geoip/database/GeoLiteCity.dat.gz  
Extract to /usr/share/GeoIP/GeoLiteCity.dat  

feh   
Needed for automatically setting background  
http://feh.finalrewind.org/  


Examples/Howto
==============

Explanation of init variables
-----------------------------

**srcimg**  
path to your world map image  
**dstimg**  
path to your desired output image, defaults to /run/shm/ikna.png  
**geoipdb**  
location of your GeoIP database, "/usr/share/GeoIP/GeoLiteCity.dat" is the default  
**font**  
path to your truetype font of choice  
**width**  
width of your image, this is set automatically but you can override it with this variable  
**height**  
height of your image, this is set automatically but you can override it with this variable  
**radius**  
the radius in pixels of the dot that is drawn  
**fontsize**  
size of the font used in the labels  
**projection**  
"mercator" or "equirectangular"  
**xshift**  
After projection is calculated, this value is added to the X part of the coordinate, use this when your map isn't properly aligned  
**yshift**  
After projection is calculated, this value is added to the Y part of the coordinate, use this when your map isn't properly aligned  
**datasource**  
"netstat" or "firewall", make sure your /var/log/messages is readable  
**statefilter**  
only applicable when datasource="netstat", this does a simple grep on the netstat output, set it to "ESTABLISHED" to only plot established connections. see man netstat  
**fwlog**  
path to your firewall log, default is /var/log/messages  
**template**  
the default template to use, defaults to "$ip"  
**layer**  
not used yet  
**showonlythelast**  
show only the last x items  
**setbg**  
True or False. the background will be set with 'feh' if this is set to True  



Template variables
------------------

The following template variables are available when using datasource="netstat" or "firewall"  
    $ip  
    $port  
    $proto    #only available when datasource="firewall"  

Template variables from pygeoip will automatically become available to you:
see https://pypi.python.org/pypi/pygeoip/  

    $city  
    $region_name  
    $area_code  
    $longitude  
    $country_code3  
    $latitude  
    $postal_code  
    $dma_code  
    $country_code  
    $country_name  
    $continent  
  
 

Example 1
---------

    ikna = Ikna(fontsize=20, srcimg="/home/user/map.jpg", projection="equirectangular", datasource="netstat", statefilter="ESTABLISHED", template="$ip $country_code")  
    ikna.update()


Example 2
---------
    ikna = Ikna(srcimg="/tmp/map.jpg", datasource="firewall", fwlog="/var/log/iptables", radius=60, template="$ip $proto $port $city", showonlythelast=30)  
    ikna.update()

Example 3: custom data
----------------------

Custom data should be a list of dicts, for example:  
    [ { 'ip': '1.2.3.4'}, { 'ip': '8.8.8.8' }, ... ]
Each dict must have an 'ip' key, and may have any other keys you like, for example:  
    [ { 'ip': '12.23.45.67', 'myinfo': 'This is my fileserver' }, ... ]
All keys you specify in your dict will automatically become template variables.   
In addition, all the pygeoip template variables listed above will be available to you.   
In case of conflict, pygeoip variables will win over your custom dict keys  

    mydata = [ {'ip': '8.8.8.8' , 'someinfo': 'Google DNS server'},
               {'ip': '4.2.2.1' , 'someinfo': 'OpenDNS DNS server'} ]

    ikna = Ikna(srcimg="/tmp/map.png")
    ikna.update(data=mydata, template="$ip $someinfo $country_code" )
