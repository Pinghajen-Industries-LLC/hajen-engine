
This project is currently undergoing a rewrite
# TODO:
    - Fix queues
    - Comment code better
    - testing suite
    - Use shared_memory for all env_data reads
    - have task that updates shared_memory on env_data change

# Known issues:
    - tasks can't communicate properly yet
    - add a check for if a process or driver is enabled
    - inefficient use of queues
    - KeyboardInterrupt isn't handled properly across all threads
    - use of inheritance when composition is better
    - Processes and drivers should be seperate
    - despaghettify code
    - A lot of busy waiting that could probably be replaced with callbacks
