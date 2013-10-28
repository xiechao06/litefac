#! /bin/sh
# this script could be sudo
cat << "EOF" > /etc/uwsgi/apps-available/lite-mms.xml
<uwsgi>
   <uid>www-data</uid>
   <gid>www-data</gid>
   <socket>/tmp/lite-mms.sock</socket>
   <plugins>python</plugins>
</uwsgi>
EOF

ln -sf /etc/uwsgi/apps-available/lite-mms.xml /etc/uwsgi/apps-enabled/lite-mms.xml
