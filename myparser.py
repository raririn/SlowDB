from utils.utils import Param
from utils.lex_header import Symbol
from utils.myexception import PrintException
from src.table import Table
import re

class Parser:

    def __init__(self, trie, terminate_map = None):
        self.trie = trie
    
    def _tokenize(self, word):
        if self.trie.search(word):
            terminate = Param.terminate_pair[self.trie.search(word)]
        else:
            if word in Param.punctuation:
                terminate  = 'Delimiter'
            else:
                try:
                    int(word)
                    terminate = 'Value'
                except:
                    terminate = 'Identifier'
        return Symbol(word, terminate)

    def _split(self, string):
        parts = string.split()

        # TODO: Handle multiple keywords

        return list(map(self._tokenize, parts))

    def parse(self, string):
        tokens = re.split("\\s", string.strip())
        for i in range(len(tokens)):
            tokens[i] = tokens[i].lower()
        return self.parse_tokens(tokens)

    def parse_tokens(self, tokens):
        if tokens[0] == "select":
            res = {
                'query': {
                    'select': {
                        'columns': [],
                        'aggr_func': [],
                        'distinct': []
                    },
                    'from': [],
                    'where': {
                        'joins': [],
                        'conditions': []
                    },
                    'groupby': [],
                    'orderby': []
                },
                'tables': {},
                'columns': {}
            }
            i = 1
            distinct = False
            if tokens[1] == "distinct":
                i += 1
                distinct = True
            ss = ''
            while i < len(tokens) and tokens[i] != "from":
                if re.match("^\\(.*", tokens[i]):
                    subquery = []
                    j = i
                    while not re.match("[^(]*\\)$", tokens[i]):
                        if i == j:
                            subquery.append(tokens[i][1:])
                        else:
                            subquery.append(tokens[i])
                        i += 1
                    if i == j:
                        subquery.append(tokens[i][1:-1])
                    else:
                        subquery.append(tokens[i][:-1])
                    i += 1
                    temp = self.evaluate(self.parse_tokens(subquery))
                    res['tables'][temp.name] = temp
                    ss += temp.name + ' '
                else:
                    ss += tokens[i] + ' '
                    i += 1
            
            cols = re.split(",", ss.strip())
            for col in cols:
                s = re.split("\\s", col.strip())
                if len(s) > 3 or len(s) < 1:
                    PrintException.syntaxError()
                    raise SyntaxError('')
                elif len(s) == 3:
                    if s[1] != "as":
                        PrintException.syntaxError()
                        raise SyntaxError('')
                    elif re.search("\\(", s[0]):
                        parts = re.split("[\\(\\)]", s[0])
                        res['query']['select']['aggr_func'].append([parts[0], s[2]])
                        res['query']['select']['columns'].append(s[2])
                        res['columns'][s[2]] = parts[1]
                        if distinct:
                            res['query']['select']['distinct'].append(s[2])
                    else:
                        res['query']['select']['columns'].append(s[2])
                        res['columns'][s[2]] = s[0]
                        if distinct:
                            res['query']['select']['distinct'].append(s[2])
                elif len(s) == 2:
                    if re.search("\\(", s[0]):
                        parts = re.split("[\\(\\)]", s[0])
                        res['query']['select']['aggr_func'].append([parts[0], s[1]])
                        res['query']['select']['columns'].append(s[1])
                        res['columns'][s[1]] = parts[1]
                        if distinct:
                            res['query']['select']['distinct'].append(s[1])
                    else:
                        res['query']['select']['columns'].append(s[1])
                        res['columns'][s[1]] = s[0]
                        if distinct:
                            res['query']['select']['distinct'].append(s[1])
                elif len(s) == 1:
                    if re.search("\\(", s[0]):
                        parts = re.split("[\\(\\)]", s[0])
                        res['query']['select']['aggr_func'].append([parts[0], parts[1]])
                        res['query']['select']['columns'].append(parts[1])
                        res['columns'][parts[1]] = parts[1]
                        if distinct:
                            res['query']['select']['distinct'].append(parts[1])
                    else:
                        res['query']['select']['columns'].append(s[0])
                        res['columns'][s[0]] = s[0]
                        if distinct:
                            res['query']['select']['distinct'].append(s[0])
            
            ss = ''
            i += 1
            while i < len(tokens) and tokens[i] != "where":
                if re.match("^\\(.*", tokens[i]):
                    subquery = []
                    j = i
                    while not re.match("[^(]*\\)$", tokens[i]):
                        if i == j:
                            subquery.append(tokens[i][1:])
                        else:
                            subquery.append(tokens[i])
                        i += 1
                    if i == j:
                        subquery.append(tokens[i][1:-1])
                    else:
                        subquery.append(tokens[i][:-1])
                    i += 1
                    temp = self.evaluate(self.parse_tokens(subquery))
                    res['tables'][temp.name] = temp
                    ss += temp.name + ' '
                else:
                    ss += tokens[i] + ' '
                    i += 1
            
            tables = re.split(",", ss.strip())
            for table in tables:
                s = re.split("\\s", table.strip())
                if len(s) > 3 or len(s) < 1:
                    PrintException.syntaxError()
                    raise SyntaxError('')
                elif len(s) == 3:
                    if s[1] != "as":
                        PrintException.syntaxError()
                        raise SyntaxError('')
                    else:
                        res['query']['from'].append(s[2])
                        res['tables'][s[2]] = s[0]
                elif len(s) == 2:
                    res['query']['from'].append(s[1])
                    res['tables'][s[1]] = s[0]
                elif len(s) == 1:
                    res['query']['from'].append(s[0])
                    res['tables'][s[0]] = s[0]
            
            i += 1
            last_junction = None
            while i < len(tokens) and tokens[i] != "order" and tokens[i] != "group":
                if tokens[i] in ['and', 'or']:
                    last_junction = tokens[i]
                    i += 1
                op0, op1, op2 = tokens[i], tokens[i + 1], tokens[i + 2]
                if Parser._is_val(op2):
                    if last_junction:
                        res['query']['where']['conditions'].append([last_junction, [op0, op1, op2]])
                    else:
                        res['query']['where']['conditions'].append(['and', [op0, op1, op2]])
                else:
                    res['query']['where']['joins'].append([op0, op1, op2])
                i += 3
            
            if i < len(tokens):
                if tokens[i] == "group":
                    i += 2
                    if i < len(tokens) and tokens[i] != "order":
                        ss = ''
                        while i < len(tokens) and tokens[i] != "order":
                            ss += tokens[i] + ' '
                            i += 1
                        parts = re.split(",", ss.strip())
                        for part in parts:
                            s = part.strip()
                            if len(s) > 0:
                                res['query']['groupby'].append(s)
                    else:
                        PrintException.syntaxError()
                        raise SyntaxError('')
                    i += 2
                    if i < len(tokens):
                        ss = ''
                        while i < len(tokens) and tokens[i] != 'group':
                            ss += tokens[i] + ' '
                            i += 1
                        parts = re.split(",", ss.strip())
                        for part in parts:
                            s = re.split("\\s", part.strip())
                            if len(s) > 2 or len(s) < 1:
                                PrintException.syntaxError()
                                raise SyntaxError('')
                            elif len(s) == 2:
                                if s[1] == 'asc' or s[1] == 'desc':
                                    res['query']['orderby'].append([s[0], s[1] == 'asc'])
                                else:
                                    PrintException.syntaxError()
                                    raise SyntaxError('')
                            elif len(s) == 1:
                                res['query']['orderby'].append([s[0], True])
                
                elif tokens[i] == "order":
                    i += 2
                    if i < len(tokens) and tokens[i] != 'group':
                        ss = ''
                        while i < len(tokens) and tokens[i] != 'group':
                            ss += tokens[i] + ' '
                            i += 1
                        parts = re.split(",", ss.strip())
                        for part in parts:
                            s = re.split("\\s", part.strip())
                            if len(s) > 2 or len(s) < 1:
                                PrintException.syntaxError()
                                raise SyntaxError('')
                            elif len(s) == 2:
                                if s[1] == 'asc' or s[1] == 'desc':
                                    res['query']['orderby'].append([s[0], s[1] == 'asc'])
                                else:
                                    PrintException.syntaxError()
                                    raise SyntaxError('')
                            elif len(s) == 1:
                                res['query']['orderby'].append([s[0], True])
                    else:
                        PrintException.syntaxError()
                        raise SyntaxError('')
                    i += 2
                    if i < len(tokens):
                        if tokens[i] != "order":
                            ss = ''
                            while i < len(tokens) and tokens[i] != "order":
                                ss += tokens[i] + ' '
                                i += 1
                            parts = re.split(",", ss.strip())
                            for part in parts:
                                s = part.strip()
                                if len(s) > 0:
                                    res['query']['groupby'].append(s)
                        else:
                            PrintException.syntaxError()
                            raise SyntaxError('')
                else:
                    PrintException.syntaxError()
                    raise SyntaxError('')

            return res

        elif tokens[0] == "create":
            if len(tokens) < 2:
                PrintException.syntaxError()
                raise SyntaxError('')
            elif tokens[1] == 'database':
                return {'name': tokens[2]}
            elif tokens[1] == 'table':
                res = {
                    'name': tokens[2],
                    'col_names': [],
                    'dtype': [],
                    'primary_key': [],
                    'foreign_key': []
                }
                if tokens[3] == 'as':
                    temp_table = self.evaluate(self.parse_tokens(tokens[4:]))

                else:
                    i = 3
                    if re.match("^\\(", tokens[i]):
                        tokens[i] = tokens[i][1:]
                    while i < len(tokens):
                        if tokens[i] == ',':
                            i += 1
                            continue
                        elif re.macth(",", tokens[i]):
                            tokens[i] = tokens[i][1:]
                        if tokens[i] == 'primary':
                            if tokens[i + 1] != 'key':
                                PrintException.syntaxError()
                                raise SyntaxError('')
                            i += 2
                            while i < len(tokens) and not re.search("\\)", tokens[i]):
                                res['primary_key'].append(tokens[i].strip('(,'))
                                i += 1
                            if i < len(tokens):
                                s = tokens[i].strip('),')
                                if len(s) > 0:
                                    res['primary_key'].append(s)
                                i += 1
                        elif tokens[i] == 'foreign':
                            if tokens[i + 1] != 'key':
                                PrintException.syntaxError()
                                raise SyntaxError('')
                            i += 2
                            s = ''
                            while i < len(tokens) and tokens[i] != 'references':
                                s += tokens[i]
                                i += 1
                            s = s.strip('()')
                            s = s.rstrip(',')
                            foreign_keys = re.split(",")
                            if i < len(tokens):
                                i += 1
                                s = ''
                                while i < len(tokens) and not re.search("\\)", tokens[i]):
                                    s += tokens[i]
                                    i += 1
                                s += tokens[i]
                                i += 1
                                s = s.rstrip(',')
                                parts = re.split("\\(", s)
                                table = parts[0]
                                s = parts[1].strip(')')
                                parts = re.split(",", s)
                                if i < len(tokens) and tokens[i] == ',':
                                    i += 1
                                on_delete = 0
                                if i + 2 < len(tokens) and tokens[i] == 'on' and tokens[i + 1] == 'delete':
                                    i += 2
                                    if (i + 1) < len(tokens):
                                        if tokens[i] == 'set' and tokens[i + 1] == 'null':
                                            on_delete = Table.ONDELETE_SETNULL
                                        elif tokens[i] == 'set' and tokens[i + 1] == 'default':
                                            on_delete = Table.ONDELETE_SETDEFAULT
                                        elif tokens[i] == 'no' and tokens[i + 1] == 'action':
                                            on_delete = Table.ONDELETE_NOACTION
                                    if tokens[i] == 'cascade':
                                        on_delete = Table.ONDELETE_CASCADE
                                    elif tokens[i] == 'restrict':
                                        on_delete = Table.ONDELETE_RESTRICT
                                    else:
                                        PrintException.syntaxError()
                                        raise SyntaxError('')
                                else:
                                    PrintException.syntaxError()
                                    raise SyntaxError('')
                                res['foreign_key'].append([foreign_keys, table, parts, on_delete])
                            else:
                                PrintException.syntaxError()
                                raise SyntaxError('')
                        else:
                            res['col_names'].append(tokens[i])
                            if re.match(",$", tokens[i + 1]):
                                res['dtype'].append(tokens[i + 1][:-1])
                            else:
                                res['dtype'].append(tokens[i + 1])
                            i += 2
                return res
            elif tokens[1] == 'index':
                index_name = tokens[2]
                if tokens[3] != 'on':
                    PrintException.syntaxError()
                    raise SyntaxError('')
                table_name = tokens[4]
                s = ''
                for i in range(5, len(tokens)):
                    s += tokens[i]
                parts = re.split(",", s)
                cols = []
                for part in parts:
                    cols.append(part.strip('()'))
                return {'name': index_name, 'table': table_name, 'columns': cols}
            else:
                PrintException.syntaxError()
                raise SyntaxError('')

        elif tokens[0] == "drop":
            if len(tokens) < 3:
                PrintException.syntaxError()
                raise SyntaxError('')
            elif tokens[1] == 'database':
                return {'name': tokens[2]}
            elif tokens[1] == 'table':
                return {'name': tokens[2]}
            elif tokens[1] == 'index':
                if len(tokens)< 5:
                    PrintException.syntaxError()
                    raise SyntaxError('')
                else:
                    return {'table': tokens[4], 'index': tokens[2]}
            else:
                PrintException.syntaxError()
                raise SyntaxError('')
        
        elif tokens[0] == 'update':
            table = tokens[1]
            i = 3
            s = ''
            while i < len(tokens) and tokens[i] != 'where':
                s += tokens[i]
                i += 1
            parts = re.split(",", s)
            vals = []
            for part in parts:
                vals.append(re.split("=", part))
            i += 1
            conditions = []
            last_junction = None
            while i < len(tokens):
                if tokens[i] in ['and', 'or']:
                    last_junction = tokens[i]
                    i += 1
                op0, op1, op2 = tokens[i], tokens[i + 1], tokens[i + 2]
                if last_junction:
                    conditions.append([last_junction, [op0, op1, op2]])
                else:
                    conditions.append(['and', [op0, op1, op2]])
                i += 3
            return {
                'update': table,
                'set': vals,
                'where': conditions
            }
        
        elif tokens[0] == 'insert':
            i = 4
            s = ''
            while i < len(tokens):
                s += tokens[i]
                i += 1
            s = s.strip('()')
            return {
                'insert_into': tokens[2],
                'values': re.split(",", s)
            }
        
        else:
            PrintException.syntaxError()
            raise SyntaxError('')

    @staticmethod
    def _is_val(x):
        try:
            float(x)
            return True
        except:
            return False
