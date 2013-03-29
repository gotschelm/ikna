Ikna
====

Ikna is a simple python script for GNU/Linux that can plot IP addresses 
from netstat or your firewall log on a world map. 

This is a toy and a work in progress.


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
