import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from hashlib import shake_128
from typing import Any, Callable
from urllib.parse import urlparse, parse_qs
from pathlib import Path

import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, no_update
from dash.dependencies import Input, Output, State, Component

AppLayout = list[dict[str, Any]]


def update_component_state(
    layout: list[dict[str, Any]] | dict[str, Any],
    updated: None | list[dict[str, Any]] = None,
    **kwargs: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Recursively updates values in a Dash app layout.

    Args:
        layout (list[dict[str, Any]] | dict[str, Any]): The Dash app layout to be updated.
        updated (Optional[list[dict[str, Any]]]): A list to store the updated layout.
            Defaults to None, and a new list will be created.
        **kwargs (Dict[str, Union[str, List]]): Keyword arguments where keys are
            component 'id' values in the app's layout, and values are dictionaries
            representing the component props and corresponding values to be applied.

    Returns:
        list[dict[str, Any]]: The updated Dash app layout.

    Example:
        # Update the component with id 'test1' a new 'children'
        # prop equal to 'it worked!!!'
        new_layout = update_component_state(
            layout=your_layout, updated=None, test1={'children': 'it worked!!!'}
        )
    """
    if not kwargs:
        return layout

    if updated is None:
        updated = [] if isinstance(layout, list) else {}

    if isinstance(layout, dict):
        if "children" in layout:
            layout["children"] = update_component_state(
                layout["children"], None, **kwargs
            )
        if "props" in layout:
            layout["props"] = update_component_state(layout["props"], None, **kwargs)
        if "id" in layout:
            id = layout["id"].replace("-", "_")
            if id in kwargs:
                layout.update(kwargs[id])

        return layout

    if isinstance(layout, str) or layout is None:
        return layout

    for item in layout:
        props = item["props"]
        children = props.get("children", None)
        if children and isinstance(children, dict):
            if "children" in children.get("props", "") or "props" in children:
                children["props"] = update_component_state(
                    children["props"], None, **kwargs
                )
            elif "children" in children:
                children["children"] = update_component_state(
                    children["children"], None, **kwargs
                )
            else:
                raise ValueError("Not Expected App Structure")

        if children and isinstance(children, list):
            props["children"] = update_component_state(children, None, **kwargs)

        id = props.get("id", "")
        id = id.replace("-", "_")
        if id not in kwargs:
            updated.append(item)
            continue

        props.update(kwargs[id])
        item["props"] = props
        updated.append(item)

    return updated


@dataclass
class DashShare(ABC):
    """_summary_

    Args:
        app (Dash): The dash app you want to update.
        load_input (tuple): A tuple where the first value is the component 'id' that
            triggers a reload and the second is the component's 'prop'. This will be
            passed into a dash `Input` argument.
        save_input (tuple): A tuple where the first value is the component 'id' that
            triggers the state being saved and the second is the component's 'prop'.
            This will be passed into a dash `Input` argument.
        save_output (tuple): A tuple where the first value is the component 'id' that
            the saved state will be output to and the second is the component's 'prop'.
            This will be passed into a dash `Output` argument.
        url_input (str): The `dcc.Location` url 'id' that will be used to build a url
            that can be shared.
        layout_id (str): The output `id` you want to give the final application layout.
        interval_id (str): The `id` to assign to the interval that allows sharing.
        modal_id (str): The `id` to assign to the modal that pops up with the sharable
            link.
        link_id (str): The `id` to assign to the sharable link textbox.
        interval_delay (int): The number of milliseconds the application should be
            locked after reloading. If there aren't very many callbacks, it can be
            left as the default, but should be longer if callbacks take more than
            two seconds to finish running.
        locked (bool): Track whether or not the application should be locked.

    """

    app: Dash
    load_input: tuple
    save_input: tuple
    save_output: tuple
    url_input: str
    layout_id: str = "app-layout"
    interval_id: str = "update-timer"
    modal_id: str = "save-modal"
    link_id: str = "url-link"
    interval_delay: int = 2000
    locked: bool = field(init=False)

    def __post_init__(self):
        self.locked = False

    def _make_state_tracker_components(
        self, *args: tuple[Component]
    ) -> list[Component]:
        """
        Generate components needed to save component state.

        Args:
            *args: Any other dash components you want to include.
        Returns:
            list[Component]: A new list of components to include in the app's layout.
        """
        return [
            dcc.Interval(
                id=self.interval_id,
                interval=self.interval_delay,
                disabled=True,
                max_intervals=1,
            ),
            dbc.Modal(
                children=[
                    dbc.ModalHeader(),
                    dbc.ModalBody(
                        dcc.Markdown(
                            """
                        #### Copy link below to share data:
                        The link will stay active for 90 days.
                        """
                        )
                    ),
                    html.Div(
                        [
                            dcc.Textarea(
                                id=self.link_id,
                                value="",
                                style={"height": 50, "width": "100%"},
                            ),
                            dcc.Clipboard(
                                target_id=self.link_id,
                                title="Copy URL",
                                style={
                                    "display": "inline-block",
                                    "fontSize": 20,
                                    "verticalAlign": "center",
                                    "paddingLeft": "5px",  # Adjust the value as needed
                                },
                            ),
                        ],
                        style={
                            "display": "flex",
                            "justifyContent": "center",
                            "padding": "15px",
                        },
                    ),
                ],
                id=self.modal_id,
                is_open=False,
                size="md",
                centered=True,
                scrollable=True,
            ),
            *args,
        ]

    def lock(self):
        """Lock components tagged with `@pause_update`."""
        self.locked = True

    def unlock(self):
        """Unlock components tagged with `@pause_update`."""
        self.locked = False

    def update_layout(self, layout: AppLayout, *args: tuple[Component]) -> html.Div:
        """Update your application's layout to include the sharing components.

        Args:
            layout (AppLayout): The application layout to update.
            *args (tuple[Component]): Other components to include in your application layout.

        Returns:
            html.Div: The updated application layout with additional components to share
                the application state.
        """
        return html.Div(
            id=self.layout_id,
            children=[layout, *self._make_state_tracker_components(*args)],
        )

    def pause_update(self, func: Callable):
        """A function decorator that stops callbacks from being triggered when the app
        is `locked`.

        Args:
            func (Callable): The application callback to pause.
        """

        def inner(*args, **kwargs):
            if self.locked:
                return no_update
            return func(*args, **kwargs)

        return inner

    @abstractmethod
    def save(self, input: str, state: AppLayout, hash: str):
        """A user-specified method to save out the application state.

        Args:
            input (str): The input of the component that triggers the save.
            state (AppLayout): The application state (layout).
            hash (str): The hashed code corresponding to the layout.
        """
        pass

    @abstractmethod
    def load(self, input: str, state: AppLayout):
        """A user-specified method to load the state.

        Args:
            input (str): The component input 'id' that will trigger a load.
            state (AppLayout): The current application state. Reused if no update is
                actually made.
        """
        pass

    def register_callbacks(self):
        """Register all the callbacks so they are triggered when the app runs."""

        @self.app.callback(
            Output(self.interval_id, "disabled", allow_duplicate=True),
            Output(self.interval_id, "n_intervals", allow_duplicate=True),
            Input(*self.load_input),
            State(self.interval_id, "disabled"),
            State(self.interval_id, "n_intervals"),
            prevent_initial_call=True,
        )
        def enable_interval_and_lock(trigger, dis, n):
            if trigger:
                self.lock()
                return False, 0
            self.unlock()
            return False, 0

        @self.app.callback(
            Output(self.interval_id, "disabled", allow_duplicate=True),
            Output(self.interval_id, "n_intervals", allow_duplicate=True),
            Input(self.interval_id, "n_intervals"),
            prevent_initial_call=True,
        )
        def unlock_after_interval_trigger(n):
            if n is not None and n > 0:
                self.unlock()
                return True, 1
            return False, 0

        @self.app.callback(
            Output(*self.save_output),
            Output(self.modal_id, "is_open"),
            Output(self.link_id, "value"),
            Input(*self.save_input),
            State(self.layout_id, "children"),
            State(self.modal_id, "is_open"),
            State(self.url_input, "href"),
        )
        @self.pause_update
        def save(input, state, is_open, url):
            hashed_url = self.encode(state)
            # Use user-defined save method.
            output = self.save(input, state, hash=hashed_url)
            if input:
                return (
                    output,
                    not is_open,
                    f"{self.get_url_base(url)}/?state={hashed_url}",
                )
            return output, is_open, ""

        @self.app.callback(
            Output(self.layout_id, "children"),
            Input(*self.load_input),
            State(self.layout_id, "children"),
        )
        def load(input, state):
            # Use user-defined load method.
            return self.load(input, state)

    @staticmethod
    def encode(state: AppLayout, n: int = 8) -> str:
        """Use the `shake_128` algorighm to hash the application layout.

        Args:
            state (AppLayout): The app layout to encode.
            n (int, optional): The number of characters you want the hash to be.
                Defaults to 4.

        Returns:
            str: The hash of the application layout.
        """
        return shake_128(json.dumps(state).encode("utf-8")).hexdigest(int(n / 2))

    @staticmethod
    def get_url_base(url: str) -> str:
        """Get the base url to add the hash code to.

        Args:
            url (str): The url to strip.

        Returns:
            str: The base url.
        """
        on_server = os.getenv("ON_SERVER")

        parsed_url = urlparse(url)
        end = "" if on_server is None or not on_server else "/dash"
        return f"{parsed_url.scheme}://{parsed_url.netloc}{end}"

    @staticmethod
    def parse_query_string(qs: str) -> dict[str, str]:
        """Parse a url query string into a dictionary

        Args:
            qs (str): The url with a query string to parse.

        Returns:
            dict[str, str]: A dict of key, value pairs from the query string.
        """
        qs = qs.replace("?", "")
        parsed_data = parse_qs(qs)
        result_dict = {key: value[0] for key, value in parsed_data.items()}
        return result_dict


class FileShare(DashShare):
    """Share application state by saving a .json file to disk on the host machine.

    Args:
        update_components (list[dict[str, Any]]): Dict of component ids and props
            to update before the state is saved.
    """

    update_components: list[dict[str, Any]] = field(default_factory=list)

    def load(self, input: str, state: AppLayout) -> AppLayout:
        """Load the application state from a file.

        Args:
            input (str): The url with state information
            state (AppLayout): The current application state to use if the share fails.

        Returns:
            AppLayout: The updated layout.
        """
        q = self.parse_query_string(input)
        if "state" in q:
            try:
                with open(f'./share/{q["state"]}.json', "rb") as file:
                    state = json.load(file)
            except FileNotFoundError:
                return state
            state = update_component_state(
                state, None, **{self.modal_id: {"is_open": False}}
            )
        return state

    def save(self, input: str, state: AppLayout, hash: str) -> str:
        """The function that saves the app state when the input callback is triggered.

        Args:
            input (str): The input value that triggered the save callback.
            state (AppLayout): The application state to be saved.
            hash (str): The hash that encodes the state.

        Returns:
            str: _description_
        """
        out_dir = Path("./share")
        if not out_dir.exists():
            out_dir.mkdir()

        if Path(f"./{out_dir}/{hash}.json").exists():
            return input
        if input is not None and input > 0:
            if self.update_components:
                state = update_component_state(state, None, **self.update_components)

            with open(f"./{out_dir}/{hash}.json", "w") as json_file:
                json.dump(state, json_file, indent=4)
        return input
