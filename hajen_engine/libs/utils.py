from multiprocessing import shared_memory
import json
import struct

async def get_env_data():
    """
    Gets env_data from shared_memory and should be properly handling the memory reading
    """
    shm = shared_memory.SharedMemory(name='env_data')
    try:
        size = struct.unpack('Q', shm.buf[:8])[0]
        return json.loads(bytes(shm.buf[8:8 + size]).decode('utf-8'))
    finally:
        shm.close()
