# Copyright (c) 2009-2010, Michael Gorven, Stefano Rivera, Jonathan Hitchcock
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

from __future__ import division
import logging
from os import kill
from random import random, randint
from signal import SIGTERM
from subprocess import Popen, PIPE
from time import time, sleep

from ibid.compat import all, factorial
from ibid.config import Option, FloatOption
from ibid.plugins import Processor, match
from ibid.utils import file_in_path, unicode_output

try:
    from ast import NodeTransformer, Pow, Name, Load, Call, copy_location, parse
    transform_method='ast'

except ImportError:
    from compiler import ast, pycodegen, parse, misc, walk
    transform_method='compiler'
    class NodeTransformer(object):
        pass
    # ExpressionCodeGenerator doesn't inherit __futures__ from calling module:
    class FD_ExpressionCodeGenerator(pycodegen.ExpressionCodeGenerator):
        futures = ('division',)

features = {}
log = logging.getLogger('calc')

features['bc'] = {
    'description': u'Calculate mathematical expressions using bc',
    'categories': ('calculate',),
}
class BC(Processor):
    usage = u'bc <expression>'

    features = ('bc',)

    bc = Option('bc', 'Path to bc executable', 'bc')
    bc_timeout = FloatOption('bc_timeout', 'Maximum BC execution time (sec)', 2.0)

    def setup(self):
        if not file_in_path(self.bc):
            raise Exception("Cannot locate bc executable")

    @match(r'^bc\s+(.+)$')
    def calculate(self, event, expression):
        bc = Popen([self.bc, '-l'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        start_time = time()
        bc.stdin.write(expression.encode('utf-8') + '\n')
        bc.stdin.close()

        while bc.poll() is None and time() - start_time < self.bc_timeout:
            sleep(0.1)

        if bc.poll() is None:
            kill(bc.pid, SIGTERM)
            event.addresponse(u'Sorry, that took too long. I stopped waiting')
            return

        output = bc.stdout.read()
        error = bc.stderr.read()

        code = bc.wait()

        if code == 0:
            if output:
                output = unicode_output(output.strip())
                output = output.replace('\\\n', '')
                event.addresponse(output)
            else:
                error = unicode_output(error.strip())
                error = error.split(":", 1)[1].strip()
                error = error[0].lower() + error[1:].split('\n')[0]
                event.addresponse(u"I'm sorry, I couldn't deal with the %s", error)
        else:
            event.addresponse(u"Error running bc")
            error = unicode_output(error.strip())
            raise Exception("BC Error: %s" % error)

features['calc'] = {
    'description': u'Returns the anwser to mathematical expressions. '
                   u'Uses Python syntax and semantics (i.e. radians)',
    'categories': ('calculate',),
}
class LimitException(Exception):
    pass

class AccessException(Exception):
    pass

def limited_pow(*args):
    "We don't want users to DOS the bot. Pow is the most dangerous function. Limit it"

    # Large modulo-powers are ok, but otherwise we don't want enormous operands
    if (all(isinstance(arg, (int, long)) for arg in args)
            and not (len(args) == 3 and args[2] < 1e100)):
        try:
            answer = pow(float(args[0]), float(args[1]))
            if answer > 1e+300:
                raise LimitException

        except OverflowError, e:
            raise LimitException(e)

    return pow(*args)

def limited_factorial(x):
    if x >= 500:
        raise LimitException
    return factorial(x)

# ast method
class PowSubstitutionTransformer(NodeTransformer):
    def visit_BinOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, Pow):
            fnode = Name('pow', Load())
            copy_location(fnode, node)
            cnode = Call(fnode, [node.left, node.right], [], None, None)
            copy_location(cnode, node)
            return cnode
        return node
    def visit_Attribute(self, node):
        raise AccessException

# compiler method
class PowSubstitutionWalker(object):
    def visitPower(self, node, *args):
        walk(node.left, self)
        walk(node.right, self)
        cnode = ast.CallFunc(ast.Name('pow'), [node.left, node.right], None, None)
        node.left = cnode
        # Little hack: instead of trying to turn node into a CallFunc, we just do pow(left, right)**1
        node.right = ast.Const(1)
    def visitGetattr(self, node, *args):
        raise AccessException

class Calc(Processor):
    usage = u'<expression>'
    features = ('calc',)

    priority = 500

    extras = ('abs', 'round', 'min', 'max')
    banned = ('for', 'yield', 'lambda', '__', 'is')

    # Create a safe dict to pass to eval() as locals
    safe = {}
    exec('from math import *', safe)
    del safe['__builtins__']
    for function in extras:
        safe[function] = eval(function)
    safe['pow'] = limited_pow
    safe['factorial'] = limited_factorial

    @match(r'^(.+)$')
    def calculate(self, event, expression):
        for term in self.banned:
            if term in expression:
                return

        try:
            # We need to remove all power operators and replace with our limited pow
            # ast is the new method (Python >=2.6) compiler is the old
            ast = parse(expression, mode='eval')
            if transform_method == 'ast':
                ast = PowSubstitutionTransformer().visit(ast)
                code = compile(ast, '<string>', 'eval')
            else:
                misc.set_filename('<string>', ast)
                walk(ast, PowSubstitutionWalker())
                code = FD_ExpressionCodeGenerator(ast).getCode()

            result = eval(code, {'__builtins__': None}, self.safe)

        except ZeroDivisionError, e:
            event.addresponse(u"I can't divide by zero.")
            return
        except ArithmeticError, e:
            event.addresponse(u"I can't do that: %s", unicode(e))
            return
        except ValueError, e:
            if unicode(e) == u"math domain error":
                event.addresponse(u"I can't do that: %s", unicode(e))
            return
        except LimitException, e:
            event.addresponse(u"I'm afraid I'm not allowed to play with big numbers")
            return
        except Exception, e:
            return

        if isinstance(result, (int, long, float, complex)):
            event.addresponse(unicode(result))


class ExplicitCalc(Calc):
    usage = u'calc <expression>'
    priority = 0

    @match(r'^calc(?:ulate)?\s+(.+)$')
    def calculate(self, event, expression):
        super(ExplicitCalc, self).calculate(event, expression)


features['random'] = {
    'description': u'Generates random numbers.',
    'categories': ('calculate', 'fun',),
}
class Random(Processor):
    usage = u'random [ <max> | <min> <max> ]'
    features = ('random',)

    @match(r'^rand(?:om)?(?:\s+(\d+)(?:\s+(\d+))?)?$')
    def random(self, event, begin, end):
        if not begin and not end:
            event.addresponse(u'I always liked %f', random())
        else:
            begin = int(begin)
            end = end and int(end) or 0
            event.addresponse(u'I always liked %i', randint(min(begin,end), max(begin,end)))

# vi: set et sta sw=4 ts=4:
