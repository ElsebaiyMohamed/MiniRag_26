import logging
import json


from fastapi import FastAPI, APIRouter, Depends, status, Request
from fastapi.responses import JSONResponse

from controllers import NLPController
from models.enums import ResponseSignal
from models.schemas import PushRequest, SearchRequest
from models import ProjectDataModel, ChunkDataModel 


log_it = logging.getLogger('uvicorn.error')

nlp_router = APIRouter(prefix="/api/v1/nlp",
                        tags=["v1", "nlp"]
                        )

@nlp_router.post('/index/push/{project_id}')
async def index_project(request: Request, project_id: str, push_request: PushRequest):
    
    project_model = await ProjectDataModel.create_instance(db_client=request.app.db_client)
    chunk_model = await ChunkDataModel.create_instance(db_client=request.app.db_client)
    
    project = await project_model.get_project_or_create_one(project_id=project_id)
    
    
    
    
    if not project:
        return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        'project_id': project_id,
                        'signal': ResponseSignal.PROJECT_NOT_FOUND.values
                    } 
                )
    
    
    
    
    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client, 
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client
    )
    

    if push_request.do_reset:
        nlp_controller.reset_vectordb_collection(project)
    has_records = True
    page_no = 1
    chunks = []
    
    while has_records:
        page_chunks = await chunk_model.get_project_chunks(project_id=project.id, page_no=page_no)

        if len(page_chunks):
            page_no += 1
        if not page_chunks or len(page_chunks) == 0:
            has_records = False
            break
        # chunks.extend(page_chunks)
        
        is_inserted = nlp_controller.index2vectordb(
            project=project,
            chunks=page_chunks,
            do_reset=False
        )

    if not is_inserted:
        log_it.error(ResponseSignal.INSERT_INTO_VECTORDB_ERROR.value)
        return JSONResponse(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            content={
                                'signal': ResponseSignal.INSERT_INTO_VECTORDB_ERROR.value
                            } 
                        )

    
    return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={ 
                'signal': ResponseSignal.INSERT_INTO_VECTOR_DATABASE_SUCCESS.value, 
            } 
        )


@nlp_router.get('/index/info/{project_id}')
async def get_project_info(request: Request, project_id: str):
    
    project_model = await ProjectDataModel.create_instance(db_client=request.app.db_client)
    
    project = await project_model.get_project_or_create_one(project_id=project_id)
    
    
    
    
    if not project:
        return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        'project_id': project_id,
                        'signal': ResponseSignal.PROJECT_NOT_FOUND.values
                    } 
                )
    
    
    
    
    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client, 
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client
    )
    
    collection_info = nlp_controller.get_vectordb_collection_info(project=project)
    
    collection_info = json.loads(
        json.dumps(collection_info, default=lambda x: x.__dict__)
    )
    
    return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={ 
                'signal': ResponseSignal.VECTORDB_COLLECTION_INFO_RETRIVED.value, 
                'collection_info': collection_info
            } 
        )



@nlp_router.post('/index/search/{project_id}')
async def index_search(request: Request, project_id: str, search_request: SearchRequest):
    
    project_model = await ProjectDataModel.create_instance(db_client=request.app.db_client)
    
    project = await project_model.get_project_or_create_one(project_id=project_id)
    

    if not project:
        return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        'project_id': project_id,
                        'signal': ResponseSignal.PROJECT_NOT_FOUND.values
                    } 
                )

    
    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client, 
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
    )
    
    result = nlp_controller.search_vector_db_collection(
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
async def index_answer(request: Request, project_id: str, search_request: SearchRequest):
    
    project_model = await ProjectDataModel.create_instance(db_client=request.app.db_client)
    
    project = await project_model.get_project_or_create_one(project_id=project_id)
    

    if not project:
        return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        'project_id': project_id,
                        'signal': ResponseSignal.PROJECT_NOT_FOUND.values
                    } 
                )

    
    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client, 
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser
    )
    
    answer, full_prompt, chat_history = nlp_controller.answer_rag_question(
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
        
