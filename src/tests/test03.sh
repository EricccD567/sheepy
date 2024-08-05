#!/bin/dash

# Written by ericdai

for file in *
do
    if [ -d $file ]
    then
        echo it is a dir
    elif [ -f $file ]
    then
        echo it is a reg file
    else
        echo i am sad
    fi
done
