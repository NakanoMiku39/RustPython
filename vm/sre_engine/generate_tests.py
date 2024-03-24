import os
from pathlib import Path
import re
import sre_constants
import sre_compile
import sre_parse
import json
from itertools import chain

m = re.search(r"const SRE_MAGIC: usize = (\d+);", open("src/constants.rs").read())
sre_engine_magic = int(m.group(1))
del m

assert sre_constants.MAGIC == sre_engine_magic

class CompiledPattern:
    @classmethod
    def compile(cls, pattern, flags=0):
        p = sre_parse.parse(pattern)
        code = sre_compile._code(p, flags)
        self = cls()
        self.pattern = pattern
        self.code = code
        self.flags = re.RegexFlag(flags | p.state.flags)
        return self

for k, v in re.RegexFlag.__members__.items():
    setattr(CompiledPattern, k, v)


# matches `// pattern {varname} = re.compile(...)`
pattern_pattern = re.compile(r"^((\s*)\/\/\s*pattern\s+(\w+)\s+=\s+(.+?))$(?:.+?END GENERATED)?", re.M | re.S)
def replace_compiled(m):
    line, indent, varname, pattern = m.groups()
    pattern = eval(pattern, {"re": CompiledPattern})
    pattern = f"Pattern {{ code: &{json.dumps(pattern.code)} }}"
    return f'''{line}
{indent}// START GENERATED by generate_tests.py
{indent}#[rustfmt::skip] let {varname} = {pattern};
{indent}// END GENERATED'''

with os.scandir("tests") as t, os.scandir("benches") as b:
    for f in chain(t, b):
        path = Path(f.path)
        if path.suffix == ".rs":
            replaced = pattern_pattern.sub(replace_compiled, path.read_text())
            path.write_text(replaced)
