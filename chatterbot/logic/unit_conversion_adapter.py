from chatterbot.logic import LogicAdapter
from chatterbot.conversation import Statement
from chatterbot import parsing
from pint import UnitRegistry
from mathparse import mathparse
import re


class UnitConversion(LogicAdapter):
    """
    The UnitConversion logic adapter parse inputs to convert values
    between several metric units.

    For example:
        User: 'How many meters are in one kilometer?'
        Bot: '1000.0'

    :kwargs:
        * *language* (``str``) --
        The language is set to 'ENG' for English by default.
    """

    def __init__(self, **kwargs):
        super(UnitConversion, self).__init__(**kwargs)

        self.language = kwargs.get('language', 'ENG')
        self.cache = {}
        self.patterns = [
            (
                re.compile(r'''
                   (([Hh]ow\s+many)\s+
                   (?P<target>\S+)\s+ # meter, celsius, hours
                   ((are)*\s*in)\s+
                   (?P<number>([+-]?\d+(?:\.\d+)?)|(a|an)|(%s[-\s]?)+)\s+
                   (?P<from>\S+)\s*) # meter, celsius, hours
                   ''' % (parsing.numbers),
                    (re.VERBOSE | re.IGNORECASE)
                ),
                lambda m: self.handle_matches(m)
            ),
            (
                re.compile(r'''
                   ((?P<number>([+-]?\d+(?:\.\d+)?)|(%s[-\s]?)+)\s+
                   (?P<from>\S+)\s+ # meter, celsius, hours
                   (to)\s+
                   (?P<target>\S+)\s*) # meter, celsius, hours
                   ''' % (parsing.numbers),
                    (re.VERBOSE | re.IGNORECASE)
                ),
                lambda m: self.handle_matches(m)
            ),
            (
                re.compile(r'''
                   ((?P<number>([+-]?\d+(?:\.\d+)?)|(a|an)|(%s[-\s]?)+)\s+
                   (?P<from>\S+)\s+ # meter, celsius, hours
                   (is|are)\s+
                   (how\s+many)*\s+
                   (?P<target>\S+)\s*) # meter, celsius, hours
                   ''' % (parsing.numbers),
                    (re.VERBOSE | re.IGNORECASE)
                ),
                lambda m: self.handle_matches(m)
            )
        ]

    def get_unit(self, ureg, unit_variations):
        """
        Get the first match unit metric object supported by pint library
        given a variation of unit metric names (Ex:['HOUR', 'hour']).

        :param ureg: unit registry which units are defined and handled
        :type ureg: pint.registry.UnitRegistry object

        :param unit_variations: A list of strings with names of units
        :type unit_variations: str
        """
        for unit in unit_variations:
            try:
                return getattr(ureg, unit)
            except Exception:
                continue
        return None

    def get_valid_units(self, ureg, from_unit, target_unit):
        """
        Returns the firt match `pint.unit.Unit` object for from_unit and
        target_unit strings from a possible variation of metric unit names
        supported by pint library.

        :param ureg: unit registry which units are defined and handled
        :type ureg: `pint.registry.UnitRegistry`

        :param from_unit: source metric unit
        :type from_unit: str

        :param from_unit: target metric unit
        :type from_unit: str
        """
        from_unit_variations = [from_unit.lower(), from_unit.upper()]
        target_unit_variations = [target_unit.lower(), target_unit.upper()]
        from_unit = self.get_unit(ureg, from_unit_variations)
        target_unit = self.get_unit(ureg, target_unit_variations)
        return from_unit, target_unit

    def handle_matches(self, match):
        """
        Returns a response statement from a matched input statement.

        :param match: It is a valid matched pattern from the input statement
        :type: `_sre.SRE_Match`
        """
        response = Statement(text='')
        try:
            from_parsed = match.group("from")
            target_parsed = match.group("target")
            n_statement = match.group("number")

            if n_statement == 'a' or n_statement == 'an':
                n_statement = '1.0'

            n = mathparse.parse(n_statement, self.language)

            ureg = UnitRegistry()
            from_parsed, target_parsed = self.get_valid_units(ureg, from_parsed, target_parsed)

            if from_parsed is None or target_parsed is None:
                raise

            from_value = ureg.Quantity(float(n), from_parsed)
            target_value = from_value.to(target_parsed)
            response.confidence = 1.0
            response.text = str(target_value.magnitude)
        except Exception:
            response.confidence = 0.0
        finally:
            return response

    def can_process(self, statement):
        response = self.process(statement)
        self.cache[statement.text] = response
        return response.confidence == 1.0

    def process(self, statement):
        response = Statement(text='')
        input_text = statement.text
        try:
            # Use the result cached by the process method if it exists
            if input_text in self.cache:
                response = self.cache[input_text]
                self.cache = {}
                return response

            for pattern, func in self.patterns:
                p = pattern.match(input_text)
                if p is not None:
                    response = func(p)
                    if response.confidence == 1.0:
                        break
        except Exception:
            response.confidence = 0.0
        finally:
            return response
