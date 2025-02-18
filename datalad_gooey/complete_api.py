# expensive import, we import from the full API
# to ensure getting all dataset methods from any extension
import datalad.api as dlapi

from datalad.interface.base import (
    Interface,
    get_interface_groups,
    load_interface,
)
from datalad.utils import get_wrapped_class

from .api_utils import get_cmd_displayname


# mapping of command interface classes to interface group titles
_cmd_group_lookup = {
    load_interface(cmd_spec): title
    for id_, title, cmds in sorted(get_interface_groups(), key=lambda x: x[0])
    for cmd_spec in cmds
}

# make each extension package its own group
from datalad.support.entrypoints import iter_entrypoints
for ename, _, (grp_descr, interfaces) in iter_entrypoints(
        'datalad.extensions', load=True):
    for intfspec in interfaces:
        # turn the interface spec into an instance
        intf = load_interface(intfspec[:2])
        _cmd_group_lookup[intf] = grp_descr


# all supported commands
api = {}
for mname in dir(dlapi):
    # iterate over all members of the Dataset class and find the
    # methods that are command interface callables
    # skip any private stuff
    if mname.startswith('_'):
        continue
    # right now, we are technically not able to handle GUI inception
    # and need to prevent launching multiple instances of this app.
    # we also do not want the internal gooey helpers
    if mname.startswith('gooey'):
        continue
    m = getattr(dlapi, mname)
    try:
        # if either of the following tests fails, this member is not
        # a datalad command
        cls = get_wrapped_class(m)
        assert issubclass(cls, Interface)
    except Exception:
        continue
    cmd_spec = dict(name=get_cmd_displayname({}, mname))
    cmd_group = _cmd_group_lookup.get(cls)
    if cmd_group:
        cmd_spec['group'] = cmd_group

    api[mname] = cmd_spec


# commands that operate on datasets, are attached as methods to the
# Dataset class
dataset_api = {
    name: api[name]
    for name in dir(dlapi.Dataset)
    if name in api
}

# commands that operate on any directory
directory_api = api
# commands that operate on directories in datasets
directory_in_ds_api = api
# commands that operate on any file
file_api = api
# commands that operate on any file in a dataset
file_in_ds_api = api
# command that operate on annex'ed files
annexed_file_api = api

# these generic parameters never make sense
exclude_parameters = set((
    # cmd execution wants a generator
    'return_type',
    # could be useful internally, but a user cannot chain commands
    'result_filter',
    # we cannot deal with non-dict results, and override any transform
    'result_xfm',
))

# generic name overrides
parameter_display_names = {}

# mapping of group name/title to sort index
api_group_order = {
    spec[1]: spec[0] for spec in get_interface_groups()
}
