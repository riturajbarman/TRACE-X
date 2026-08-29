import uuid
from datetime import datetime, timezone

from app.domain.graph.service import GraphService
from app.domain.event.models import Event
from app.domain.detection.models import Detection, IOC, Incident


import pytest
from app.core.database import SessionLocal
from app.domain.case.models import Case, CaseStatus
from app.domain.evidence.models import Evidence

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def test_case(db_session):
    c = Case(title="Test Case", status=CaseStatus.OPEN, created_by="pytest")
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c

@pytest.fixture
def test_evidence(db_session, test_case):
    e = Evidence(case_id=test_case.id, name="test.evtx", sha256=str(uuid.uuid4())[:32], size_bytes=100)
    db_session.add(e)
    db_session.commit()
    db_session.refresh(e)
    return e

def test_build_graph_empty_case(db_session):
    """Test building a graph for an empty case returns 0 nodes/edges."""
    case_id = uuid.uuid4()
    service = GraphService(db_session)
    graph = service.build_graph(case_id)
    
    assert graph.case_id == case_id
    assert graph.node_count == 0
    assert graph.edge_count == 0
    assert graph.nodes == []
    assert graph.edges == []


def test_build_graph_fk_edges(db_session, test_case, test_evidence):
    """Test building a graph derives FK edges correctly."""
    # 1. Create Event
    ev1 = Event(
        case_id=test_case.id,
        evidence_id=test_evidence.id,
        event_type="process_exec",
        source="sysmon",
        timestamp=datetime.now(timezone.utc),
        data={"process_name": "cmd.exe"}
    )
    db_session.add(ev1)
    db_session.flush()

    # 2. Create Detection on Event
    det1 = Detection(
        case_id=test_case.id,
        event_id=ev1.id,
        detection_type="rule",
        rule_id="RULE_1",
        severity="HIGH",
        confidence=90
    )
    db_session.add(det1)

    # 3. Create IOC on Event
    ioc1 = IOC(
        case_id=test_case.id,
        event_id=ev1.id,
        evidence_id=test_evidence.id,
        ioc_type="ip",
        value="1.1.1.1",
        severity="HIGH",
        confidence=100
    )
    db_session.add(ioc1)
    db_session.flush()

    # 4. Create Incident clustering Event + Detection
    inc1 = Incident(
        case_id=test_case.id,
        title="Suspicious Command",
        severity="HIGH",
        confidence=90,
    )
    inc1.events.append(ev1)
    inc1.detections.append(det1)
    db_session.add(inc1)
    db_session.commit()

    # Test Graph
    service = GraphService(db_session)
    graph = service.build_graph(test_case.id)

    # Nodes: 1 Event, 1 Detection, 1 IOC, 1 Incident = 4
    assert graph.node_count == 4
    node_types = {n.type for n in graph.nodes}
    assert node_types == {"event", "detection", "ioc", "incident"}

    # Edges: 
    # Event->Detection (TRIGGERED)
    # Event->IOC (PRODUCED)
    # Event->Incident (PART_OF)
    # Detection->Incident (PART_OF)
    assert graph.edge_count == 4
    edge_rels = {(e.source, e.target, e.relationship) for e in graph.edges}
    
    assert (ev1.id, det1.id, "TRIGGERED") in edge_rels
    assert (ev1.id, ioc1.id, "PRODUCED") in edge_rels
    assert (ev1.id, inc1.id, "PART_OF") in edge_rels
    assert (det1.id, inc1.id, "PART_OF") in edge_rels


def test_build_graph_shared_entity_edges(db_session, test_case, test_evidence):
    """Test building a graph derives shared entity edges from JSONB."""
    
    # Event 1 with IP 10.0.0.1
    ev1 = Event(
        case_id=test_case.id,
        evidence_id=test_evidence.id,
        event_type="net_conn",
        source="sysmon",
        timestamp=datetime.now(timezone.utc),
        data={"ip": "10.0.0.1"}
    )
    
    # Event 2 with IP 10.0.0.1
    ev2 = Event(
        case_id=test_case.id,
        evidence_id=test_evidence.id,
        event_type="dns_query",
        source="sysmon",
        timestamp=datetime.now(timezone.utc),
        data={"ip": "10.0.0.1"}
    )
    
    # Event 3 with DIFFERENT IP
    ev3 = Event(
        case_id=test_case.id,
        evidence_id=test_evidence.id,
        event_type="net_conn",
        source="sysmon",
        timestamp=datetime.now(timezone.utc),
        data={"ip": "8.8.8.8"}
    )
    
    db_session.add_all([ev1, ev2, ev3])
    db_session.commit()

    service = GraphService(db_session)
    graph = service.build_graph(test_case.id, include_shared_entities=True)

    # 3 event nodes
    assert graph.node_count == 3
    
    # 1 edge: ev1 <-> ev2 (SHARES_ENTITY)
    assert graph.edge_count == 1
    edge = graph.edges[0]
    
    # The source is the hub (first inserted, so usually ev1), target is the other
    assert edge.relationship == "SHARES_ENTITY"
    assert {edge.source, edge.target} == {ev1.id, ev2.id}
    assert edge.label == "ip: 10.0.0.1"


def test_build_graph_filtering(db_session, test_case, test_evidence):
    """Test graph builder respects node_types filter."""
    
    ev1 = Event(
        case_id=test_case.id,
        evidence_id=test_evidence.id,
        event_type="test",
        source="test",
        timestamp=datetime.now(timezone.utc),
    )
    db_session.add(ev1)
    db_session.flush()

    det1 = Detection(
        case_id=test_case.id,
        event_id=ev1.id,
        detection_type="rule",
        severity="HIGH",
        confidence=90
    )
    db_session.add(det1)
    db_session.commit()

    service = GraphService(db_session)
    
    # Filter only events
    graph = service.build_graph(test_case.id, node_types=["event"])
    assert graph.node_count == 1
    assert graph.nodes[0].type == "event"
    assert graph.edge_count == 0  # Can't have event->detection if detection is filtered
