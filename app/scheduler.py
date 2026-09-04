from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from Services.CAService import CAService


scheduler = BackgroundScheduler(
    timezone="America/Sao_Paulo"
)

ca_service = None


def iniciar_scheduler():
    global ca_service

    if scheduler.running:
        return

    ca_service = CAService()

    scheduler.add_job(
        ca_service._atualizarBaseDados,
        trigger=CronTrigger(
            hour=20,
            minute=10,
            timezone="America/Sao_Paulo"
        ),
        id="atualizar_base_caepi",
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )

    scheduler.start()

    print(
        "Scheduler iniciado. "
        "Atualização CAEPI programada para 20:10 "
        "America/Sao_Paulo."
    )


def parar_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
