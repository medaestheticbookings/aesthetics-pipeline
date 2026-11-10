# -*- coding: utf-8 -*-
"""Add an EL/EN toggle to the clinic-owners landing page.

    python add_english.py

Greek stays the default and the page never switches on its own: English
loads only if the visitor pressed EN before (localStorage map_lang), which
is the same contract the patient site at /greece/ uses.

Every element that holds Greek copy gets a data-en attribute carrying its
English innerHTML. Only the outermost such element is annotated, so a
paragraph with <b> inside it swaps as one piece.

Strings not in EN below are left in Greek rather than machine-guessed.
"""
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "index.html")

GREEK = re.compile(r"[Α-Ωα-ωΆ-Ώά-ώΪΫϊϋΐΰ]")
INLINE = r"b|em|strong|i|u|br|span|a|small|sup"
ELEM = re.compile(
    r"<(h1|h2|h3|h4|p|li|span|option|td|th|summary|label|button|a|div)\b([^>]*)>"
    r"((?:[^<]|<(?:%s)\b[^>]*>|</(?:%s)>)*?)"
    r"</\1>" % (INLINE, INLINE),
    re.S,
)

EN = json.load(io.open(os.path.join(HERE, "_en.json"), encoding="utf-8"))

TOGGLE_CSS = """
  .lang{display:inline-flex;gap:2px;margin-left:14px;border:1px solid var(--line);
    border-radius:999px;overflow:hidden;background:var(--card);}
  .lang button{border:0;background:none;font:inherit;font-size:12px;font-weight:800;
    letter-spacing:.06em;padding:7px 11px;cursor:pointer;color:var(--ink-soft);}
  .lang button.on{background:var(--teal);color:#fff;}
  @media(max-width:560px){ .lang{margin-left:8px;} .lang button{padding:6px 9px;} }
"""

TOGGLE_JS = """
<script>
/* EL/EN. Greek is the default and nothing reads navigator.language:
   the page switches only because someone pressed EN. */
(function(){
  var KEY = 'map_lang';
  function setLang(lang){
    document.documentElement.lang = (lang === 'en') ? 'en' : 'el';
    var nodes = document.querySelectorAll('[data-en]');
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      if (!n.hasAttribute('data-el')) n.setAttribute('data-el', n.innerHTML);
      n.innerHTML = (lang === 'en') ? n.getAttribute('data-en') : n.getAttribute('data-el');
    }
    var ph = document.querySelectorAll('[data-en-ph]');
    for (var j = 0; j < ph.length; j++) {
      var p = ph[j];
      if (!p.hasAttribute('data-el-ph')) p.setAttribute('data-el-ph', p.placeholder || '');
      p.placeholder = (lang === 'en') ? p.getAttribute('data-en-ph') : p.getAttribute('data-el-ph');
    }
    var btns = document.querySelectorAll('.lang button');
    for (var k = 0; k < btns.length; k++) {
      btns[k].classList.toggle('on', btns[k].getAttribute('data-lang') === lang);
    }
    try { localStorage.setItem(KEY, lang); } catch (e) {}
  }
  document.addEventListener('click', function(e){
    var b = e.target.closest ? e.target.closest('.lang button') : null;
    if (b) { e.preventDefault(); setLang(b.getAttribute('data-lang')); }
  });
  var saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) {}
  setLang(saved === 'en' ? 'en' : 'el');
})();
</script>
"""


def main():
    s = io.open(PAGE, encoding="utf-8").read()
    if "data-en=" in s:
        sys.exit("already translated — revert first")

    head, body = s.split("<body>", 1)

    # outermost elements only: once a span is taken, anything inside it is skipped
    # anything inside a <script> is code, not copy
    skip = [(m.start(), m.end()) for m in re.finditer(r'<script.*?</script>', body, re.S)]
    taken = []
    edits = []
    missing = []
    for m in ELEM.finditer(body):
        a, b = m.span()
        if any(a >= x and b <= y for x, y in skip) or any(a >= x and b <= y for x, y in taken):
            continue
        inner = m.group(3)
        if not GREEK.search(inner):
            continue
        key = inner.strip()
        if key not in EN:
            missing.append(key)
            continue
        taken.append((a, b))
        edits.append((m.start(2), m.end(2), EN[key]))

    # apply back to front so earlier offsets stay valid
    for start, end, en in sorted(edits, reverse=True):
        attrs = body[start:end]
        esc = en.replace("&", "&amp;").replace('"', "&quot;")
        esc = esc.replace("&amp;amp;", "&amp;").replace("&amp;nbsp;", "&nbsp;")
        body = body[:start] + attrs + ' data-en="%s"' % esc + body[end:]

    # placeholders
    ph = 0
    def ph_sub(m):
        nonlocal ph
        val = m.group(1)
        if val.strip() in EN:
            ph += 1
            return 'placeholder="%s" data-en-ph="%s"' % (val, EN[val.strip()].replace('"', "&quot;"))
        return m.group(0)
    body = re.sub(r'placeholder="([^"]*)"', ph_sub, body)

    # the switch itself, next to the nav CTA (which now carries data-en)
    i = body.find('class="nav-cta"')
    if i < 0:
        sys.exit("ABORT: nav CTA not found")
    j = body.index("</a>", i) + 4
    toggle = ('<span class="lang">'
              '<button type="button" data-lang="el">ΕΛ</button>'
              '<button type="button" data-lang="en">EN</button></span>')
    body = body[:j] + chr(10) + "    " + toggle + body[j:]

    body = body.replace("</body>", TOGGLE_JS.strip() + "\n</body>", 1)

    anchor = "  .mid-cta{"
    if head.count(anchor) != 1:
        sys.exit("ABORT: css anchor")
    head = head.replace(anchor, TOGGLE_CSS.strip("\n") + "\n" + anchor)

    io.open(PAGE, "w", encoding="utf-8", newline="\n").write(head + "<body>" + body)
    print("translated elements : %d" % len(edits))
    print("placeholders        : %d" % ph)
    print("left in Greek       : %d" % len(missing))
    for k in missing[:15]:
        print("   ·", k[:90])


if __name__ == "__main__":
    main()
