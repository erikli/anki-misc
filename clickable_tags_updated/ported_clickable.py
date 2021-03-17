# Copyright 2013 Abdolmahdi Saravi <amsaravi@yahoo.com>
# Copyright 2019 Joseph Lorimer <joseph@lorimer.me>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
An example of porting old template/wrapping code to Anki 2.1.20.
The add-on now looks for {{clickable:Tags}} instead of just {{Tags}}
on the template.
"""


from anki import hooks
from anki.template import TemplateRenderContext
from aqt import dialogs, gui_hooks, mw
from aqt.browser import PreviewDialog
from aqt.clayout import CardLayout
from aqt.qt import Qt
from aqt.reviewer import Reviewer

# Responding to clicks
############################
from aqt.utils import tooltip


def on_js_message(handled, msg, context):
    if isinstance(context, CardLayout) and (
        msg.startswith("ct_click_") or msg.startswith("ct_dblclick_")
    ):
        # card layout is a modal dialog, so we can't display there
        tooltip("Can't be used in card layout screen.")
        return handled

    if not isinstance(context, Reviewer) and not isinstance(context, PreviewDialog):
        # only function in review and preview screens
        return handled

    if msg.startswith("ct_click_"):
        tag = msg.replace("ct_click_", "")
        browser = dialogs.open("Browser", mw)
        browser.setFilter('"tag:%s"' % tag)
        return True, None
    elif msg.startswith("ct_dblclick_"):
        tag, deck = msg.replace("ct_dblclick_", "").split("|")
        browser = dialogs.open("Browser", mw)
        browser.setFilter('"tag:%s" "deck:%s"' % (tag, deck))
        browser.setWindowState(
            browser.windowState() & ~Qt.WindowMinimized | Qt.WindowActive
        )
        return True, None

    return handled


gui_hooks.webview_did_receive_js_message.append(on_js_message)

# Adding CSS/JS to card
############################

add_to_card = """
<style>
  kbd {
    box-shadow: inset 0 1px 0 0 white;
    background:
      gradient(
        linear,
        left top,
        left bottom,
        color-stop(0.05, #f9f9f9),
        color-stop(1, #e9e9e9)
      );
    background-color: #f9f9f9;
    border-radius: 4px;
    border: 1px solid gainsboro;
    display: inline-block;
    font-size: 15px;
    height: 15px;
    line-height: 15px;
    padding: 4px 4px;
    margin: 5px;
    text-align: center;
    text-shadow: 1px 1px 0 white;
    cursor: pointer;
    cursor: hand;
  }
  
</style>
<script type="text/javascript">
function ct_click(tag) {
    pycmd("ct_click_" + tag)
    return false;
}
function ct_dblclick(tag, deck) {
    pycmd("ct_dblclick_" + tag + "|" + deck)
    return false;
}
</script>
"""


def on_card_render(output, context):
    output.question_text += add_to_card
    output.answer_text += add_to_card


hooks.card_did_render.append(on_card_render)

# Handling {{clickable:Tags}}
################################


def on_field_filter(text, field, filter, context: TemplateRenderContext):
    if filter != "clickable" or field != "Tags":
        return text

    tags = sorted(context.fields()["Tags"].split())
    tag_tree = list()
    tag_tracker = dict()
    # tree is [{'name':'tagName','sub':[]}] where `sub` contains subtrees
    # tracker is ['tagName':treeObj]

    SEPARATOR = "::"# TODO: configurable SEPARATOR
    for t in tags:
        components = t.split(SEPARATOR)
        for idx, c in enumerate(components):
            partial_tag = SEPARATOR.join(components[0 : idx + 1])
            if not tag_tracker.get(partial_tag):
                treeObj = {'name':partial_tag,'sub':list()}
                tag_tracker[partial_tag] = treeObj
                if idx == 0:
                    tag_tree.append(treeObj)
                else:
                    parent_tag = SEPARATOR.join(components[0:idx])
                    parent = tag_tracker[parent_tag]
                    parent['sub'].append(treeObj)

    def _add_kbd_tag_recursive(tag_tree,deck):
        kbd_start = """<kbd onclick="var event=arguments[0]||window.event;if(event.target==this) ct_click('{tag}');" ondblclick="var event=arguments[0]||window.event;if(event.target==this) ct_dblclick('{tag}', '{deck}');">{short_tag}"""
        kbd_end = "</kbd>"
        return "".join(["{start}{inner}{end}".format(
            start = kbd_start.format(tag=tagObj['name'],short_tag=tagObj['name'].split(SEPARATOR)[-1],deck=deck),
            inner = _add_kbd_tag_recursive(tagObj['sub'],deck),
            end = kbd_end)
         for tagObj in tag_tree])

    return _add_kbd_tag_recursive(tag_tree,context.fields()["Deck"])


hooks.field_filter.append(on_field_filter)
