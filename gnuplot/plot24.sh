#!/bin/bash
machine=$(hostname)
duration="day"

pastyear=$(date --date='24 hours ago' +%Y)
pastmonth=$(date --date='24 hours ago' +%m)
pastday=$(date --date='24 hours ago' +%d)
pasthour=$(date --date='24 hours ago' +%H)

yeartoday=$(date +%Y)
monthtoday=$(date +%m)
daytoday=$(date +%d)
hourtoday=$(date +%H)

tempcol=3
humicol=5

if [ "$1" = "dht" ]; then
  tempcol=4
  humicol=5
fi

if [ "$1" = "sht" ]; then
  tempcol=6
  humicol=7
fi

if [ "$1" = "bme" ]; then
  tempcol=3
  humicol=4
fi

cp /opt/measurements/readings_log.txt /opt/measurements/temp.txt

sed -i -e 's/  / X /g' /opt/measurements/temp.txt

sed -i -e 's/  / X /g' /opt/measurements/temp.txt

sed -i -e 's/  / X /g' /opt/measurements/temp.txt

gnuplot <<-EOFMarker
set term x11 persist
set xdata time
set timefmt "%Y-%m-%d %H:%M:%S"
set format x "%d.%m %H:%M"
set xrange ["$pastyear-$pastmonth-$pastday $pasthour:00:00":"$yeartoday-$monthtoday-$daytoday $hourtoday:00:00"]
set yrange [16:26]
set y2range [0.1:100]
set key font ",20"
#set log y2
set grid x y
set xlabel "Time" font ",20"
set ylabel "Deg C" font ",20"
set y2label "% RH" font ",20"
set ytics nomirror
set xtics font ",20"
set ytics font ",20"
set y2tics font ",20"
set mytics 5
set tics out
set title "Status of $machine - past $duration" font ",20"
#set autoscale y
#set autoscale y2
plot "/opt/measurements/temp.txt" using 1:$tempcol title "Temperature" w l lt rgb "red"  lw 3, "/opt/measurements/temp.txt" using 1:$humicol title "% Relative Humidity" w l lt rgb "blue"  lw 3 axes x1y2
EOFMarker

rm /opt/measurements/temp.txt
