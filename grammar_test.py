import pyparsing as pp

import knowledge_base.grammar

pp.ParserElement.enablePackrat()

if __name__ == '__main__':
    knowledge_base.grammar.Formula.runTests("""
        x = y
        x != y
        
        Not Likes
        !Likes
        
        # for all x
        *x: x
        *x: !x != x
        
        # for all x: exists y: ...
        *x, ?y: Add(x, y)
        *x, ?y: Add(x, y) != x 
        *x, ?y: Add(x, y) != x & y != 0
    """)
