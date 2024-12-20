"""
This module contains the OutputStream class.
"""

import asyncio
import logging
import time
import uuid
from collections import defaultdict
from typing import Any, Dict, Type

from pydantic import BaseModel
from pykka import ActorProxy, ActorRegistry

from llmstack.common.blocks.base.schema import StrEnum
from llmstack.play.messages import (
    ContentData,
    ContentStreamChunkData,
    Error,
    ErrorsData,
    Message,
    MessageType,
)

__all__ = ["OutputStream"]

logger = logging.getLogger(__name__)


def stitch_model_objects(obj1: Any, obj2: Any) -> Any:
    """Stitch two objects together.

    Args:
      obj1: The first object (could be a BaseModel instance, dict, or list).
      obj2: The second object (could be a BaseModel instance, dict, or list).

    Returns:
      The stitched object.
    """
    if obj1 is None:
        return obj2
    if obj2 is None:
        return obj1

    # If both objects are BaseModels and the same type, stitch the fields
    if isinstance(obj1, BaseModel) and isinstance(obj2, BaseModel) and type(obj1) == type(obj2):  # noqa: E721
        stitched_obj = obj1.model_copy()
        for field in obj1.model_fields:
            setattr(
                stitched_obj,
                field,
                stitch_model_objects(getattr(obj1, field), getattr(obj2, field)),
            )
        return stitched_obj

    def stitch_fields(
        obj1_fields: Dict[str, Any],
        obj2_fields: Dict[str, Any],
    ) -> Dict[str, Any]:
        stitched_fields = defaultdict(Any)
        for field in set(obj1_fields).union(obj2_fields):
            stitched_fields[field] = stitch_model_objects(
                obj1_fields.get(field, None),
                obj2_fields.get(field, None),
            )
        return dict(stitched_fields)

    if isinstance(obj1, dict) and isinstance(obj2, dict):
        return stitch_fields(obj1, obj2)

    elif isinstance(obj1, list) and isinstance(obj2, list):
        if not obj1:
            return obj2
        if not obj2:
            return obj1

        stitched_obj = []
        max_length = max(len(obj1), len(obj2))
        for i in range(max_length):
            item1 = obj1[i] if i < len(obj1) else None
            item2 = obj2[i] if i < len(obj2) else None
            stitched_obj.append(stitch_model_objects(item1, item2))
        return stitched_obj

    elif isinstance(obj1, StrEnum) and isinstance(obj2, StrEnum):
        return obj1 if obj1.value == obj2.value else obj2

    elif isinstance(obj1, str) and isinstance(obj2, str):
        return obj1 + obj2

    else:
        return obj2 if obj2 else obj1


class OutputStream:
    """
    OutputStream class.
    """

    def __init__(
        self,
        stream_id: str = None,
        coordinator_urn: str = None,
        output_cls: Type = None,
        bookkeeping_queue: asyncio.Queue = None,
    ) -> None:
        """
        Initializes the OutputStream class.
        """
        self._message_id = str(uuid.uuid4())
        self._data = None
        self._output_cls = output_cls
        self._stream_id = stream_id
        self._coordinator_urn = coordinator_urn
        self._coordinator_proxy = None
        self._bookkeeping_queue = bookkeeping_queue

    @property
    def _coordinator(self) -> ActorProxy:
        """
        Returns the coordinator.
        """
        if not self._coordinator_proxy:
            try:
                self._coordinator_proxy = ActorRegistry.get_by_urn(
                    self._coordinator_urn,
                ).proxy()
            except Exception as e:
                logger.error(f"Failed to get coordinator proxy for {self._coordinator_urn}: {e}")

        return self._coordinator_proxy

    async def write(self, data: Any) -> None:
        """
        Stitches fields from data to _data.
        """

        self._coordinator.relay(
            Message(
                id=self._message_id,
                type=MessageType.CONTENT_STREAM_CHUNK,
                sender=self._stream_id,
                receiver="coordinator",
                data=ContentStreamChunkData(
                    chunk=(
                        data.model_dump()
                        if isinstance(
                            data,
                            BaseModel,
                        )
                        else data
                    ),
                ),
            ),
        )

        if self._data is None:
            self._data = (
                data.model_dump()
                if isinstance(
                    data,
                    BaseModel,
                )
                else data
            )
        else:
            self._data = stitch_model_objects(self._data, data)
        await asyncio.sleep(0.0001)

    async def write_raw(self, message: Message) -> None:
        """
        Writes raw message to the output stream.
        """
        response = self._coordinator.relay(message)

        await asyncio.sleep(0.0001)

        return response

    def get_data(self) -> BaseModel:
        """
        Returns the data.
        """
        return self._data

    def finalize(
        self,
    ) -> BaseModel:
        """
        Closes the output stream and returns stitched data.
        """
        output = (
            self._data if not self._output_cls or isinstance(self._data, BaseModel) else self._output_cls(**self._data)
        )
        self._data = None

        # Send the end message
        self._coordinator.relay(
            Message(
                id=self._message_id,
                type=MessageType.CONTENT_STREAM_END,
                sender=self._stream_id,
                receiver="coordinator",
            ),
        )

        # Send the final data

        self._coordinator.relay(
            Message(
                id=self._message_id,
                type=MessageType.CONTENT,
                sender=self._stream_id,
                receiver="coordinator",
                data=ContentData(
                    content=(
                        output.model_dump()
                        if isinstance(
                            output,
                            BaseModel,
                        )
                        else output
                    ),
                ),
            ),
        )

        return output

    def bookkeep(self, data: BaseModel) -> None:
        """
        Bookkeeping entry.
        """
        timestamp = time.time()
        timestamped_data = {**data.model_dump(), "timestamp": timestamp}

        self._bookkeeping_queue.put_nowait((self._stream_id, timestamped_data))

    def error(self, error: Exception) -> None:
        """
        Error entry.
        """
        self._coordinator.relay(
            Message(
                type=MessageType.ERRORS,
                sender=self._stream_id,
                receiver="coordinator",
                data=ErrorsData(errors=[Error(message=str(error))]),
            ),
        )
