#!/bin/bash

#kinda config
home=/home/bash/pla2test
if [ -f /var/log/mail.info ]; then fn=/var/log/mail.info; else fn=/var/log/maillog; fi;

#get file identifier
gfi () {
  if [ `head -10 $1|wc -l` == 10 ]; then
    head -10 $1|md5sum|awk '{print $1}'
  fi;
}

#determine id
fi=`gfi $fn`;
date=`date -u +%Y%m%d%H%M%S`;
if [ -z $fi ]; then
        echo File too small 
        exit 1;
fi;

#analyze
/usr/local/bin/pypy ${0%/*}/analyze.py $fn $fi > $home/tmpr.result

#determine id once more
fi2=`gfi $fn`;
if [ $fi2 != $fi ]; then
	echo file rewritten while proceessed
	exit 2;
fi;

#calculate the new file name
if [ -f $home/*-$fi.result ]; then 
  nfn=$home/*-$fi.result;
else
  nfn=$home/$date-$fi.result;
fi;

#move
mv $home/tmpr.result $nfn;

#aggregate with previous results
cat $home/*-*.result|awk '{d[$1 " " $2]+=$3}END{for (i in d){print i " " d[i]}}' > $home/final.result
