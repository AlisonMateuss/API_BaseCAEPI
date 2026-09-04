from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from Services.service_container import caService


scheduler = BackgroundScheduler(
    timezone="America/Sao_Paulo"
)


def iniciar_scheduler():
    if scheduler.running:
        return

    scheduler.add_job(
        caService._atualizarBaseDados,
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
