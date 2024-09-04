
# Known issues:
    # - queues lock up
    # - inefficient use of queues
    # - KeyboardInterrupt isn't handled properly across all threads
    # - Packet type isn't well designed
    # - processes and drivers should really be combined
    # - use of inheritance when composition is better
    # - propogation of tracebacks doesn't work well
    # - Processes and drivers shouldn't be seperated
    # - Things don't seem to transfer to queues like they should, might be related to queues locking up
