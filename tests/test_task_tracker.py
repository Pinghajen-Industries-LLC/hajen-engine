import asyncio
from src.classes.classes import TaskTracker
import json
import pytest

with open('data/environment.json', 'r') as file:
    env_data = json.load(file)


@pytest.mark.asyncio
async def test_task_tracker():
    task_tracker = TaskTracker()
    assert isinstance(task_tracker.running_tasks, dict)


@pytest.mark.asyncio
async def test_stop_task():
    task_tracker = TaskTracker()
    with pytest.raises(NotImplementedError):
        task_tracker.stop_task('1234')


@pytest.mark.asyncio
async def test__run_scheduled_task():
    task_tracker = TaskTracker()
    with pytest.raises(DeprecationWarning):
        await task_tracker._run_scheduled_task('1234')


@pytest.mark.asyncio
async def test_set_task_running_new_key_1():
    task_tracker = TaskTracker()
    task_tracker.set_task_running(key='1234')
    assert task_tracker.running_tasks != {}
    assert '1234' in task_tracker.running_tasks
    assert task_tracker.running_tasks['1234']['running'] is True
    assert isinstance(task_tracker.running_tasks['1234']['last_run'], float)
    assert task_tracker.running_tasks['1234']['cooldown'] == 60.0
    assert task_tracker.running_tasks['1234']['task'] is None


@pytest.mark.asyncio
async def test_set_task_running_new_key_2():
    task_tracker = TaskTracker()
    task_tracker.set_task_running(key='1234', running=False)
    assert task_tracker.running_tasks != {}
    assert '1234' in task_tracker.running_tasks
    assert task_tracker.running_tasks['1234']['running'] is False


@pytest.mark.asyncio
async def test_set_task_running_new_key_3():
    task_tracker = TaskTracker()
    task_tracker.set_task_running(key='1234', cooldown=61)
    assert task_tracker.running_tasks != {}
    assert '1234' in task_tracker.running_tasks
    assert isinstance(task_tracker.running_tasks['1234']['last_run'], float)
    assert task_tracker.running_tasks['1234']['cooldown'] == 61


@pytest.mark.asyncio
async def test_set_task_running_new_key_4():
    task_tracker = TaskTracker()
    task_tracker.set_task_running(key='1234',
                                  task=asyncio.create_task(asyncio.sleep(1)))
    assert task_tracker.running_tasks != {}
    assert '1234' in task_tracker.running_tasks
    assert task_tracker.running_tasks['1234']['task'] is not None
    task_tracker.running_tasks['1234']['task'].cancel()


@pytest.mark.asyncio
async def test_set_task_running_existing_key_1():
    task_tracker = TaskTracker()
    task_tracker.set_task_running(key='1234')
    task_tracker.set_task_running(key='1234')
    assert task_tracker.running_tasks != {}
    assert '1234' in task_tracker.running_tasks
    assert task_tracker.running_tasks['1234']['running'] is True
    assert isinstance(task_tracker.running_tasks['1234']['last_run'], float)
    assert task_tracker.running_tasks['1234']['cooldown'] == 60.0
    assert task_tracker.running_tasks['1234']['task'] is None


@pytest.mark.asyncio
async def test_set_task_running_existing_key_2():
    task_tracker = TaskTracker()
    task_tracker.set_task_running(key='1234')
    task_tracker.set_task_running(key='1234', running=False)
    assert task_tracker.running_tasks != {}
    assert '1234' in task_tracker.running_tasks
    assert task_tracker.running_tasks['1234']['running'] is False


@pytest.mark.asyncio
async def test_set_task_running_existing_key_3():
    task_tracker = TaskTracker()
    task_tracker.set_task_running(key='1234')
    task_tracker.set_task_running(key='1234', cooldown=61,
                                  update_cooldown=True)
    assert task_tracker.running_tasks != {}
    assert '1234' in task_tracker.running_tasks
    assert isinstance(task_tracker.running_tasks['1234']['last_run'], float)
    assert task_tracker.running_tasks['1234']['cooldown'] == 61


@pytest.mark.asyncio
async def test_set_task_running_existing_key_4():
    task_tracker = TaskTracker()
    task_tracker.set_task_running(key='1234')
    task_tracker.set_task_running(key='1234',
                                  task=asyncio.create_task(asyncio.sleep(1)),
                                  update_task=True)
    assert task_tracker.running_tasks != {}
    assert '1234' in task_tracker.running_tasks
    assert task_tracker.running_tasks['1234']['task'] is not None
    task_tracker.running_tasks['1234']['task'].cancel()

# TODO: Add tests for get_tasks and for testing get_tasks_callback


# @pytest.mark.asyncio
# async def test_get_tasks_callback():
    # task_tracker = TaskTracker()
    # task_tracker.set_task_running(key='1234',
                                  # task=asyncio.create_task(asyncio.sleep(1)),
                                  # update_task=True)
    # assert task_tracker.running_tasks != {}
    # assert '1234' in task_tracker.running_tasks
    # assert task_tracker.running_tasks['1234']['task'] is not None
    # task_tracker.running_tasks['1234']['task'].

@pytest.mark.asyncio
async def test_get_tasks_empty():
    task_tracker = TaskTracker()
    result = task_tracker.get_tasks()
    assert result == {}


@pytest.mark.asyncio
async def test_get_tasks_all_tasks():
    task_tracker = TaskTracker()
    task_tracker.set_task_running(key='12354', running=True)
    task_tracker.set_task_running(key='1234', running=False)
    result = task_tracker.get_tasks(all_tasks=True)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_tasks_none_running():
    task_tracker = TaskTracker()
    task_tracker.set_task_running(key='1234', running=False)
    result = task_tracker.get_tasks(running=True)
    assert result == {}


@pytest.mark.asyncio
async def test_get_tasks_by_key():
    task_tracker = TaskTracker()
    task_tracker.set_task_running(key='12354', running=False)
    task_tracker.set_task_running(key='1234', running=False)
    result = task_tracker.get_tasks(key='1234')
    assert len(result) == 1


@pytest.mark.asyncio
async def test_get_tasks_on_cooldown():
    task_tracker = TaskTracker()
    task_tracker.set_task_running(key='1234', running=True, cooldown=10000,
                                  update_last_run=True)
    result = task_tracker.get_tasks()
    assert result == {}


@pytest.mark.asyncio
async def test_get_tasks_key_on_cooldown():
    task_tracker = TaskTracker()
    task_tracker.set_task_running(key='1234', running=True, cooldown=10000,
                                  update_last_run=True)
    result = task_tracker.get_tasks(key='1234')
    assert result == {}
