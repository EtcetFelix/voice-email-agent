# bot.py (or main.py)
import aiohttp
import asyncio
from loguru import logger

print("🚀 Starting Pipecat bot...")
print("⏳ Loading models and imports (20 seconds, first run only)\n")
logger.info("Loading Local Smart Turn Analyzer V3...")
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3

logger.info("✅ Local Smart Turn Analyzer V3 loaded")
logger.info("Loading Silero VAD model...")
from pipecat.audio.vad.silero import SileroVADAnalyzer

logger.info("✅ Silero VAD model loaded")

from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import LLMRunFrame

logger.info("Loading pipeline components...")
from pipecat.runner.run import RunnerArguments
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.runner.utils import create_transport
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.daily.transport import DailyParams

from pipecat.services.elevenlabs.tts import ElevenLabsTTSService as ElevenLabsTTS
from pipecat.services.elevenlabs.stt import ElevenLabsSTTService as ElevenLabsSTT

from pipecat.pipeline.pipeline import Pipeline

from voice_agent.config import settings
from voice_agent.database_service import Database
from voice_agent.embeddings.vector_store import EmailSearchStore
from voice_agent.etl_service import EmailETLService
from voice_agent.tools.email_tools import (
    EmailSearchTools,
    EMAIL_SEARCH_TOOLS,
    search_emails_handler,
    search_emails_by_sender_handler,
    get_recent_emails_handler
)

logger.info("✅ All components loaded successfully!")


# Global variables to hold initialized services
_database = None
_vector_store = None
_email_tools = None


async def initialize_email_services():
    """Initialize database, vector store, and run ETL before bot starts"""
    global _database, _vector_store, _email_tools
    
    logger.info("🔧 Initializing email services...")
    
    # Initialize database
    logger.info("📦 Initializing database...")
    _database = Database()
    await _database.init_db("./data/emails.db")
    logger.info("✅ Database initialized")
    
    # Initialize vector store
    logger.info("📦 Initializing vector store...")
    _vector_store = EmailSearchStore(persist_directory="./data/chroma_db")
    await _vector_store.init_store()
    logger.info("✅ Vector store initialized")
    
    # Run ETL to load emails
    logger.info("🔄 Running ETL to fetch and index emails...")
    etl_service = EmailETLService(
        database=_database,
        vector_store=_vector_store
    )
    
    try:
        grant_id = settings.NYLAS_EMAIL_ACCOUNT_GRANT_ID
        etl_result = await etl_service.run_etl(grant_id)
        logger.info(f"✅ ETL complete: {etl_result['emails_processed']} emails processed")
    except Exception as e:
        logger.error(f"❌ ETL failed: {e}")
        logger.warning("⚠️  Continuing with existing data...")
    
    # Create email tools
    _email_tools = EmailSearchTools(database=_database, vector_store=_vector_store)
    
    # Check counts
    email_count = await _database.get_email_count()
    vector_count = await _vector_store.get_count()
    logger.info(f"📧 {email_count} emails in database, {vector_count} emails in vector store")
    logger.info("✅ Email services fully initialized!")


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    logger.info("🎤 Starting bot with initialized services...")
    
    session = aiohttp.ClientSession()
    
    tts = ElevenLabsTTS(
        api_key=settings.ELEVENLABS_API_KEY,
        voice_id="Xb7hH8MSUJpSbSDYk0k2",    # Alice, British English
    )
    
    stt = ElevenLabsSTT(
        api_key=settings.ELEVENLABS_API_KEY,
        model_id="eleven_monolingual_v2_5",    # English
        aiohttp_session=session,
    )
    
    logger.info("🤖 Initializing LLM...")
    llm = OpenAILLMService(
        model="gpt-4o",
        api_key=settings.OPENAI_API_KEY
    )
    
    # Register function handlers using global email_tools
    logger.info("🔧 Registering email search functions...")
    llm.register_function(
        "search_emails",
        lambda params: search_emails_handler(params, _email_tools)
    )
    llm.register_function(
        "search_emails_by_sender",
        lambda params: search_emails_by_sender_handler(params, _email_tools)
    )
    llm.register_function(
        "get_recent_emails",
        lambda params: get_recent_emails_handler(params, _email_tools)
    )
    logger.info("✅ Email search functions registered")
    
    messages = [
        {
            "role": "system",
            "content": """You are a helpful email assistant named Alice. You can help users search and find information in their emails.

When users ask about their emails, use the available tools to search for relevant information. 
Be conversational and natural in your responses. Summarize email content clearly and concisely.

Available capabilities:
- Search emails by content or topic using search_emails
- Find emails from specific senders using search_emails_by_sender
- Get recent emails using get_recent_emails

Always confirm what you found and offer to provide more details if needed. Keep your responses brief and to the point.""",
        },
    ]
    
    # Create context with email search tools
    context = LLMContext(messages, tools=EMAIL_SEARCH_TOOLS)
    context_aggregator = LLMContextAggregatorPair(context)

    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))
    
    logger.info("🔗 Building pipeline...")
    pipeline = Pipeline(
        [
            transport.input(),
            rtvi,
            stt,
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )
    
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=False,
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        observers=[RTVIObserver(rtvi)],
    )
    
    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("👤 Client connected")
        messages.append({
            "role": "system",
            "content": "Greet the user warmly and let them know you can help them search their emails. Keep it brief."
        })
        await task.queue_frames([LLMRunFrame()])
        
    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info(f"👤 Client disconnected")
        await task.cancel()
        await session.close()
    
    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)
    
    logger.info("✅ Bot ready to accept connections!")
    
    try:
        await runner.run(task)
    finally:
        if not session.closed:
            await session.close()


async def bot(runner_args: RunnerArguments):
    logger.info("🌐 Creating transport...")
    transport_params = {
        "daily": lambda: DailyParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
            turn_analyzer=LocalSmartTurnAnalyzerV3(),
        ),
        "webrtc": lambda: TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
            turn_analyzer=LocalSmartTurnAnalyzerV3(),
        ),
    }

    transport = await create_transport(runner_args, transport_params)
    logger.info("✅ Transport created")

    await run_bot(transport, runner_args)


if __name__ == "__main__":
    # Initialize email services BEFORE starting Pipecat
    logger.info("=" * 80)
    logger.info("🚀 PRE-INITIALIZATION STARTING")
    logger.info("=" * 80)
    
    asyncio.run(initialize_email_services())
    
    logger.info("=" * 80)
    logger.info("✅ PRE-INITIALIZATION COMPLETE - Starting Pipecat")
    logger.info("=" * 80)
    
    # Now start Pipecat
    from pipecat.runner.run import main
    main()