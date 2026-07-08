"""
app/services/relationship_graph_service.py
──────────────────────────────────────────
Service for building investigation relationship graphs from PostgreSQL.
"""

import logging
import uuid
from typing import Dict, Any, List, Set, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.fir import FIR
from app.models.fir_entity import FIREntity
from app.services.similar_case_service import SimilarCaseService

logger = logging.getLogger(__name__)


class RelationshipGraphService:
    """
    Retrieves entities, cases, and similarities to build a Cytoscape-compatible
    node-edge JSON graph structure.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_case_graph(self, fir_id: uuid.UUID) -> Dict[str, Any]:
        """
        Builds and returns the relationship graph for a given FIR ID.
        Fetches the root FIR, its entities, similar cases, and similar cases' entities
        to construct a linked network graph.
        """
        # 1. Fetch root FIR
        fir_stmt = select(FIR).where(FIR.id == fir_id)
        fir_res = await self.db.execute(fir_stmt)
        root_fir = fir_res.scalar_one_or_none()
        if not root_fir:
            raise ValueError("FIR document not found.")

        # Initialize collections
        nodes_map: Dict[str, Dict[str, Any]] = {}
        edges_set: Set[Tuple[str, str, str]] = set()

        # Helper to generate clean node ID
        def get_node_id(entity_type: str, value: str) -> str:
            clean_val = value.strip().lower().replace(" ", "_")
            # Replace characters that might break cytoscape select
            for c in ["'", '"', ".", ",", "(", ")", "/"]:
                clean_val = clean_val.replace(c, "")
            return f"{entity_type}_{clean_val}"

        # Helper to add node
        def add_node(node_id: str, label: str, node_type: str, metadata: Dict[str, Any] = None) -> None:
            if node_id not in nodes_map:
                nodes_map[node_id] = {
                    "id": node_id,
                    "label": label,
                    "type": node_type,
                    "metadata": metadata or {},
                    "related_firs": set()
                }

        # Add root FIR node
        root_fir_node_id = f"fir_{str(root_fir.id)}"
        add_node(
            node_id=root_fir_node_id,
            label=root_fir.case_number,
            node_type="fir",
            metadata={
                "case_number": root_fir.case_number,
                "original_filename": root_fir.original_filename,
                "status": root_fir.status.value,
                "uploaded_at": root_fir.uploaded_at.isoformat()
            }
        )
        nodes_map[root_fir_node_id]["related_firs"].add(root_fir.case_number)

        # 2. Fetch similar cases
        similar_service = SimilarCaseService(self.db)
        similar_cases = []
        try:
            sim_res = await similar_service.get_similar_cases(fir_id, limit=5)
            similar_cases = sim_res.get("matches", [])
        except Exception as e:
            logger.warning("Could not fetch similar cases for graph: %s", e)

        # We will collect all FIR IDs in this graph (root + similar)
        fir_ids_to_fetch = [fir_id]
        similar_firs_by_id = {}
        
        for m in similar_cases:
            try:
                sim_uuid = uuid.UUID(m["fir_id"])
                fir_ids_to_fetch.append(sim_uuid)
                similar_firs_by_id[sim_uuid] = m
                
                # Add similar FIR node
                sim_node_id = f"fir_{str(sim_uuid)}"
                add_node(
                    node_id=sim_node_id,
                    label=m["case_number"],
                    node_type="fir",
                    metadata={
                        "case_number": m["case_number"],
                        "status": m["status"],
                        "similarity": f"{m['similarity']}%"
                    }
                )
                nodes_map[sim_node_id]["related_firs"].add(m["case_number"])
                
                # Add similarity edge
                edges_set.add((root_fir_node_id, sim_node_id, f"Similar ({m['similarity']}%)"))
            except Exception:
                pass

        # 3. Fetch all entities for all collected FIRs
        entities_stmt = select(FIREntity).where(FIREntity.fir_id.in_(fir_ids_to_fetch))
        entities_res = await self.db.execute(entities_stmt)
        all_entities = entities_res.scalars().all()

        # Group entities by FIR ID for local connection mapping
        entities_by_fir: Dict[uuid.UUID, List[FIREntity]] = {fid: [] for fid in fir_ids_to_fetch}
        for ent in all_entities:
            if ent.fir_id in entities_by_fir:
                entities_by_fir[ent.fir_id].append(ent)

        # Build nodes and edges for each FIR
        for fid in fir_ids_to_fetch:
            fir_node_id = f"fir_{str(fid)}"
            fir_obj = root_fir if fid == fir_id else None
            
            # Find case label
            case_label = root_fir.case_number
            if fid != fir_id and fid in similar_firs_by_id:
                case_label = similar_firs_by_id[fid]["case_number"]

            fir_entities = entities_by_fir[fid]
            
            # Categorize entities within this FIR to create local relationships
            suspects: List[str] = []
            victims: List[str] = []
            witnesses: List[str] = []
            weapons: List[str] = []
            vehicles: List[str] = []
            phones: List[str] = []
            locations: List[str] = []
            organizations: List[str] = []
            evidence_items: List[str] = []

            for ent in fir_entities:
                val = ent.entity_value.strip()
                if not val:
                    continue
                
                # Normalize types to match Cytoscape requirements
                raw_type = ent.entity_type
                node_type = "evidence"
                if raw_type in ["suspect", "victim", "witness", "person"]:
                    node_type = raw_type if raw_type != "person" else "suspect"  # fallback to suspect
                elif raw_type in ["phone", "email"]:
                    node_type = "phone"
                elif raw_type == "vehicle":
                    node_type = "vehicle"
                elif raw_type in ["location", "address"]:
                    node_type = "location"
                elif raw_type == "organization":
                    node_type = "organization"
                elif raw_type == "weapon":
                    node_type = "weapon"
                elif raw_type == "evidence":
                    node_type = "evidence"

                node_id = get_node_id(node_type, val)
                
                # Add node (duplicates will automatically merge because of nodes_map keys)
                add_node(
                    node_id=node_id,
                    label=val,
                    node_type=node_type,
                    metadata={"confidence": ent.confidence}
                )
                nodes_map[node_id]["related_firs"].add(case_label)

                # Connect Entity -> Appears In -> FIR
                edges_set.add((node_id, fir_node_id, "Appears In"))

                # Keep track of local list to draw cross-entity edges
                if node_type == "suspect":
                    suspects.append(node_id)
                elif node_type == "victim":
                    victims.append(node_id)
                elif node_type == "witness":
                    witnesses.append(node_id)
                elif node_type == "weapon":
                    weapons.append(node_id)
                elif node_type == "vehicle":
                    vehicles.append(node_id)
                elif node_type == "phone":
                    phones.append(node_id)
                elif node_type == "location":
                    locations.append(node_id)
                elif node_type == "organization":
                    organizations.append(node_id)
                elif node_type == "evidence":
                    evidence_items.append(node_id)

            # Draw logical local edges between entities inside this FIR
            # Suspect -> Uses -> Vehicle
            for s in suspects:
                for v in vehicles:
                    edges_set.add((s, v, "Uses"))
            
            # Suspect -> Owns -> Phone
            for s in suspects:
                for p in phones:
                    edges_set.add((s, p, "Owns"))

            # Suspect -> Used -> Weapon
            for s in suspects:
                for w in weapons:
                    edges_set.add((s, w, "Used"))

            # Suspect -> Member Of -> Organization
            for s in suspects:
                for o in organizations:
                    edges_set.add((s, o, "Member Of"))

            # Vehicle -> Seen At -> Location
            for v in vehicles:
                for l in locations:
                    edges_set.add((v, l, "Seen At"))

            # Weapon -> Used In -> FIR
            for w in weapons:
                edges_set.add((w, fir_node_id, "Used In"))

            # Evidence -> Found In -> FIR
            for ev in evidence_items:
                edges_set.add((ev, fir_node_id, "Found In"))

        # Convert nodes map to cytoscape format
        formatted_nodes = []
        for n_id, node in nodes_map.items():
            formatted_nodes.append({
                "id": node["id"],
                "label": node["label"],
                "type": node["type"],
                "metadata": {
                    **node["metadata"],
                    "related_firs": list(node["related_firs"])
                }
            })

        # Convert edges set to list
        formatted_edges = []
        for src, tgt, lbl in edges_set:
            formatted_edges.append({
                "source": src,
                "target": tgt,
                "label": lbl
            })

        return {
            "nodes": formatted_nodes,
            "edges": formatted_edges
        }
