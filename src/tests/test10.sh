#!/bin/dash

# Written by ericdai

echo hello world
echo 42 is the meaning of life, the universe, and everything
echo To be or not to be: that is the question

echo Hello      World

echo

echo $0
echo ${0}

echo $#
echo ${#}

echo "$@"
echo "${@}"

echo $@
echo ${@}

a=hello
print=hi
echo $a
echo ${a}
echo $print

echo $a$a
echo $a${a}
echo ${a}$a
echo ${a}${a}

echo $a $a
echo $a ${a}
echo ${a} $a
echo ${a} ${a}
echo      ${a}         ${a}

echo asasas${0}asasas
echo asasas${#}asasas
echo asasas"${@}"asasas
echo asasas${@}asasas
echo asasas${a}asasas

echo ${a}asasas$0
echo ${@}asasas$a
echo "${@}"asasas$@
echo ${@}asasas"$@"
echo     "$@"   asasas    $@
echo     $@   asasas    "$@"

for el in "$@"; do
    echo "$el"
done

for el in $@; do
    echo "$el"
done

if [ '' ]; then
    echo 'hi'
fi
