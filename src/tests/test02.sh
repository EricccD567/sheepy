#!/bin/dash

# From COMP2041 -> topic -> shell -> code -> seq.v1.sh
# Written by andrewt@unsw.edu.au

input=$1

if test $input -eq 1
then
    echo 1 + 1 = 2
elif test $input -gt 3
then
    echo opps too large
else
    echo Usage: $0 int
    exit 1
fi
