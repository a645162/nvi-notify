from html import escape

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.responses import RedirectResponse

app = FastAPI(
    title='FastAPI',
    description='FastAPI',
    version='1.0.0',
    docs_url='/docs',
    redoc_url='/redocs',
)
templates = Jinja2Templates(directory="templates")

from config.settings import GPU_BOARD_WEB_URL, SERVER_NAME

from feature.web.web_common import *

from feature.utils.logs import get_logger

logger = get_logger()
logger.info("FastAPI server is starting...")


@app.get("/nvitop_output")
def get_result():
    command_result = get_nvitop_result()
    return JSONResponse(
        content={"result": escape(command_result)},
        status_code=200,
        media_type="application/json",
    )


@app.post("/machine_user_message")
def machine_user_message(request: Request):
    final_data: dict = {
        "haveError": True,
        "isSucceed": False,
        "result": "error"
    }

    user_name = request.form.get('userName')
    content = request.form.get('content')

    if user_name and content:
        machine_user_message_backend(
            user_name=user_name,
            content=content,
        )
        final_data["haveError"] = False
        final_data["isSucceed"] = True
        final_data["result"] = "success"

    return JSONResponse(
        content=final_data,
        status_code=200,
        media_type="application/json",
    )


@app.get("/system_info")
def get_system_info():
    system_info: dict = get_system_info_dict()
    return JSONResponse(
        content=system_info,
        status_code=200,
        media_type="application/json",
    )


@app.get("/gpu_count")
def get_gpu_count():
    return JSONResponse(
        content={"result": get_gpu_count_backend()},
        status_code=200,
        media_type="application/json",
    )


@app.get("/gpu_usage_info")
def get_gpu_usage(request: Request):
    gpu_index = request.query_params.get("gpu_index", None)
    if gpu_index is None or not gpu_index.isdigit() or int(gpu_index) > get_gpu_count_backend():
        return JSONResponse(
            content={"result": "Invalid GPU Index(gpu_index)."},
            status_code=400,
            media_type="application/json",
        )

    response_gpu_usage = get_gpu_usage_dict(gpu_index=int(gpu_index))

    return JSONResponse(
        content=response_gpu_usage,
        status_code=200,
        media_type="application/json",
    )


@app.get("/gpu_task_info")
def get_gpu_task(request: Request):
    gpu_index = request.query_params.get("gpu_index", None)

    if gpu_index is None or not gpu_index.isdigit() or int(gpu_index) > get_gpu_count_backend():
        return JSONResponse(
            content={"result": "Invalid GPU Index(gpu_index)."},
            status_code=400,
            media_type="application/json",
        )

    response_gpu_task = get_gpu_task_dict_list(gpu_index=int(gpu_index))

    return JSONResponse(
        content=response_gpu_task,
        status_code=200,
        media_type="application/json",
    )
