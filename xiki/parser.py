import json, re, logging
from .util import unindent, indent

log = logging.getLogger('xiki.parser')

WHITESPACE = re.compile(r'\s+')
HANGING    = re.compile(r'(?m)\S.*\n([\x20\t]+\S.*\n|[\x20\t]*\n)*')
KEY        = re.compile(r':?([^:]+):((?=\n)|[\x20\t]+)')

try:
    unicode('')
except:
    unicode = str


def is_list(s):
    from .path import BULLET_RE
    return BULLET_RE.match(s)


def is_dictionary(s):
    return KEY.match(s)


def syntax_error(message, lineno=None, filename=None):
    e = SyntaxError(message)
    e.lineno = lineno
    e.filename = filename
    return e


def whitespace(s, lineno):
    log.debug("s: %s", s)
    m = WHITESPACE.match(s)
    if m:
        lineno = m.group(0).count("\n")+1
        s = s[m.end():]
    return s, lineno


def parse(input, lineno=1, filename=None):
    '''Get a data tree out of s.

    Examples::

        foo: bar
        key: value
            and more data
        list:
            - first
            - "second"
            - third: true
              forth: 1

    | foo: bar
    | key: value
    |   and more data

    :foo: bar
    :key: value
        and more data
    '''

    s = input
    log.debug("parse s: %s", s)

    # remove "| " if present
    if s.startswith('| '):
        s = ''.join([ l[2:] for l in s.splitlines(1) ])

    # JSON is fine
    try:
        return json.loads(s)
    except:
        pass

    # skip whitespace
    s, lineno = whitespace(s, lineno)

    log.debug("lineno: %s, s: %s", lineno, s)

    result = s

    # parse list
    if is_list(s):
        log.debug("is_list!")
#       unindent(s[2:], hang=True)
        result = []

        while s:
            s, lineno = whitespace(s, lineno)

            if not s:
                return result

            m = HANGING.match(s)
            if not m:
                raise syntax_error("unexpected end of file: %s" % s, lineno=lineno)

            current, s = s[:m.end()], s[m.end():]
            log.debug('current: %s, s: %s', current, s)

            current = current[1:]
            if current[0] in "\x20\t":
                current = current[1:]

            if current[0] == "\n":
                lineno += 1

            result.append(parse(unindent(current, hang=True), lineno=lineno))
            lineno += current.count("\n")
            log.debug("result: %s", result)

    # parse dictionary
    if is_dictionary(s):
        log.debug("is_dict!")
        result = {}

        while s:
            s, lineno = whitespace(s, lineno)

            if not s:
                return result

            m = HANGING.match(s)
            if not m:
                raise syntax_error("unexpected end of file: %s" % s.split("\n", 1)[0], lineno=lineno)

            current, s = s[:m.end()], s[m.end():]
            log.debug('current: %s, s: %s', current, s)

            m = KEY.match(current)
            if not m:
                raise syntax_error("key expected: %s" % s.split("\n", 1)[0], lineno=lineno)

            key = m.group(1).strip()
            log.debug("key: %s", key)
            if current[m.end()] == "\n":
                lineno += 1
            value = parse(unindent(current[m.end():], hang=True), lineno=lineno)
            log.debug("value: %s", value)

            result[key] = value

    if isinstance(result, bytes):
        result = result.decode('utf-8')

    # else we keep this string
    if isinstance(result, unicode):
        if result.count("\n") == 1:
            return result.strip()

    return result

def assemble(data):
#    import spdb ; spdb.start()
    output = ""
    import types
    if isinstance(data, dict):
        # align keys
        out_data = []
        max_len  = 0
        MAX_LEN  = 25
        for k,v in sorted(data.items()):
            v = assemble(v)
            k_len = len(k)
            if k_len < MAX_LEN and k_len > max_len:
                max_len = k_len
            out_data.append((k_len, k,v))

        for k_len, k,v in out_data:
            if k_len < MAX_LEN:
                output += ("%s:" % k).ljust(k_len)
            else:
                output += "%s:"

            if k_len >= MAX_LEN or "\n" in v:
                output += "\n"+indent(v, 4)
            else:
                output += v+"\n"

    elif isinstance(data, str):
        if data:
            if data[0].isspace():
                return json.dumps(data)
            elif "\n" in data:
                if not data.endswith("\n"):
                    return json.dumps(data)
            return data
    elif data is None or isinstance(data, (int, float)):
        return json.dumps(data)

    else:
        for d in data:
            r = indent(assemble(d), 2, True)
            if not r.endswith("\n"):
                r += "\n"
            output += '- '+r

    return output