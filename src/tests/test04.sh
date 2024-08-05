#!/bin/dash

# Written by ericdai

life=hamburger

for arg in "$@"
do
    for name in a b c d $life
    do
        if [ name = hamburger ]
        then
            echo I am happy
        fi
    done
done
