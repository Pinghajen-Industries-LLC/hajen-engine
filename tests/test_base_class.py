import asyncio
from copy import deepcopy
from src.classes.classes import BaseClass
import json
import pytest

from src.custom_types.communication import PacketWithHeaders

"""
Tests for the BaseClass class
"""

@pytest.mark.asyncio
async def test_base_class_init():
    """
    Tests that the class can be initialized
    """
    base_class = BaseClass()

    assert isinstance(base_class, BaseClass)
    assert base_class.source == ""
    assert base_class.class_type == "base_class"

@pytest.mark.asyncio
async def test__read_queue():
    """
    Tests that self._read_queue functions properly
    """
    base_class = BaseClass()

    queue = await base_class._read_queue()

    assert queue == []

    test_packet_with_headers: PacketWithHeaders = (
                "test",
                0,
                {
                "source": "test_source",
                "data": {
                    "test_data": "test_data",
                    },
                "datatype": "test_datatype",
                "destination": "test_destination",
                "job_id": "test_job_id",
                "requestid": "test_requestid",
                "result": "test_result",
                }
            , )
    base_class.receive_queue.put(test_packet_with_headers)

    while base_class.receive_queue.empty():
        await asyncio.sleep(1)

    queue = await base_class._read_queue()

    assert queue == [test_packet_with_headers]

    base_class.receive_queue.put(test_packet_with_headers)
    base_class.receive_queue.put(test_packet_with_headers)

    while base_class.receive_queue.empty():
        await asyncio.sleep(1)
    queue = await base_class._read_queue()

    assert queue == [test_packet_with_headers, test_packet_with_headers]

@pytest.mark.asyncio
async def test_logger():
    """
    TODO: Leaving this empty but will have to do this if self.logger gets used
    """
    pass

@pytest.mark.asyncio
async def test_main():
    """
    TODO: Write this
    """
    pass

@pytest.mark.asyncio
async def test_run():
    """
    TODO: Write this
    """
    pass

@pytest.mark.asyncio
async def test_get_request_id():
    """

    """
    base_class = BaseClass()

    assert base_class.uid == 0
    request_id = await base_class.get_request_id("test")
    split_request_id = request_id.split(".")
    assert isinstance(request_id, str)
    assert split_request_id[0] == "base_class"
    assert split_request_id[1] == "test"
    assert split_request_id[2] == "1"
    assert isinstance(int(split_request_id[3]), int)
    assert base_class.uid == 1
    request_id = await base_class.get_request_id("test")
    split_request_id = request_id.split(".")
    assert isinstance(request_id, str)
    assert split_request_id[0] == "base_class"
    assert split_request_id[1] == "test"
    assert split_request_id[2] == "2"
    assert isinstance(int(split_request_id[3]), int)
    assert base_class.uid == 2

@pytest.mark.asyncio
async def test__send_packet_list():
    """

    """
    base_class = BaseClass()

    test_packet_with_headers: PacketWithHeaders = (
                "test",
                0,
                {
                "source": "test_source",
                "data": {
                    "test_data": "test_data",
                    },
                "datatype": "test_datatype",
                "destination": "test_destination",
                "job_id": "test_job_id",
                "requestid": "test_requestid",
                "result": "test_result",
                }
            , )
    packet_list: list[PacketWithHeaders] = [deepcopy(test_packet_with_headers) for _ in range(10)]

    result = await base_class._send_packet_list([])
    assert result == {'result': '1', 'error': 'packet_list was empty'}
    result = await base_class._send_packet_list(packet_list)
    assert result == {'result': '0'}
    result = await base_class._send_packet_list([('1234')])
    for index, value in enumerate(result):
        match value:
            case 'result':
                assert result[value] == '1'
            case 'message':
                assert result[value] == 'Packet is not of type list[PacketWithHeaders].'
            case 'error':
                assert isinstance(result[value], str)
    result = await base_class._send_packet_list(('1234'))
    assert result == {'result': '1', 'error': 'Packet is not of type list[].'}

@pytest.mark.asyncio
async def test__send_packet():
    """

    """
    base_class = BaseClass()

    test_packet_with_headers: PacketWithHeaders = (
                "test_destination",
                0,
                {
                "source": "test_source",
                "data": {
                    "test_data": "test_data",
                    },
                "datatype": "test_datatype",
                "destination": "test_destination",
                "job_id": "test_job_id",
                "requestid": "test_requestid",
                "result": "test_result",
                }
            , )
    packet_list: list[PacketWithHeaders] = [deepcopy(test_packet_with_headers) for _ in range(10)]

    result = await base_class._send_packet(
            priority=test_packet_with_headers[1],
            destination=test_packet_with_headers[2]['destination'],
            source=test_packet_with_headers[2]['source'],
            data=test_packet_with_headers[2]['data'],
            datatype=test_packet_with_headers[2]['datatype'],
            job_id=test_packet_with_headers[2]['job_id'],
            requestid=test_packet_with_headers[2]["requestid"],
            result=test_packet_with_headers[2]['result'],
            )
    assert result == None
    result = base_class.send_queue.get()
    assert result == test_packet_with_headers

@pytest.mark.asyncio
async def test_schedule_task():
    """

    """
    base_class = BaseClass()

    with pytest.raises(NotImplementedError):
        await base_class.schedule_task('1234')

@pytest.mark.asyncio
async def test_shutdown():
    """

    """
    base_class = BaseClass()

    with pytest.raises(NotImplementedError):
        await base_class.shutdown()
