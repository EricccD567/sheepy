#!/usr/bin/python3

# Author: Eric Dai
# Date: 15/08/23
# Description: a basic Dash script to Python code transpiler


import keyword
import re
import sys

IMPORT_FNMATCH = 'import fnmatch'
IMPORT_GLOB = 'import glob'
IMPORT_OS = 'import os'
IMPORT_STAT = 'import stat'
IMPORT_SUBPROCESS = 'import subprocess'
IMPORT_SYS = 'import sys'

INDENT = '    '
SH_VAR = 'sh_var_'
SHEBANG_PY = '#!/usr/bin/python3 -u'
SHEBANG_SH = '#!/bin/dash'

PY_BUILTINS = (
    'abs', 'aiter', 'all', 'anext', 'any', 'ascii',
    'bin', 'bool', 'breakpoint', 'bytearray', 'bytes',
    'callable', 'chr', 'classmethod', 'compile', 'complex',
    'delattr', 'dict', 'dir', 'divmod',
    'enumerate', 'eval', 'exec',
    'filter', 'float', 'fnmatch', 'format', 'frozenset',
    'getattr', 'glob', 'globals',
    'hasattr', 'hash', 'help', 'hex',
    'id', 'input', 'int', 'isinstance', 'issubclass', 'iter',
    'len', 'list', 'locals',
    'map', 'max', 'memoryview', 'min',
    'next',
    'object', 'oct', 'open', 'ord', 'os',
    'pow', 'print', 'property',
    'range', 'repr', 'reversed', 'round',
    'set', 'setattr', 'slice', 'sorted', 'stat', 'staticmethod', 'str', 'sum', 'subprocess', 'super', 'sys',
    'tuple', 'type',
    'vars',
    'zip'
)


"""Return a variable name that is valid in Python 3

Convert a Dash Shell variable name to a valid Python 3 variable name
The Dash Shell variable name cannot be a Python 3 keyword, builtin function, or module
"""
def handle_var_keyword(var_name: str) -> str:
    if keyword.iskeyword(var_name) or var_name in PY_BUILTINS:
        var_name = f'{SH_VAR}{var_name}'
    return var_name


"""Return a transformed piece of code and is glob required

Expand all globs for a piece of code and then convert it to a string
"""
def handle_glob_to_string(code_sh: str) -> tuple[str, bool]:
    req_glob = False
    code_py = re.sub(r'(\S*[*?\[\]]\S*)', '{\' \'.join(sorted(glob.glob(\'\\1\')))}', code_sh)
    if code_py != code_sh:
        req_glob = True
    return code_py, req_glob

"""Return a transformed piece of code and is glob required

Expand all globs for a piece of code and then convert it to a string of a list
"""
def handle_glob_to_list(code_sh: str) -> tuple[str, bool]:
    req_glob = False
    code_py = re.sub(r'(\S*[*?\[\]]\S*)', 'sorted(glob.glob(\"\\1\"))', code_sh)
    if code_py != code_sh:
        req_glob = True
    return code_py, req_glob

"""Return a transformed piece of code and is sys required

Access all variables for a piece of code and then convert it to a string
"""
def handle_var_access_to_string(code_sh: str) -> tuple[str, bool]:
    req_sys = False

    # case: ${?[0-9]+}?
    new_code_sh = re.sub(r'\$\{?([0-9]+)\}?', '{sys.argv[\\1]}', code_sh)
    # case: ${?#}?
    new_code_sh = re.sub(r'\$\{?#\}?', '{len(sys.argv)-1}', new_code_sh)
    # case: "${?@}?"
    new_code_sh = re.sub(r'\"\$\{?@\}?\"', '{\' \'.join(sys.argv[1:])}', new_code_sh)
    # case: ${?@}?
    new_code_sh = re.sub(r'\$\{?@\}?', '{\' \'.join((\' \'.join(sys.argv[1:])).split())}', new_code_sh)

    if new_code_sh != code_sh:
        req_sys = True

    # case: ${?var}?
    code_py = re.sub(r'\$\{?([^${}\s]+)\}?', lambda var: f'{{{handle_var_keyword(var.group(1))}}}', new_code_sh)

    return code_py, req_sys

