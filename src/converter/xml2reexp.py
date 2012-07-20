# -*- coding: UTF-8 -*-
import lxml.etree as ET
import sys
import os
import codecs
import copy

did_you_mean = False
number = 0
amount = 0
to_implement = 0
no_support = 0


class RuleModel(object):
    '''parse() method returns rule'''
    def __init__(self, rule):
        self.rule = rule
        self.pattern = rule.find('pattern')
        self.pattern_descendants = RuleModel.element_descendants(self.pattern)
        self.message = rule.find('message')
        self.message_descendants = RuleModel.element_descendants(self.message)
        self.items = RuleModel.nesting_list_killer(
                    [i.items() for i in self.message.iterdescendants()]
                    + [i.items() for i in self.pattern.iterdescendants()])
        self.keys = RuleModel.nesting_list_killer(
                    [i.keys() for i in self.message.iterdescendants()]
                    + [i.keys() for i in self.pattern.iterdescendants()])

    @staticmethod
    def nesting_list_killer(lst):
        result = []
        for element in lst:
            if isinstance(element, (str, unicode, tuple)):
                result.append(element)
            else:
                result += RuleModel.nesting_list_killer(element)
        return set(result)

    @staticmethod
    def key_remover(iterable, keys_list):
        keys = copy.copy(keys_list)
        it = list(copy.copy(iterable))
        for key in keys:
            try:
                it.remove(key)
            except ValueError:
                pass
        return it

    @staticmethod
    def space_killer(old_result):
        '''space killer, char dealer'''
        result = [i.strip() for i in old_result[1:]]

        for item in result:
            if (item in ('.', ',', ':', '!', '?', "'", '"', '([.])')
                and item in result
                or item.startswith('\\n')
                ):
                indx = result.index(item)
                if indx != 0:
                    result[indx - 1] += item
                    result.remove(item)
                else:
                    result = [(item + result[:][1]), ] + result[2:]

        for item in result:
            if '\\n' in item:
                result[result.index(item)] = '\\n'.join(i.strip()
                                                    for i in item.split('\\n'))

            if item.startswith('([.])') or item.endswith('([.]))'):
                indx = result.index(item)
                if indx != 0:
                    result[indx - 1] += item
                    result.remove(item)

        for item in result:
            if item.endswith('([.]))'):
                indx = result.index(item)
                if indx != 0:
                    result[indx - 1] += item
                    result.remove(item)
#            if '|' in item:
#                result[result.index(item)] = '\\n'.join(i.strip()
#                                                    for i in item.split('|'))

        for item in result:
            if item.endswith("'") and (len(result) - result.index(item) >= 2):
                indx = result.index(item)
                result[indx] += result[indx + 1]
                result.remove(result[indx + 1])

        result.insert(0, old_result[0])
        return result

    @staticmethod
    def element_descendants(element):
        return ((i, i.tag, tuple(i.keys()), i.getchildren(), i.text, i.tail)
                                            for i in element.iterdescendants())

    def parse(self, attr):
        result = []
        suggestions = []

        if attr == 'pattern':
            target = self.pattern_descendants
        elif attr == 'message':
            target = self.message_descendants
        else:
            raise AttributeError("wrong attr for parse()'s target ")

        for (element, tag, keys, _children, text,
                                            tail) in target:
