import sys

from harlequin.adapter import HarlequinAdapter
from harlequin_adbc.adapter import HarlequinAdbcAdapter

if sys.version_info < (3, 10):
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points


def test_plugin_discovery() -> None:
    PLUGIN_NAME = "adbc"
    eps = entry_points(group="harlequin.adapter")
    assert eps[PLUGIN_NAME]
    adapter_cls = eps[PLUGIN_NAME].load()  # type: ignore
    assert issubclass(adapter_cls, HarlequinAdapter)
    assert adapter_cls == HarlequinAdbcAdapter