"""Return a transformed piece of code and is sys required

Access all variables for a piece of code and then convert it to a string of a list
"""
def handle_var_access_to_list(code_sh: str) -> tuple[str, bool]:
    if code_sh == '"$@"':
        return 'sys.argv[1:]', True

    if code_sh == '$@':
        return '(" ".join(sys.argv[1:])).split()', True

    req_sys = False

    # case: ${?[0-9]+}?
    new_code_sh = re.sub(r'\$\{?([0-9]+)\}?', '{sys.argv[\\1]}', code_sh)
    # case: ${?#}?
    new_code_sh = re.sub(r'\$\{?#\}?', '{len(sys.argv)-1}', new_code_sh)

    if new_code_sh != code_sh:
        req_sys = True

    # case: ${?var}?
    code_py = re.sub(r'\$\{?([^${}\s]+)\}?', lambda var: f'{{{handle_var_keyword(var.group(1))}}}', new_code_sh)
    code_py_lst = [f'f"{el}"' for el in code_py.split()]
    code_py = ', '.join(code_py_lst)
    cody_py = f'[{code_py}]'

    return cody_py, req_sys


"""Return a transformed conditional statement

Handle (almost) all possibilities of the test builtin command
"""
def handle_test(test: str) -> str:
    if not test:
        return test

    test = test.replace('(', '').replace(')', '')
    test_parts = test.split()

    if len(test_parts) == 1:
        return test

    # handle negation
    if test_parts[0] == '!':
        neg_expr = ' '.join(test_parts[1:])
        return f'not {handle_test(neg_expr)}'

    expr = ''
    if len(test_parts) == 2:
        if test_parts[0] == '-n':
            expr = f'f"{test_parts[1]}'
        elif test_parts[0] == '-z':
            expr = f'not f"{test_parts[1]}"'
        elif test_parts[0] == '-b':
            expr = f'os.access(f"{test_parts[1]}", os.F_OK) and stat.S_ISBLK(os.stat(f"{test_parts[1]}")[0])'
        elif test_parts[0] == '-c':
            expr = f'os.access(f"{test_parts[1]}", os.F_OK) and stat.S_ISCHR(os.stat(f"{test_parts[1]}")[0])'
        elif test_parts[0] == '-d':
            expr = f'os.path.isdir(f"{test_parts[1]}")'
        elif test_parts[0] == '-e':
            expr = f'os.access(f"{test_parts[1]}", os.F_OK)'
        elif test_parts[0] == '-f':
            expr = f'os.path.isfile(f"{test_parts[1]}")'
        elif test_parts[0] == '-g':
            pass
        elif test_parts[0] == '-G':
            pass
        elif test_parts[0] == '-h' or test_parts[0] == '-L':
            expr = f'os.path.islink(f"{test_parts[1]}")'
        elif test_parts[0] == '-k':
            pass
        elif test_parts[0] == '-N':
            expr = f'os.access(f"{test_parts[1]}", os.F_OK) and os.path.getmtime(f"{test_parts[1]}") > os.path.getatime(f"{test_parts[1]}")'
        elif test_parts[0] == '-O':
            pass
        elif test_parts[0] == '-p':
            expr = f'os.access(f"{test_parts[1]}", os.F_OK) and stat.S_ISFIFO(os.stat(f"{test_parts[1]}")[0])'
        elif test_parts[0] == '-r':
            expr = f'os.access(f"{test_parts[1]}", os.R_OK)'
        elif test_parts[0] == '-s':
            expr = f'os.access(f"{test_parts[1]}", os.F_OK) and os.path.getsize(f"{test_parts[1]}")'
        elif test_parts[0] == '-S':
            expr = f'os.access(f"{test_parts[1]}", os.F_OK) and stat.S_ISSOCK(os.stat(f"{test_parts[1]}")[0])'
        elif test_parts[0] == '-u':
            pass
        elif test_parts[0] == '-w':
            expr = f'os.access(f"{test_parts[1]}", os.W_OK)'
        elif test_parts[0] == '-x':
            expr = f'os.access(f"{test_parts[1]}", os.X_OK)'
    elif len(test_parts) == 3:
        if test_parts[1] == '=':
            expr = f'f"{test_parts[0]}" == f"{test_parts[2]}"'
        elif test_parts[1] == '!=':
            expr = f'f"{test_parts[0]}" != f"{test_parts[2]}"'
        elif test_parts[1] == '-eq':
            test_parts[0] = test_parts[0].replace('{', '').replace('}', '')
            test_parts[2] = test_parts[2].replace('{', '').replace('}', '')
            expr = f'{test_parts[0]} == {test_parts[2]}'
        elif test_parts[1] == '-ge':
            test_parts[0] = test_parts[0].replace('{', '').replace('}', '')
            test_parts[2] = test_parts[2].replace('{', '').replace('}', '')
            expr = f'{test_parts[0]} >= {test_parts[2]}'
        elif test_parts[1] == '-gt':
            test_parts[0] = test_parts[0].replace('{', '').replace('}', '')
            test_parts[2] = test_parts[2].replace('{', '').replace('}', '')
            expr = f'{test_parts[0]} > {test_parts[2]}'
        elif test_parts[1] == '-le':
            test_parts[0] = test_parts[0].replace('{', '').replace('}', '')
            test_parts[2] = test_parts[2].replace('{', '').replace('}', '')
            expr = f'{test_parts[0]} <= {test_parts[2]}'
        elif test_parts[1] == '-lt':
            test_parts[0] = test_parts[0].replace('{', '').replace('}', '')
            test_parts[2] = test_parts[2].replace('{', '').replace('}', '')
            expr = f'{test_parts[0]} < {test_parts[2]}'
        elif test_parts[1] == '-ne':
            test_parts[0] = test_parts[0].replace('{', '').replace('}', '')
            test_parts[2] = test_parts[2].replace('{', '').replace('}', '')
            expr = f'{test_parts[0]} != {test_parts[2]}'
        elif test_parts[1] == '-nt':
            expr = f'os.access(f"{test_parts[0]}", os.F_OK) and os.access(f"{test_parts[2]}", os.F_OK) and os.path.getmtime(f"{test_parts[0]}") > os.path.getmtime(f"{test_parts[2]}")'
        elif test_parts[1] == '-ot':
            expr = f'os.access(f"{test_parts[0]}", os.F_OK) and os.access(f"{test_parts[2]}", os.F_OK) and os.path.getmtime(f"{test_parts[0]}") < os.path.getmtime(f"{test_parts[2]}")'
    else:
        if '-a' in test_parts:
            idx = test_parts.index('-a')
            expr_1 = ' '.join(test_parts[:idx])
            expr_2 = ' '.join(test_parts[idx + 1:])
            expr = f'{handle_test(expr_1)} and {handle_test(expr_2)}'
        elif '-o' in test_parts:
            idx = test_parts.index('-o')
            expr_1 = ' '.join(test_parts[:idx])
            expr_2 = ' '.join(test_parts[idx + 1:])
            expr = f'{handle_test(expr_1)} or {handle_test(expr_2)}'
        elif '&&' in test_parts:
            idx = test_parts.index('&&')
            expr_1 = ' '.join(test_parts[:idx])
            expr_2 = ' '.join(test_parts[idx + 1:])
            expr = f'{handle_test(expr_1)} and {handle_test(expr_2)}'
        elif '||' in test_parts:
            idx = test_parts.index('||')
            expr_1 = ' '.join(test_parts[:idx])
            expr_2 = ' '.join(test_parts[idx + 1:])
            expr = f'{handle_test(expr_1)} or {handle_test(expr_2)}'

    return expr


