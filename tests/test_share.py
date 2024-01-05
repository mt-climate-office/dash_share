import json
from dash_share.share import update_component_state


def test_update_state():
    with open("./tests/test.json", "r") as file:
        layout = json.load(file)

    new_layout = update_component_state(
        layout=layout, updated=None, test1={"children": "it worked!!!"}
    )

    assert new_layout[3]["props"]["children"][0]["props"]["children"] == "it worked!!!"
