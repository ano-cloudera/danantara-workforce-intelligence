from app.config import Settings
from app.services.data_gateway import DataGateway


def test_demo_data_loads():
    d = DataGateway(Settings(data_mode='demo'))
    assert len(d.list_candidates()) >= 3
    assert len(d.list_positions()) >= 2