"""Return a transformed piece of code and is sys required

Handle the cd builtin command using os.chdir()
"""
def handle_cd(code_sh: str) -> tuple[str, bool]:
    dir = re.search(r'^cd\s+(.+)$', code_sh).group(1)
    dir = dir.replace('\'', '').replace('\"', '')

    dir, req_sys = handle_var_access_to_string(dir)
    code_py = f'os.chdir(f"{dir}")'

    return code_py, req_sys

"""Return a transformed piece of code, is glob required, and is sys required

Handle the echo builtin command using print()
"""
def handle_echo(code_sh: str) -> tuple[str, bool, bool]:
    echo_val = re.search(r'^echo(.*)$', code_sh).group(1)
    echo_val = echo_val.replace('\'', '').replace('\"', '')

    print_val, req_glob = handle_glob_to_string(echo_val)
    print_val, req_sys = handle_var_access_to_string(print_val)
    print_val = ' '.join(print_val.split())
    code_py = f'print(f"{print_val}")'

    return code_py, req_glob, req_sys

"""Return a transformed piece of code

Handle the exit builtin command using sys.exit()
"""
def handle_exit(code_sh: str) -> str:
    find_exit_code = re.search(r'^exit\s+([0-9]+)$', code_sh)
    exit_code = find_exit_code.group(1) if find_exit_code else ''

    code_py = f'sys.exit({exit_code})'

    return code_py

