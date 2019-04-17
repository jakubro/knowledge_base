import os
import sys

import pyparsing as pp

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.abspath(__file__), '../../knowledge_base')))

pp.ParserElement.enablePackrat()
