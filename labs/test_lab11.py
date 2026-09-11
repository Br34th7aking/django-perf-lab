from config.routers import ReplicaRouter
from core.models import Tag


def test_router_splits_reads_and_writes():
    router = ReplicaRouter()
    assert router.db_for_read(Tag) == "replica"
    assert router.db_for_write(Tag) == "default"
    assert router.allow_migrate("default", "core") is True
    assert router.allow_migrate("replica", "core") is False


def test_anomaly_endpoint_cleans_up(client, db):
    # No replica in test settings: both reads hit the primary, so both are True.
    data = client.get("/labs/11/anomaly/").json()
    assert data["immediately_visible_on_primary"] is True
    assert Tag.objects.filter(name="anomaly-probe").count() == 0