# start for #
            '''unsupported pattern keys'''
            if (self.keys
                and 'postag' in self.keys
                or 'postag_regexp' in self.keys
                or 'negate_pos' in self.keys
                ):
                if ('postag', 'SENT_START') in self.items:
                    r = copy.copy(self.items)
                    r.remove(('postag', 'SENT_START'))
                    r = [i[0] for i in RuleModel.nesting_list_killer(r)]
                    if ('postag' in r
                        or 'postag_regexp' in r
                        or 'negate_pos' in r):
                        result = [[], 'Not supported', ]
                        return result
                    else:
                        pass
                else:
                    result = [[], 'Not supported', ]
                    return result

            '''not implemented features'''
            if (self.keys
                and 'regexp_match' in self.keys
                or 'regexp_replace' in self.keys
                or 'regexp_replace' in self.keys
                or 'case_conversion' in self.keys
#                or tag == 'match'
#                or 'skip' in self.keys
#                or 'negate' in keys
#                or 'spacebefore' in keys
#                or 'inflected' in keys
#                or tag == 'exception'
                or ('postag', 'SENT_START') in self.items
                ):
                if not 'Not supported' in result:
                    result = [[], 'Not implemented', ]
                    return result

            if not len(result):
                result.append(element.items())
            else:
                result[0] += element.items()

            #exception tag with scope attr rule
            if (tag == 'exception' and 'scope' in keys
                and not RuleModel.key_remover(keys, ['scope', ])):
                ''' exception tag with only the scope key'''
                if element.get('scope') == 'previous':
                    result.append('(?<!%s)' % text)
                if element.get('scope') == 'next':
                    result.append('(?!%s)' % text)
                if element.get('scope') == "current":
                    result.append('(?=%s)' % text)
                if tail is not None:
                    result[-1] += ' (%s)' % tail

            # regexp attr rule
            if ('regexp' in keys
                and not RuleModel.key_remover(keys, ['regexp',
                                                     'inflected',
                                                     'skip'
                                                     ])
                and not element.getparent() == 'marker'):
                '''elements with only the regexp attr'''
                if text and text.strip():
                    result.append('(%s)' % text.strip())

            # token tag rule
            if tag == 'token':
                if not RuleModel.key_remover(keys, ['inflected',
                                                    'skip'
                                                    ]):
                    '''common tokens with no attrs'''
                    if text and text.strip():
                        if text is not '.':
                            result.append('(%s)' % text.rstrip())
                        else:
                            result.append('([.])')
                    else:
                        if not element.getchildren():
                            result.append('()')

            # marked tag rules
            if (element.tag == 'marker' and not element.getchildren()):
                '''markers without children -> error'''
                raise TypeError("'markered' elements in %s"
                                    % self.rule.get('id'))
            if element.getparent().tag == 'marker':
                children_list = element.getparent().getchildren()
                if len(children_list) == 1:
                    pass
                    #result[-1] = '(' + result[-1] + ')'
                else:
                    if children_list[0] == element:
                        if "regexp" not in element.keys():
                            if result[-1][0] != '(':
                                result[-1] = '((' + result[-1] + ')'
                            else:
                                result[-1] = '(' + result[-1]
                    elif len(result) > 2:
                        if (element in children_list[1:-1]
                              and "regexp" not in element.keys()):
                            if not result[-1][0] == '(':
                                result[-1] = '(' + result[-1] + ')'

                        elif children_list[-1] == element:
                            """ ')' after last element"""
                            if result[-1][0] != '(':
                                result[-1] = '(' + result[-1] + '))'
                            elif result[-1][0] == '(':
                                result[-1] += ')'

            #negate attr rule
            if (('negate', 'yes') in element.items()
                and not RuleModel.key_remover(keys, ['regexp',
                                                     'default',
                                                     'skip',
                                                     'negate'])):
                '''negate="yes" attribute'''
                if not RuleModel.key_remover([i for i in text],
                                        ('.', ',', ':', '!', '?', "'", '"',)):
                    result.append('([^%s])' % text)
                elif 'regexp' in keys:
                    result.append('(^(%s))' % text)
                else:
                    result.append('(^%s)' % text)

            #spacebefore attr rule
            if ('spacebefore' in keys
                and not RuleModel.key_remover(keys, ['default',
                                                     'spacebefore',
                                                     'skip',
                                                     'inflected'])):
                if text and text.strip():
                    if not self.pattern.getchildren()[0] == element:
                        if element.get('spacebefore') == 'no':
                            result[-1] += text.strip()
                        else:
                            result[-1] = result[-1] + ' ' + text.strip()
                    else:
                        if element.get('spacebefore') == 'no':
                            result.append('(w*)%s' % text.strip())
                        else:
                            result.append('(w*) %s' % text.strip())
            #spacebefore + regexp attr rule
            if ('spacebefore' in keys
                and 'regexp' in keys
                and not RuleModel.key_remover(keys, ['default',
                                                     'spacebefore',
                                                     'regexp',
                                                     'skip',
                                                     'inflected'])):
                if text and text.strip():
                    if not self.pattern.getchildren()[0] == element:
                        if element.get('spacebefore') == 'no':
                            result[-1] = ('(%s%s)'
                                          % (result[-1].translate(None, '()'),
                                             text.strip()))
                        else:
                            result[-1] = ('(%s %s)'
                                          % (result[-1].translate(None, '()'),
                                             text.strip()))
                    else:
                        if element.get('spacebefore') == 'no':
                            result.append('()%s' % text.strip())
                        else:
                            result.append('(() %s)' % text.strip())
            # skip attr rule
            if 'skip' in keys:
                if element.get('skip') == '-1':
                    result.append('(\w+ )*')
                else:
                    result.append('(\w+ ){0,%d}' % int(element.get('skip')))

            # rules for message
            # suggestion tag with no attrs or suggestion match tag with 1 attr
            if tag == 'suggestion' and not RuleModel.key_remover(keys, 'no'):
                if text and text.strip() and not keys:
                    '''message suggestions appearance'''
                    if [item.startswith('=') for item in result[1:]]:
                        result.append('\\n%s' % text.strip())
                        suggestions.append('%s' % text.strip())
                    else:
                        result.append('%s' % text.strip())
                        suggestions.append('%s' % text.strip())

                # suggestion match rules
                for el in element.getchildren():
                    if el.tag == "match":
                        match_no = int(el.get('no'))
