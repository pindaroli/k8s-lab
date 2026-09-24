#!/bin/sh
# Exit 1: FreeRADIUS treats this as "session still online", so Simultaneous-Use
# counts the open SQLite row until Accounting-Stop.
exit 1
