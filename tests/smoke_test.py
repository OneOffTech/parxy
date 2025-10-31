"""Check that basic features work before publishing on Pypi

Catch cases where e.g. files are missing so the import doesn't work. It is
recommended to check that e.g. assets are included."""

from parxy_core.facade import Parxy
from parxy_core.drivers import PyMuPdfDriver

driver = Parxy.driver()
if isinstance(driver, PyMuPdfDriver):
    print('Smoke test succeeded') # noqa: T201
else:
    raise RuntimeError('Failed to obtain PyMuPdfDriver')
