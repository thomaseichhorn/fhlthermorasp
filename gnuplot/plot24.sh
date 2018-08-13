#!/bin/bash
machine=$(hostname)

yeartoday=$(date +%Y)
monthtoday=$(date +%m)
daytoday=$(date +%d)
hourtoday=$(date +%H)

pastyear=$(date --date='24 hours ago' +%Y)
pastmonth=$(date --date='24 hours ago' +%m)
pastday=$(date --date='24 hours ago' +%d)
pasthour=$(date --date='24 hours ago' +%H)
echo $yeartoday $monthtoday $daytoday $hourtoday
echo $pastyear $pastmonth $pastday $pasthour
gnuplot <<-EOFMarker
set term x11 persist
set xdata time
set timefmt "%Y-%m-%d %H:%M:%S"
set format x "%d.%m %H:%M"
set xrange ["$pastyear-$pastmonth-$pastday $pasthour:00:00":"$yeartoday-$monthtoday-$daytoday $hourtoday:00:00"]
set yrange [18:24]
set y2range [0.1:50]
set log y2
set grid x y
set xlabel "Time"
set ylabel "Deg C"
set y2label "% RH"
set ytics nomirror
set y2tics
set mytics 0.5
set tics out
set title "Status of $machine - past day"
#set autoscale y
#set autoscale y2
plot "/opt/measurements/readings_log.txt" using 1:3 title "Temperature" w p, "/opt/measurements/readings_log.txt" using 1:4 title "% Relative Humidity" w p axes x1y2
EOFMarker
echo "test"
