from typing import Any

AppLayout = list[dict[str, Any]]

def update_component_state(
    layout: list[dict[str, Any]], 
    updated: None | list[dict[str, Any]]=None, 
    **kwargs: dict[str, Any]
) -> list[dict[str, Any]]: 
    """
    Recursively updates values in a Dash app layout.

    Parameters:
        layout (list[dict[str, Any]]): The Dash app layout to be updated.
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
    if updated is None:
        updated = []

    for item in layout:
        props = item['props']

        children = props.get("children", None)
        if children and isinstance(children, list):
            props['children'] = update_component_state(children, None, **kwargs)

        id = props.get('id', '')
        if id not in kwargs:
            updated.append(item)
            continue

        props.update(kwargs[id])
        item['props'] = props
        updated.append(item)

    return updated
