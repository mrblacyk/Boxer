from __future__ import absolute_import, unicode_literals
from django.conf import settings
from alphapwners.celery import app
# from libvirt import virConnect
from django.apps import apps


import logging

logger = logging.getLogger("celery")


@app.task
def stop_machine(domain_name: str,
        force: bool = False) -> None:
    if "aplibvirt" not in locals():
        import panel.aplibvirt as aplibvirt
    if "virt_conn" not in locals() or "INIT_SNAP_NAME" not in locals():
        from panel.views import virt_conn, INIT_SNAP_NAME
    _, _ = aplibvirt.stopMachine(virt_conn, domain_name, force)
    _ = aplibvirt.revertSnapshot(virt_conn, domain_name, INIT_SNAP_NAME)

    SimpleQueue = apps.get_model(app_label='panel', model_name='SimpleQueue')

    if SimpleQueue.objects.filter(vm__name=domain_name, type="stop"):
        sq = SimpleQueue.objects.get(vm__name=domain_name, type="stop")
        sq.delete()
        del sq
    return None


@app.task
def reset_machine(domain_name: str,
        force: bool = False) -> None:
    if "aplibvirt" not in locals():
        import panel.aplibvirt as aplibvirt
    if "virt_conn" not in locals() or "INIT_SNAP_NAME" not in locals():
        from panel.views import virt_conn, INIT_SNAP_NAME
    _, _ = aplibvirt.stopMachine(virt_conn, domain_name, force)
    _ = aplibvirt.revertSnapshot(virt_conn, domain_name, INIT_SNAP_NAME)
    _, _ = aplibvirt.startMachine(virt_conn, domain_name)

    SimpleQueue = apps.get_model(app_label='panel', model_name='SimpleQueue')

    if SimpleQueue.objects.filter(vm__name=domain_name, type="reset"):
        sq = SimpleQueue.objects.get(vm__name=domain_name, type="reset")
        sq.delete()
        del sq
    return None
