import json
import logging

from fastapi import APIRouter, status, Request
from fastapi.responses import JSONResponse

from controllers import NLPController
from models import ProjectDataModel, AssetDataModel
from models.enums import ResponseSignal, AssetType
from models.schemas import PushRequest, SearchRequest


from application.use_cases.index_project import (
    IndexProject,
    IndexProjectCommand,
)
from infrastructure.adapters import (
    SqlAlchemyAssetIndexRepository,
    SqlAlchemyChunkRepository,
    LLMEmbedder,
    PgVectorStoreAdapter,
)

log_it = logging.getLogger("uvicorn.error")

nlp_router = APIRouter(prefix="/api/v1/nlp", tags=["v1", "nlp"])



@nlp_router.post("/index/push/{project_id}")
async def index_project(request: Request, project_id: int, push_request: PushRequest):
    project_model = await ProjectDataModel.create_instance(
        db_client=request.app.db_client
    )
    project = await project_model.get_project(project_id=project_id)

    if not project:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"signal": ResponseSignal.PROJECT_NOT_FOUND.value},
        )

    asset_model = await AssetDataModel.create_instance(
        db_client=request.app.db_client
    )
    all_project_files = await asset_model.get_all_project_assets(
        asset_project_id=project.project_id,
        asset_type=AssetType.FILE.value,
    )

    if not all_project_files:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"signal": ResponseSignal.NO_FILES_ERROR.value},
        )

    index_project_use_case = IndexProject(
        asset_repository=SqlAlchemyAssetIndexRepository(
            request.app.db_client
        ),
        chunk_repository=SqlAlchemyChunkRepository(
            request.app.db_client
        ),
        embedder=LLMEmbedder(request.app.embedding_client),
        vector_store=PgVectorStoreAdapter(request.app.vectordb_client),
    )

    result = await index_project_use_case.execute(
        IndexProjectCommand(
            project_id=project.project_id,
            do_reset=bool(push_request.do_reset),
            page_size=10,
        )
    )

    index_status = {
        "project_status_before_run": result.project_status_before_run,
        "call_status": result.call_status,
    }

    if result.outcome == "no_files":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"signal": ResponseSignal.NO_FILES_ERROR.value},
        )

    if result.outcome == "nothing_to_index":
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "signal": ResponseSignal.NO_FILES_TO_BE_INDEXED.value,
                "insertion_status": index_status,
            },
        )

    if result.outcome == "needs_chunking":
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "signal": ResponseSignal.FILES_NEED_CHUNKING.value,
                "insertion_status": index_status,
            },
        )

    if result.outcome in ("collection_error", "failed"):
        log_it.error(
            "Project %s indexing failed: %s",
            project.project_id,
            result.outcome,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.INSERT_INTO_VECTORDB_ERROR.value,
                "insertion_status": index_status,
            },
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "signal": ResponseSignal.INSERT_INTO_VECTOR_DATABASE_SUCCESS.value,
            "insertion_status": index_status,
        },
    )



@nlp_router.get("/index/info/{project_id}")
async def get_project_info(request: Request, project_id: int):
    project_model = await ProjectDataModel.create_instance(db_client=request.app.db_client)

    project = await project_model.get_project(project_id=project_id)

    if project is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"project_id": project_id,
                     "signal": ResponseSignal.PROJECT_NOT_FOUND.value},
        )

    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
    )

    collection_info = await nlp_controller.get_vectordb_collection_info(project=project)
    if collection_info is None:
        log_it.error(ResponseSignal.VECTORDB_COLLECTION_INFO_NOT_FOUND.value)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.VECTORDB_COLLECTION_INFO_NOT_FOUND.value,
            },
        )
    collection_info = json.loads(
        json.dumps(collection_info, default=lambda x: x.__dict__))

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"signal": ResponseSignal.VECTORDB_COLLECTION_INFO_RETRIEVED.value,
                 "collection_info": collection_info},
    )


@nlp_router.post("/index/search/{project_id}")
async def index_search(request: Request, project_id: int, search_request: SearchRequest):
    project_model = await ProjectDataModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project(project_id=project_id)

    if project is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"project_id": project_id,
                     "signal": ResponseSignal.PROJECT_NOT_FOUND.value},
        )

    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
    )

    result, embed_result = await nlp_controller.search_vector_db_collection(
        project=project, text=search_request.text, limit=search_request.limit
    )

    # Check if embedding failed upstream
    if embed_result and not embed_result.success:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "signal": (
                    ResponseSignal.EMBEDDING_GENERATION_ERROR.value
                    if hasattr(ResponseSignal, "EMBEDDING_GENERATION_ERROR")
                    else "EMBEDDING_GENERATION_ERROR"
                ),
                "error": embed_result.error_message,
                "telemetry": embed_result.dict(),
            },
        )

    if result is not False:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "signal": ResponseSignal.VECTORDB_SEARCH_SUCCESS.value,
                "result": [r.model_dump() for r in result],
                "telemetry": embed_result.model_dump() if embed_result else None,
            },
        )

    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "signal": ResponseSignal.VECTORDB_SEARCH_ERROR.value,
            "telemetry": embed_result.model_dump() if embed_result else None,
        },
    )


@nlp_router.post("/index/answer/{project_id}")
async def index_answer(request: Request, project_id: int, search_request: SearchRequest):
    project_model = await ProjectDataModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project(project_id=project_id)

    if project is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"project_id": project_id,
                     "signal": ResponseSignal.PROJECT_NOT_FOUND.value},
        )

    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
    )

    generation_result, embed_result, full_prompt, chat_history, error_msg = await nlp_controller.answer_rag_question(
        project=project, query=search_request.text, limit=search_request.limit
    )

    if embed_result and not embed_result.success:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "signal": "EMBEDDING_GENERATION_ERROR",
                "error": embed_result.error_message,
                "telemetry": embed_result.dict(),
            },
        )

    if generation_result:
        response_content = {
            "signal": ResponseSignal.RAG_ANSWER_SUCCESS.value,
            "answer": generation_result.content,
            # Extract the text string from LLMResult
            "telemetry": {
                "generation_metrics": generation_result.model_dump(exclude={"content"}),
                "embedding_metrics": embed_result.model_dump() if embed_result else None,
            },
        }

        if search_request.debug:
            response_content["full_prompt"] = full_prompt
            response_content["chat_history"] = chat_history

        return JSONResponse(status_code=status.HTTP_200_OK, content=response_content)

    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "signal": ResponseSignal.RAG_ANSWER_ERROR.value,
            "error": error_msg or "Failed to generate RAG answer",
            "telemetry": embed_result.dict() if embed_result else None,
        },
    )
