========
Poor BMC
========

Hacked virtual_bmc for controlling instances via cheap PDUs & grub

Installation
------------

.. code-block:: bash

  pip install poorbmc

Supported IPMI commands
-----------------------

.. code-block:: bash

  # Power the virtual machine on, off, graceful off, NMI and reset
  ipmitool -I lanplus -U admin -P password -H 127.0.0.1 power on|off|soft|diag|reset

  # Check the power status
  ipmitool -I lanplus -U admin -P password -H 127.0.0.1 power status

  # Set the boot device to network, hd or cdrom
  ipmitool -I lanplus -U admin -P password -H 127.0.0.1 chassis bootdev pxe|disk|cdrom

  # Get the current boot device
  ipmitool -I lanplus -U admin -P password -H 127.0.0.1 chassis bootparam get 5


.. Change things from this point on

