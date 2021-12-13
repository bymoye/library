from blacksheep.messages import Response
from blacksheep.contents import Content
import orjson
def res(status: int, context: str) -> Response:
    return Response(
        status=status,
        content=Content(
            b'application/json',
            orjson.dumps({
                "status": status,
                "message": f'{context}'
                })
        )
    )
    
def data_res(status:int,context: str|list) -> Response:
    return Response(
        status=status,
        content=Content(
            b'application/json',
            orjson.dumps({
                "status": status,
                "data": context
                })
        )
    )