"""Return a transformed piece of code

Handle the read builtin command using input()
"""
def handle_read(code_sh: str) -> str:
    read_var = re.search(r'^read\s+([a-zA-Z_][a-zA-Z_0-9]*)$', code_sh).group(1)

    input_var = handle_var_keyword(read_var)
    code_py = f'{input_var} = input()'

    return code_py

"""Return a transformed piece of code, is glob required, and is sys required

Handle a for loop conditional statement
"""
def handle_for(code_sh: str) -> tuple[str, bool, bool]:
    for_loop = re.search(r'^for\s+([a-zA-Z_][a-zA-Z_0-9]*)\s+in\s+(.+)$', code_sh)
    var = for_loop.group(1)
    lst_sh = for_loop.group(2)
    req_glob = False
    req_sys = False

    var = handle_var_keyword(var)
    if re.search(r'^(\S*[*?\[\]]\S*)$', lst_sh):
        lst_sh = lst_sh.replace('\'', '').replace('\"', '')
        lst_py, req_glob = handle_glob_to_list(lst_sh)
    else:
        lst_py, req_sys = handle_var_access_to_list(lst_sh)
    code_py = f'for {var} in {lst_py}:'

    return code_py, req_glob, req_sys

"""Return a transformed piece of code, is glob required, is os required, is stat required, and is sys required

Handle a while loop conditional statement from test
"""
def handle_while(code_sh: str) -> tuple[str, bool, bool, bool, bool]:
    find_test_1 = re.search(r'^while\s+test\s+(.+)$', code_sh)
    find_test_2 = re.search(r'^while\s+\[\s+(.+)\s+\]$', code_sh)
    if find_test_1:
        test = find_test_1.group(1)
    elif find_test_2:
        test = find_test_2.group(1)
    else:
        test = ''
    test = test.replace('\'', '').replace('\"', '')
    req_os = False
    req_stat = False

    test, req_glob = handle_glob_to_string(test)
    test, req_sys = handle_var_access_to_string(test)
    expr = handle_test(test)
    code_py = f'while {expr}:'

    if 'os.' in expr:
        req_os = True
    if 'stat.' in expr:
        req_stat = True

    return code_py, req_glob, req_os, req_stat, req_sys

"""Return a transformed piece of code, is glob required, is os required, is stat required, and is sys required

Handle an if or elif conditional statement from test
"""
def handle_if_elif(code_sh: str, code_start: str) -> tuple[str, bool, bool, bool, bool]:
    find_test_1 = re.search(r'^(if|elif)\s+test\s+(.+)$', code_sh)
    find_test_2 = re.search(r'^(if|elif)\s+\[\s+(.+)\s+\]$', code_sh)
    if find_test_1:
        test = find_test_1.group(2)
    elif find_test_2:
        test = find_test_2.group(2)
    else:
        test = ''
    test = test.replace('\'', '').replace('\"', '')
    req_os = False
    req_stat = False

    test, req_glob = handle_glob_to_string(test)
    test, req_sys = handle_var_access_to_string(test)
    expr = handle_test(test)
    code_py = f'{code_start} {expr}:'

    if 'os.' in expr:
        req_os = True
    if 'stat.' in expr:
        req_stat = True

    return code_py, req_glob, req_os, req_stat, req_sys

"""Return a transformed piece of code, is glob required, and is sys required

Handle a variable assignment to value
"""
def handle_var_assign(code_sh: str) -> tuple[str, bool, bool]:
    var_val = re.search(r'^([a-zA-Z_][a-zA-Z_0-9]*)=(.+)$', code_sh)
    var = var_val.group(1)
    val = var_val.group(2)
    val = val.replace('\'', '').replace('\"', '')

    var = handle_var_keyword(var)
    val, req_glob = handle_glob_to_string(val)
    val, req_sys = handle_var_access_to_string(val)
    code_py = f'{var} = f"{val}"'

    return code_py, req_glob, req_sys

"""Return a transformed piece of code, is glob required, and is sys required

Handle any external commands (not exit, read, cd, test, and echo) using subprocess.run()
"""
def handle_ext_cmd(code_sh: str) -> tuple[str, bool, bool]:
    code_sh = code_sh.replace('\'', '').replace('\"', '')

    code_py, req_glob = handle_glob_to_string(code_sh)
    code_py, req_sys = handle_var_access_to_list(code_py)
    code_py = f'subprocess.run({code_py})'

    return code_py, req_glob, req_sys


