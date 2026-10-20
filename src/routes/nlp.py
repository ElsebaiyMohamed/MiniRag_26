import json
import logging

from fastapi import APIRouter, status, Request
from fastapi.responses import JSONResponse

from controllers import NLPController
from models import ProjectDataModel, AssetDataModel, ChunkDataModel
from models.enums import ResponseSignal, AssetType, AssetStatus
from models.schemas import PushRequest, SearchRequest

log_it = logging.getLogger('uvicorn.error')

nlp_router = APIRouter(prefix="/api/v1/nlp",
                        tags=["v1", "nlp"]
                        )

@nlp_router.post('/index/push/{project_id}')
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

    asset_model = await AssetDataModel.create_instance(db_client=request.app.db_client)

    all_project_files = await asset_model.get_all_project_assets(
        asset_project_id=project.project_id, asset_type=AssetType.FILE.value
    )

    total_project_files_num = len(all_project_files)
    if not total_project_files_num:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"signal": ResponseSignal.NO_FILES_ERROR.value},
        )

    chunk_model: ChunkDataModel = await ChunkDataModel.create_instance(
        db_client=request.app.db_client)
    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client
    )

    if push_request.do_reset:
        log_it.info("reset all embedding at project")
        for dummy_asset in all_project_files:
            if dummy_asset.asset_status == AssetStatus.INDEXED.value:
                await asset_model.set_asset_status(dummy_asset.asset_id, AssetStatus.CHUNKED.value)
                dummy_asset.asset_status = AssetStatus.CHUNKED.value
        no_deleted = await nlp_controller.reset_vectordb_collection(project)
        project_files = [a for a in all_project_files if a.asset_status == AssetStatus.CHUNKED.value]
    else:
        project_files = [
            asset for asset in all_project_files
            if asset.asset_status == AssetStatus.CHUNKED.value
        ]

    index_status = {
        'project_status_before_run':{
        'total_files': len(all_project_files),
        'uploaded_files': len([a for a in all_project_files if a.asset_status == AssetStatus.UPLOADED.value]),
        'chunked_files': len(project_files),
        'indexed_files': len([a for a in all_project_files if a.asset_status == AssetStatus.INDEXED.value]),
        },
        'call_status':{
        'file_success': 0,
        'file_failed': 0,
        'chunk_success': 0,
        'chunk_failed': 0
        }
    }
    if (index_status['project_status_before_run']['chunked_files'] == 0 and
            index_status['project_status_before_run']['uploaded_files'] == 0):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                'signal': ResponseSignal.NO_FILES_TO_BE_INDEXED.value,
                'insertion_status': index_status
            }
        )
    if (index_status['project_status_before_run']['chunked_files'] == 0 and
            index_status['project_status_before_run']['uploaded_files'] > 0):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                'signal': ResponseSignal.FILES_NEED_CHUNKING.value,
                'insertion_status': index_status
            }
        )




    for asset in project_files:
        has_records = True
        page_no = 1
        chunks_insertion_status = {
                'success': 0,
                'failed': 0
            }

        while has_records:
            page_chunks = await chunk_model.get_project_asset_chunks(
                asset_id=asset.asset_id, page_no=page_no)
            if not page_chunks or len(page_chunks) == 0:
                has_records = False
                break
            page_no += 1

            insertion_status = await nlp_controller.index2vectordb(
                project=project,
                chunks=page_chunks,
                do_reset=False
            )
            chunks_insertion_status = {key: chunks_insertion_status[key] + insertion_status[key] for key in chunks_insertion_status.keys()}

        if chunks_insertion_status['failed'] > 0 or chunks_insertion_status[
            'success'] == 0:
            log_it.error(f"file {asset.asset_name} failed to indexed ")
            index_status['call_status']['file_failed'] += 1
            index_status['call_status']['chunk_failed'] += chunks_insertion_status[
                'failed'] + chunks_insertion_status[
                'success']
            _ = await nlp_controller.reset_vectordb_collection_asset_vectors(
                project=project, asset=asset)
        else:
            await asset_model.set_asset_status(asset.asset_id,
                                            AssetStatus.INDEXED.value)
            index_status['call_status']['file_success'] += 1
            index_status['call_status']['chunk_success'] += chunks_insertion_status['success']
            index_status['call_status']['chunk_failed'] += chunks_insertion_status['failed']



    if index_status['call_status']['file_success'] == 0:
        log_it.error(ResponseSignal.INSERT_INTO_VECTORDB_ERROR.value)

        return JSONResponse(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            content={
                                'signal': ResponseSignal.INSERT_INTO_VECTORDB_ERROR.value,
                                'insertion_status': index_status
                            }
                        )


    return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                'signal': ResponseSignal.INSERT_INTO_VECTOR_DATABASE_SUCCESS.value,
                'insertion_status': index_status
            }
        )


@nlp_router.get('/index/info/{project_id}')
async def get_project_info(request: Request, project_id: int):

    project_model = await ProjectDataModel.create_instance(db_client=request.app.db_client)

    project = await project_model.get_project(project_id=project_id)




    if project is None:
        return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        'project_id': project_id,
                        'signal': ResponseSignal.PROJECT_NOT_FOUND.value
                    }
                )




    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client
    )

    collection_info = await nlp_controller.get_vectordb_collection_info(project=project)
    if collection_info is None:
        log_it.error(ResponseSignal.VECTORDB_COLLECTION_INFO_NOT_FOUND.value)
        return JSONResponse(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            content={
                                'signal': ResponseSignal.VECTORDB_COLLECTION_INFO_NOT_FOUND.value,
                            }
                        )
    collection_info = json.loads(
        json.dumps(collection_info, default=lambda x: x.__dict__)
    )

    return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                'signal': ResponseSignal.VECTORDB_COLLECTION_INFO_RETRIEVED.value,
                'collection_info': collection_info
            }
        )



@nlp_router.post('/index/search/{project_id}')
async def index_search(request: Request, project_id: int, search_request: SearchRequest):

    project_model = await ProjectDataModel.create_instance(db_client=request.app.db_client)

    project = await project_model.get_project(project_id=project_id)


    if project is None:
        return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        'project_id': project_id,
                        'signal': ResponseSignal.PROJECT_NOT_FOUND.value
                    }
                )


    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
    )

    result = await nlp_controller.search_vector_db_collection(
        project=project,
        text=search_request.text,
        limit=search_request.limit
    )
    if result:

        return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    'signal': ResponseSignal.VECTORDB_SEARCH_SUCCESS.value,
                    'result': [r.dict() for r in result]
                }
            )
    return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        'signal': ResponseSignal.VECTORDB_SEARCH_ERROR.value,
                    }
                )



@nlp_router.post('/index/answer/{project_id}')
async def index_answer(request: Request, project_id: int, search_request: SearchRequest):

    project_model = await ProjectDataModel.create_instance(db_client=request.app.db_client)

    project = await project_model.get_project(project_id=project_id)


    if project is None:
        return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        'project_id': project_id,
                        'signal': ResponseSignal.PROJECT_NOT_FOUND.value
                    }
                )


    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser
    )

    answer, full_prompt, chat_history = await nlp_controller.answer_rag_question(
        project=project,
        query=search_request.text,
        limit=search_request.limit
    )
    if answer:

        return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    'signal': ResponseSignal.RAG_ANSWER_SUCCESS.value,
                    'answer': answer,
                    'full_prompt': full_prompt,
                    'chat_history': chat_history
                }
            )
    return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        'signal': ResponseSignal.RAG_ANSWER_ERROR.value,
                    }
                )

