import logging
import os
import sys

import pyparsing as pp

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.abspath(__file__), '../../knowledge_base')))

pp.ParserElement.enablePackrat()

# setup logging

log = logging.getLogger()
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
# formatter = logging.Formatter('%(message)s (%(asctime)s [%(levelname)s] '
#                               '%(name)s %(funcName)s %(lineno)d)')
formatter = logging.Formatter('%(message)s')
handler.setFormatter(formatter)
log.addHandler(handler)
