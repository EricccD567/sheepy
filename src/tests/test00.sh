#!/bin/dash

# From COMP2041 -> topic -> shell -> code -> args.sh
# Written by andrewt@unsw.edu.au

echo My name is $0
echo I have $# arguments

echo My arguments as not quoted are $@

echo My 5th argument is $5
echo My 10th argument is ${10}
echo My 255th argument is ${255}
