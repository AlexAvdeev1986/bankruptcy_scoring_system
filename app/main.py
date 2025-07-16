from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import asyncio
import os
import csv
import logging
from datetime import datetime

# Импорт модулей
from .database import DatabaseManager
from .data_normalizer import DataNormalizer
from .external_parsers import ExternalParsers
from .scoring_engine import ScoringEngine
from .config import Config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(Config.LOG_DIR, Config.LOG_FILE)),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Модели запросов
class ScoringRequest(BaseModel):
    regions: List[str]
    min_debt: int = 250000
    exclude_bankrupt: bool = True
    exclude_no_debt: bool = False
    only_property: bool = False
    only_bank_mfo: bool = False
    only_court_orders: bool = False
    only_active_inn: bool = True

class ScoringStatus(BaseModel):
    status: str  # idle, running, completed, error
    progress: int
    message: str
    total_contacts: Optional[int] = None
    errors: Optional[List[str]] = None

# Глобальное состояние
scoring_status = ScoringStatus(
    status="idle",
    progress=0,
    message="Ready to start"
)

# Инициализация приложения
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Инициализация компонентов
db_manager = DatabaseManager()
normalizer = DataNormalizer()
scoring_engine = ScoringEngine()

# Обеспечиваем существование директорий
Config.ensure_directories()

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    logger.info("Application starting up...")
    await db_manager.init_database()
    logger.info("Application started")

@app.get("/")
async def read_root(request: Request):
    """Главная страница"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/start-scoring")
async def start_scoring(request: ScoringRequest, background_tasks: BackgroundTasks):
    """Запуск процесса скоринга"""
    global scoring_status
    
    if scoring_status.status == "running":
        raise HTTPException(status_code=400, detail="Scoring already in progress")
    
    # Сбрасываем статус
    scoring_status = ScoringStatus(
        status="running",
        progress=0,
        message="Scoring started..."
    )
    
    # Запускаем в фоне
    background_tasks.add_task(run_scoring_process, request)
    
    return {"status": "started", "message": "Scoring process started"}

@app.get("/api/status")
async def get_status():
    """Получение текущего статуса скоринга"""
    return scoring_status

@app.get("/api/download-results")
async def download_results():
    """Скачивание результатов"""
    file_path = os.path.join(Config.EXPORT_DIR, "scoring_ready.csv")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Results file not found")
    return FileResponse(file_path, filename="scoring_ready.csv")

@app.get("/api/download-logs")
async def download_logs():
    """Скачивание логов"""
    file_path = os.path.join(Config.LOG_DIR, Config.LOG_FILE)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Log file not found")
    return FileResponse(file_path, filename="scoring_logs.log")

async def run_scoring_process(request: ScoringRequest):
    """Основной процесс скоринга"""
    global scoring_status
    
    try:
        # Инициализация компонентов
        parsers = ExternalParsers()
        await parsers.__aenter__()
        
        # Шаг 1: Загрузка и нормализация данных
        scoring_status.progress = 10
        scoring_status.message = "Loading data..."
        raw_data = await normalizer.load_csv_files()
        normalized_data = await normalizer.normalize_data(raw_data)
        
        # Фильтрация по регионам
        filtered_data = await normalizer.filter_by_regions(normalized_data, request.regions)
        
        # Шаг 2: Обогащение данными
        scoring_status.progress = 30
        scoring_status.message = "Enriching with external data..."
        enriched_data = []
        
        total_items = len(filtered_data)
        for i, lead in enumerate(filtered_data):
            # Обновляем прогресс
            progress = 30 + int(40 * i / total_items)
            scoring_status.progress = progress
            scoring_status.message = f"Processing {i+1}/{total_items} leads"
            
            # Сбор данных из внешних источников
            try:
                # Получаем данные из всех источников
                fssp_data = await parsers.get_fssp_data(lead)
                fedresurs_data = await parsers.get_fedresurs_data(lead)
                rosreestr_data = await parsers.get_rosreestr_data(lead)
                court_data = await parsers.get_court_data(lead)
                inn_data = await parsers.check_inn_status(lead.get('inn', ''))
                
                # Объединяем все данные
                enriched_lead = {
                    **lead,
                    **fssp_data,
                    **fedresurs_data,
                    **rosreestr_data,
                    **court_data,
                    **inn_data
                }
                enriched_data.append(enriched_lead)
            except Exception as e:
                logger.error(f"Error enriching lead {lead.get('lead_id')}: {e}")
                enriched_data.append(lead)
        
        # Шаг 3: Расчет скоринга
        scoring_status.progress = 80
        scoring_status.message = "Calculating scores..."
        scored_data = []
        for lead in enriched_data:
            try:
                scored_lead = await scoring_engine.calculate_score(lead, request.dict())
                scored_data.append(scored_lead)
            except Exception as e:
                logger.error(f"Error scoring lead {lead.get('lead_id')}: {e}")
                scored_data.append({
                    **lead,
                    'score': 0,
                    'is_target': 0,
                    'reason_1': 'Error'
                })
        
        # Фильтрация по is_target и score
        target_leads = [lead for lead in scored_data if lead['is_target'] == 1 and lead['score'] >= 50]
        target_leads.sort(key=lambda x: x['score'], reverse=True)
        
        # Шаг 4: Сохранение результатов
        scoring_status.progress = 90
        scoring_status.message = "Saving results..."
        save_results_to_csv(target_leads)
        
        # Сохраняем в базу данных
        await db_manager.save_leads(normalized_data)
        await db_manager.save_scoring_results(target_leads)
        
        # Обновляем статус
        scoring_status = ScoringStatus(
            status="completed",
            progress=100,
            message=f"Scoring completed. Found {len(target_leads)} target contacts",
            total_contacts=len(target_leads)
        )
        
        await parsers.__aexit__(None, None, None)
        
    except Exception as e:
        logger.error(f"Scoring process error: {str(e)}", exc_info=True)
        scoring_status = ScoringStatus(
            status="error",
            progress=0,
            message="Scoring process failed",
            errors=[str(e)]
        )

def save_results_to_csv(results: List[Dict]):
    """Сохранение результатов в CSV файл"""
    file_path = os.path.join(Config.EXPORT_DIR, "scoring_ready.csv")
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'phone', 'fio', 'score', 'reason_1', 'reason_2', 'reason_3', 'is_target', 'group'
        ])
        writer.writeheader()
        for row in results:
            writer.writerow({
                'phone': row.get('phone', ''),
                'fio': row.get('fio', ''),
                'score': row.get('score', 0),
                'reason_1': row.get('reason_1', ''),
                'reason_2': row.get('reason_2', ''),
                'reason_3': row.get('reason_3', ''),
                'is_target': row.get('is_target', 0),
                'group': row.get('group', '')
            })
    logger.info(f"Saved {len(results)} records to {file_path}")
    