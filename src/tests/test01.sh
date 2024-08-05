#!/bin/dash

# From COMP2041 -> topic -> shell -> code -> accessing_args.sh
# Written by andrewt@unsw.edu.au

for a in $@
do
    echo $a
done

for a in "$@"
do
    echo $a
done
