import asyncio
import functools
import json
from typing import Dict, cast, Any, Union

from omi_async_http_client import AsyncHTTPClientBackend
from omi_async_http_client._exceptions import HTTPException
from omi_async_http_client._status_code import status_codes
from omi_async_http_client.async_http_client import ClientBackendResponse


class MockTestClientBackend(AsyncHTTPClientBackend):
    def __init__(self,
                 test_client=None,
                 event_loop=None
                 ) -> None:
        self.test_client = test_client
        self.event_loop = event_loop

    async def send(self, url, data, header, auth, timeout):
        raise NotImplementedError

    async def head(self, url, header, auth, timeout):
        future = asyncio.get_event_loop().run_in_executor(None,
                                                          functools.partial(
                                                              self.test_client.head,
                                                              str(url),
                                                              headers=header,
                                                              auth=None,
                                                              timeout=timeout
                                                          )
                                                          )
        response = await future
        return self.mock_prepare_response(response)

    async def get(self, url, data, header, auth, timeout) -> Union[Dict, ClientBackendResponse]:
        future = asyncio.get_event_loop().run_in_executor(None,
                                                          functools.partial(
                                                              self.test_client.get,
                                                              str(url),
                                                              data=json.dumps(data),
                                                              headers=header,
                                                              auth=None,
                                                              timeout=timeout
                                                          )
                                                          )
        response = await future
        return self.mock_prepare_response(response)

    async def put(self, url, data, header, auth, timeout) -> Union[Dict, ClientBackendResponse]:
        future = asyncio.get_event_loop().run_in_executor(None,
                                                          functools.partial(
                                                              self.test_client.put,
                                                              str(url),
                                                              data=json.dumps(data),
                                                              headers=header,
                                                              auth=None,
                                                              timeout=timeout
                                                          )
                                                          )
        response = await future
        return self.mock_prepare_response(response)

    async def post(self, url, data, header, auth, timeout) -> Union[Dict, ClientBackendResponse]:
        future = asyncio.get_event_loop().run_in_executor(None,
                                                          functools.partial(
                                                              self.test_client.post,
                                                              str(url),
                                                              data=json.dumps(data),
                                                              headers=header,
                                                              auth=None,
                                                              timeout=timeout
                                                          )
                                                          )
        response = await future
        return self.mock_prepare_response(response)

    async def delete(self, url, data, header, auth, timeout) -> Union[Dict, ClientBackendResponse]:
        future = asyncio.get_event_loop().run_in_executor(None,
                                                          functools.partial(
                                                              self.test_client.delete,
                                                              str(url),
                                                              data=json.dumps(data),
                                                              headers=header,
                                                              auth=None,
                                                              timeout=timeout
                                                          )
                                                          )
        response = await future
        return self.mock_prepare_response(response)

    def mock_prepare_response(self, response):
        # 获得状态代码，不需要等到response收到
        status = response.status_code
        # 服务端50x错误
        if status_codes.is_server_error(status):
            raise HTTPException(status_code=status)
        # 客户端40x错误
        elif status_codes.is_client_error(status):
            pass  # 跳过40x错误，由客户端程序处理
        # 转换为字典格式
        response_dict = cast(Dict[str, Any], response.json())
        # 解码过滤已收到的response
        self.mock_filter_received_response(status, response_dict)
        # 返回组合后的ClientBackendResponse对象
        return ClientBackendResponse(
            status_code=status, response=response_dict
        )

    def mock_filter_received_response(self, status, response_dict):
        """
        过滤来自远程API服务的相应，统一处理特定的错误
        status - int , 远程API服务HTTP响应的代码，
        response_dict - Dict, 远程API服务HTTP响应内容，在处理远程异常时，此处会获取response_dict中的code字段，
            生成HTTPAPIException

        Exceptions::
            HTTPAPIException，Resource API 调用发生业务性异常或错误时抛出，通常这类错误都会指定Trace_code,用于指定特定的处理逻辑
            HTTPException, Resource API 调用发生异常时抛出，通常这类错误都会指定status_code, 程序可以根据status_code进行处理
        """
        # TODO 按实际API设计Raise相应的异常信息
        if status in [
            status_codes.BAD_REQUEST,
            status_codes.UNAUTHORIZED,
            status_codes.FORBIDDEN,
            status_codes.NOT_FOUND,
            status_codes.CONFLICT,
        ]:
            trace_code = response_dict.get("code", 0)
            # 如果使用了预定义API TradeCode, 使用预定义的detail内容
            if trace_code > 0:
                raise HTTPException(
                    status_code=status,
                    trace_code=trace_code,
                    detail=status_codes.get_reason_phrase(status),
                )
            else:
                raise HTTPException(
                    status_code=status,
                    detail=status_codes.get_reason_phrase(status)
                )
        elif status == status_codes.UNPROCESSABLE_ENTITY:
            # HTTPValidationError
            raise HTTPException(status_code=status, detail=response_dict)
        elif status in [status_codes.OK, status_codes.CREATED, status_codes.ACCEPTED]:
            pass
        else:
            pass