#                       match_el = self.pattern.getchildren()[match_no- 1]
#                       print 'ZZZ', match_el.text
                        result.append('\\%s' % (match_no))
                        suggestions.append('\\%s' % (match_no))
                        if el.tail and el.tail.strip():
                            result.append('%s' % el.tail.strip())
                            suggestions.append('%s' % el.tail.strip())
                if tail and tail.strip():
                    suggestions.append(tail.strip())

# end for #
        if attr == 'message':
            if self.message.getchildren() and not result:
                '''in case of empty message'''
                raise TypeError('empty message!')

            '''message verbosity'''
            global did_you_mean
            if did_you_mean:
                result.append('#Did you mean?')
            else:
                result.append('#%s' % self.message.text.strip())
                if self.message.tail and self.message.tail.strip():
                    result.append('%s' % self.message.tail.strip())

                if suggestions is not None:
                    for suggestion in suggestions:
                        if suggestion is not None:
                            result.append('%s' % suggestion)

        result = RuleModel.space_killer(result)
        return result


class RuleView(object):
    '''adaptes rule's API, printer() method prints rule'''
    def __init__(self, rule, category):
        self.parse_pattern = RuleModel(rule).parse('pattern')
        self.pref = self.parse_pattern[0]
        self.pattern = self.parse_pattern[1:]
        self.parse_message = RuleModel(rule).parse('message')
        self.ix = self.parse_message[0]
        self.message = self.parse_message[1:]
        self.prefix = list(self.pref) + list(self.ix)
        self.id = rule.get('id')[0:15] if rule.get('id') else 'Unknown'
        self.rule = rule
        self.category = category
        self.supported_keys = ['regexp', 'scope', 'spacebefore', 'negate']
        self.key_to_print = None
        self.keys = RuleModel.nesting_list_killer([i.keys()
                                        for i in self.rule.iterdescendants()])

    @staticmethod
    def aggregate(iter1, iter2):
        set1 = set(iter1)
        set2 = set(iter2)
        aggregate = set1 & set2
        return list(aggregate)

    def sys_argv(self):
        supported_args = {'-short': 'Print \"Did you mean?\". '
                                        'Default: Print full message',
                          '-file': 'Dump rules to \'rules.txt\' file',
                          '-attr': 'Print <rule> tags\'s attr list '
                          'before rule if any',
                          '-show=attr': 'Incompatible with other '
                          ' keys except maybe -short :)'}
        if len(sys.argv) > 1:
            if '-short' in sys.argv:
                global did_you_mean
                did_you_mean = True
            if '-file' in sys.argv:
                sys.stdout = codecs.open('rules.txt',
                                         encoding='utf-8', mode='a+')
            if '-attr' in sys.argv:
                if self.prefix:
                    print sorted(list(set(self.prefix))), '=>',

            show_attr = [i for i in sys.argv if i.startswith('-show=')]
            if show_attr:
                if len(show_attr) == 1:
                    self.key_to_print = show_attr[0][6:]
                else:
                    raise TypeError('Too many "show" arguments')

            if False in [el in supported_args.keys() for el in sys.argv[1:]
                                            if not el.startswith('-show=')]:
                print '\n-*-sys.argv Error-*-'
                print '\nYou printed:  python',
                for i in sys.argv:
                    print i,
                print ('\nUsage: python %s [ Keys ]\n\n Keys:'
                       % sys.argv[0])
                for i, j in sorted(supported_args.items()):
                    print '{0:<20}{1}'.format(i, j)
                sys.exit(1)

    @staticmethod
    def print_element(element):
        for el in element:
            print el,

    def printer(self):
        if (self.pattern and self.message
            and 'Not supported' not in self.pattern
            and 'Not supported' not in self.message
            and 'Not implemented' not in self.pattern
            and 'Not implemented' not in self.message):
            sys.stdout = open('ok.txt', 'a+')
            ET.dump(self.rule)
            sys.stdout = sys.__stdout__

            RuleView.sys_argv(self)
            '''
            if not did_you_mean:
                print (self.rule.get('id') if self.rule.get('id')
                       else self.rule.getparent().get('id'))
            '''
            if self.key_to_print:
                if self.key_to_print in self.prefix:
                    if self.key_to_print in self.supported_keys:
                        sys.stdout = sys.__stdout__
                else:
                    sys.stdout = codecs.open(os.devnull, encoding='utf-8',
                                                                    mode='w')

            global number
            global amount
            number += 1