"""Return a piece of code and a comment

Separate a line into the code section and the comment section
"""
def separate_comment(line: str) -> tuple[str, str]:
    line = line.strip()

    code = line
    comment = ''

    find_comment = re.search(r'(^#.*$)|(^.*?)(\s#.*$)', line)

    if find_comment:
        if find_comment.group(1):
            code = ''
            comment = find_comment.group(1)
        else:
            code = find_comment.group(2).rstrip()
            comment = find_comment.group(3)

    return code, comment


"""Return a transformed line, an indent level, and a set of required imports

Convert a Dash Shell script line to a Python 3 script line
Track the indent level and any required imports
"""
def line_sh_to_line_py(line_sh: str, indent_count: int) -> tuple[str, int, set[str]]:
    code_sh, comment = separate_comment(line_sh)

    code_py = ''
    line_req_imports: set[str] = set()
    req_glob = False
    req_os = False
    req_stat = False
    req_sys = False

    code_start = re.search(r'^\S*', code_sh).group(0)

    if code_start == 'cd':
        line_req_imports.add(f'{IMPORT_OS}\n')
        code_py, req_sys = handle_cd(code_sh)
    elif code_start == 'echo':
        code_py, req_glob, req_sys = handle_echo(code_sh)
    elif code_start == 'exit':
        line_req_imports.add(f'{IMPORT_SYS}\n')
        code_py = handle_exit(code_sh)
    elif code_start == 'read':
        code_py = handle_read(code_sh)
    elif code_start == 'for':
        code_py, req_glob, req_sys = handle_for(code_sh)
    elif code_start == 'while':
        code_py, req_glob, req_os, req_stat, req_sys = handle_while(code_sh)
    elif code_start == 'do':
        indent_count += 1
    elif code_start == 'done':
        indent_count -= 1
    elif code_start == 'if':
        code_py, req_glob, req_os, req_stat, req_sys = handle_if_elif(code_sh, code_start)
    elif code_start == 'elif':
        indent_count -= 1
        code_py, req_glob, req_os, req_stat, req_sys = handle_if_elif(code_sh, code_start)
    elif code_start == 'else':
        indent_count -= 1
        code_py = 'else:'
    elif code_start == 'then':
        indent_count += 1
    elif code_start == 'fi':
        indent_count -= 1
    elif '=' in code_start:
        code_py, req_glob, req_sys = handle_var_assign(code_start)
    elif code_start:
        line_req_imports.add(f'{IMPORT_SUBPROCESS}\n')
        code_py, req_glob, req_sys = handle_ext_cmd(code_sh)

    line_py = f'{code_py}{comment}'

    if req_glob:
        line_req_imports.add(f'{IMPORT_GLOB}\n')
    if req_os:
        line_req_imports.add(f'{IMPORT_OS}\n')
    if req_stat:
        line_req_imports.add(f'{IMPORT_STAT}\n')
    if req_sys:
        line_req_imports.add(f'{IMPORT_SYS}\n')

    return line_py, indent_count, line_req_imports


"""Convert a Dash Shell script to a Python 3 script"""
def main() -> None:
    # check usage
    if len(sys.argv) != 2:
        sys.stderr.write(f'Usage: {sys.argv[0]} filename\n')
        sys.exit(2)

    # get all lines of the Dash Shell script
    filename = sys.argv[1]
    with open(filename) as file:
        lines_sh = file.readlines()

    # remove the Dash Shell shebang and all redundant whitespace at the start of the Dash Shell script
    if lines_sh[0].strip().replace(' ', '') == SHEBANG_SH:
        lines_sh.pop(0)
    while not lines_sh[0].strip():
        lines_sh.pop(0)

    # store all lines of the Python 3 script
    lines_py = [
        f'{SHEBANG_PY}\n',
        '\n'
    ]

    # store all required imports
    all_req_imports: set[str] = set()

    # track indent level
    indent_count: int = 0

    # convert the Dash Shell script to Python 3 line by line
    for line_sh in lines_sh:
        line_py, indent_count, line_req_imports = line_sh_to_line_py(line_sh, indent_count)
        if 'else:\n' in lines_py[-1]:
            indent_count += 1
        lines_py.append(f'{INDENT * indent_count}{line_py}\n')
        all_req_imports.update(line_req_imports)

    # add required imports to the Python 3 script
    if all_req_imports:
        all_req_imports_sorted: list[str] = sorted(all_req_imports)
        all_req_imports_sorted.append('\n')
        lines_py[2:2] = all_req_imports_sorted

    # print the Python 3 script
    for line_py in lines_py:
        print(line_py, end='')


if __name__ == '__main__':
    main()
