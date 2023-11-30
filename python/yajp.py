from typing import List, Dict, Union

JSONValue = Union[
    str, int, float, bool, None, List["JSONValue"], Dict[str, "JSONValue"]
]
JSONElement = JSONValue


class JSONParserError(Exception):
    pass


class JSONParser:
    def __init__(self, s: str) -> None:
        self.s = s
        self.idx = 0
        self.len = len(s)

    def parse(self) -> JSONElement:
        return self.parse_element(True)

    def parse_element(self, root=False) -> JSONElement:
        obj = None
        assigned = False

        while (val := self.peek()) is not None:
            if self.is_ws(val):
                self.consume()
            elif assigned:
                break
            elif val == "{":
                obj = self.parse_object()
                assigned = True
            elif val == "[":
                obj = self.parse_array()
                assigned = True
            elif val == '"':
                obj = self.parse_string()
                assigned = True
            elif val in "-0123456789":
                obj = self.parse_number()
                assigned = True
            elif val == "t":
                obj = self.parse_literal("true", True)
                assigned = True
            elif val == "f":
                obj = self.parse_literal("false", False)
                assigned = True
            elif val == "n":
                obj = self.parse_literal("null", None)
                assigned = True
            else:
                raise JSONParserError(f"Unexpected character: {val}")

        if root:
            if self.peek() is not None:
                raise JSONParserError(f"Unexpected character: {self.peek()}")
            if obj is None and not assigned:
                raise JSONParserError(f"Unexpected EOF at index {self.idx}")

        return obj

    def is_ws(self, c: str) -> bool:
        return c in " \t\n\r"

    def is_valid_literal_ending(self, c: Union[str, None]) -> bool:
        return c is None or self.is_ws(c) or c in ",]}"

    def parse_object(self) -> Dict[str, JSONElement]:
        self.consume()
        obj = {}
        expects_key = True
        expects_colon = False
        expects_object = False
        while (val := self.peek()) is not None:
            if self.is_ws(val):
                self.consume()
            elif (
                (len(obj) == 0 or not expects_key)
                and not expects_object
                and not expects_colon
                and val == "}"
            ):
                self.consume()
                return obj
            elif expects_key:
                key = self.parse_string()
                expects_key = False
                expects_colon = True
            elif expects_colon and val == ":":
                self.consume()
                expects_object = True
                expects_colon = False
            elif expects_object:
                el = self.parse_element()
                obj[key] = el
                expects_object = False
            elif not expects_object and val == ",":
                self.consume()
                expects_key = True
            else:
                raise JSONParserError(f"Unexpected character: {val}")

        raise JSONParserError(f"Expected \x7d, found {self.peek()}")

    def parse_array(self) -> List[JSONElement]:
        self.consume()
        arr = []
        expects_element = True
        while (val := self.peek()) is not None:
            if self.is_ws(val):
                self.consume()
            elif (len(arr) == 0 or not expects_element) and val == "]":
                self.consume()
                return arr
            elif expects_element:
                arr.append(self.parse_element())
                expects_element = False
            elif val == ",":
                self.consume()
                expects_element = True
            else:
                raise JSONParserError(f"Unexpected character: {val}")
        raise JSONParserError(f"Expected \x5d, found {self.peek()}")

    def parse_hex(self, n: int) -> Union[int, None]:
        start = self.idx
        while (val := self.peek()) is not None:
            if self.idx - start == n:
                break
            if val in "0123456789abcdefABCDEF":
                self.consume()
            else:
                raise JSONParserError(f"Unexpected character: {val}")
        if self.idx - start != n:
            raise JSONParserError(f"Unexpected EOF at index {self.idx}")
        return int(self.s[start : self.idx], 16)

    def parse_string(self) -> str:
        s = []
        self.consume()

        while (val := self.peek()) is not None:
            if val == '"':
                self.consume()
                return "".join(s)
            elif val == "\\":
                self.consume()
                if (val := self.peek()) is None:
                    raise JSONParserError(f"Unexpected EOF at index {self.idx}")
                elif val == '"':
                    s.append('"')
                elif val == "\\":
                    s.append("\\")
                elif val == "/":
                    s.append("/")
                elif val == "b":
                    s.append("\b")
                elif val == "f":
                    s.append("\f")
                elif val == "n":
                    s.append("\n")
                elif val == "r":
                    s.append("\r")
                elif val == "t":
                    s.append("\t")
                elif val == "u":
                    self.consume()
                    code = self.parse_hex(4)
                    if code is None:
                        raise JSONParserError(
                            f"Invalid unicode escape at index {self.idx}"
                        )
                    if len(s) > 0 and 0xD800 <= ord(s[-1]) <= 0xDBFF and 0xDC00 <= code <= 0xDFFF:
                        s[-1] = chr((ord(s[-1]) - 0xD800) * 0x400 + (code - 0xDC00) + 0x10000)
                    else:
                        s.append(chr(code))
                    continue
                else:
                    raise JSONParserError(f"Invalid escape at index {self.idx}")
                self.consume()
            elif ord(val) < 0x20:
                raise JSONParserError(f"Invalid character at index {self.idx}")
            else:
                s.append(val)
                self.consume()

        raise JSONParserError(f"Invalid character at index {self.idx}")

    def parse_number(self) -> Union[int, float]:
        start = self.idx
        start_fraction, start_exponent = False, False
        number, fraction, exponent, zero, sign_number, sign_exp = (
            False,
            False,
            False,
            False,
            False,
            False,
        )
        while (val := self.peek()) is not None:
            if val == ".":
                if fraction or exponent or (sign_number and not (number or zero)):
                    raise JSONParserError(f"Invalid state: {fraction, exponent}")
                fraction = True
                self.consume()
                continue
            elif val in "eE":
                if exponent or (fraction and not start_fraction):
                    raise JSONParserError(f"Invalid state: {fraction, exponent}")
                exponent = True
                fraction = False
                self.consume()
                continue
            elif fraction:
                if val in "0123456789":
                    if not start_fraction:
                        start_fraction = self.idx
                    self.consume()
                elif not start_fraction:
                    raise JSONParserError(f"Unexpected character: {val}")
                else:
                    break
            elif exponent:
                if not sign_exp and not start_exponent and (val == "-" or val == "+"):
                    sign_exp = True
                    self.consume()
                elif val in "0123456789":
                    if not start_exponent:
                        start_exponent = self.idx
                    self.consume()
                elif not start_exponent:
                    raise JSONParserError(f"Unexpected character: {val}")
                else:
                    break
            else:
                if start == self.idx:
                    if val == "-":
                        sign_number = True
                        self.consume()
                    elif val == "0":
                        zero = True
                        self.consume()
                    elif val in "123456789":
                        number = True
                        self.consume()
                    else:
                        raise JSONParserError(f"Unexpected character: {val}")
                elif self.idx == start + 1 and sign_number:
                    if val == "0":
                        zero = True
                        self.consume()
                    elif val in "123456789":
                        number = True
                        self.consume()
                    else:
                        break
                elif zero:
                    if val in "0123456789":
                        raise JSONParserError(f"Unexpected character: {val}")
                    else:
                        break
                elif number:
                    if val in "0123456789":
                        self.consume()
                    else:
                        break

        if fraction or exponent:
            return float(self.s[start : self.idx])
        else:
            return int(self.s[start : self.idx])

    def parse_literal(self, target: str, value: Union[bool, None]) -> Union[bool, None]:
        for c in target:
            if self.peek() != c:
                raise JSONParserError(f"Found {self.peek()}, expected {target}")
            self.consume()
        if not self.is_valid_literal_ending(self.peek()):
            raise JSONParserError(f"Found {self.peek()}, expected whitespace")
        return value

    def peek(self, offset=0) -> Union[str, None]:
        if self.idx + offset >= self.len:
            return None
        return self.s[self.idx]

    def consume(self) -> str:
        if self.idx >= self.len:
            raise JSONParserError(f"Unexpected EOF at index {self.idx}")
        self.idx += 1
        return self.s[self.idx - 1]


def parse(s: str) -> JSONElement:
    return JSONParser(s).parse()