###############
            ''' API's "marker" difference handler'''
            if ('marker' in [el.tag
                        for el in self.rule.find('pattern').getchildren()]):

                ''' regexp in marker => suggestion_counters +=1'''

                for string in self.message:
                    if '\\' in string:
                        try:
                            parts = string.split('\\')
                            rest = []
                            for el in parts[1:]:
                                el = str(int(el[0]) + 1) + el[1:]
                                rest.append(el)
                            result = '\\'.join([parts[0], ] + rest)
                            self.message[self.message.index(string)] = result
                        except ValueError:
                            pass
            self.message.append('\n')
###############
            RuleView.print_element(self.pattern)
###############
            ''' API's '<- option[...] ->' handler'''
            print '<- option("%s")' % self.category.get('name'),
            try:
                ''' marker in pattern => -%d> in result'''
                marker = [el.tag for el
            in self.rule.find('pattern').getchildren()].index('marker') + 1
                if not 'skip' in self.keys:
                    print '-%d>' % marker,
                else:
                    print '-%d>' % (marker + 1),
            except ValueError:
                print '->',
###############
            RuleView.print_element(self.message)
############### For debug purposes only.
        elif ('Not implemented' in self.pattern
              or 'Not implemented' in self.message
              and 'Not supported' not in self.pattern
              and 'Not supported' not in self.message):
            global to_implement
            to_implement += 1
#            print ET.dump(self.rule)
            sys.stdout = open('notimplemented.txt', 'a+')
            ET.dump(self.rule)
            sys.stdout = sys.__stdout__
        elif ('Not supported' in self.pattern
              or 'Not supported' in self.message
              and 'Not implemented' not in self.pattern
              and 'Not implemented' not in self.message):
            global no_support
            no_support += 1
            sys.stdout = open('unsupported.txt', 'a+')
            ET.dump(self.rule)
            sys.stdout = sys.__stdout__


class RuleController(object):
    '''flow control'''
    def __init__(self):
        try:
            os.remove(os.path.join(os.getcwd(), 'unsupported.txt'))
        except OSError:
            pass
        try:
            os.remove(os.path.join(os.getcwd(), 'notimplemented.txt'))
        except OSError:
            pass
        try:
            os.remove(os.path.join(os.getcwd(), 'rules.txt'))
        except OSError:
            pass

        self.categories = ET.iterparse("grammar.xml", events=('end',),
                                       tag='category')

    def process(self):
        global number
        global amount
        for _event, category in self.categories:
            for rule in category.iter('rule'):
                amount += 1
                RuleView(rule, category).printer()
        if not did_you_mean:
            percent = float(number) / amount * 100
            print '\n%.3f %s of rules covered (%s/%s)' % (percent, chr(37),
                                                         number, amount)
            global to_implement
            print '%s rules left to cover' % to_implement
            global no_support
            print '%s unsupported rules' % no_support

RuleController().process()
