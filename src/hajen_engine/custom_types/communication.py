from typing import TypedDict

class Packet(TypedDict, total=True):
    source: str
    job_id: str
    data: dict
    destination: str
    result: str
    datatype: str
    requestid: str

PacketWithHeaders = tuple[str, int, Packet]
