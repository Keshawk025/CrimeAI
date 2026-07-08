"""
app/services/investigation_recommendation_service.py
────────────────────────────────────────────────────
Service to generate actionable investigation recommendations using Gemini.
"""

import json
import logging
import uuid
import os
from typing import Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.fir import FIR
from app.models.fir_document_content import FIRDocumentContent
from app.models.fir_entity import FIREntity
from app.services.similar_case_service import SimilarCaseService
from app.integrations.enkrypt.validator import validate_prompt, validate_output

logger = logging.getLogger(__name__)


class InvestigationRecommendationService:
    """
    Builds the case context, triggers Gemini (or fallbacks) to prioritize,
    score, and explain investigative recommendations.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate_recommendations(self, fir_id: uuid.UUID) -> Dict[str, Any]:
        """
        Builds FIR context and gets prioritized next steps from Gemini or a local parser.
        """
        # 1. Fetch FIR details
        fir_stmt = select(FIR).where(FIR.id == fir_id)
        fir_res = await self.db.execute(fir_stmt)
        fir = fir_res.scalar_one_or_none()
        if not fir:
            raise ValueError("FIR document not found.")

        # 2. Fetch extracted plain text
        txt_stmt = select(FIRDocumentContent).where(FIRDocumentContent.fir_id == fir_id)
        txt_res = await self.db.execute(txt_stmt)
        doc_content = txt_res.scalar_one_or_none()
        fir_text = doc_content.extracted_text if doc_content else ""

        # Check for empty FIR / insufficient info
        if not fir_text.strip() or len(fir_text.split()) < 8:
            return {"recommendations": [], "message": "Not enough evidence to generate reliable recommendations."}

        # 3. Fetch entities
        ent_stmt = select(FIREntity).where(FIREntity.fir_id == fir_id)
        ent_res = await self.db.execute(ent_stmt)
        entities = ent_res.scalars().all()
        entities_str = "\n".join([f"- {e.entity_type}: {e.entity_value} (conf={e.confidence})" for e in entities])

        # 4. Fetch similar cases
        similar_service = SimilarCaseService(self.db)
        similar_cases_str = "None found"
        try:
            sim_res = await similar_service.get_similar_cases(fir_id, limit=3)
            matches = sim_res.get("matches", [])
            if matches:
                similar_cases_str = "\n".join([
                    f"- {m['case_number']}: similarity={m['similarity']}%, category={m['crime_category']}, reasons={m['matching_reasons']}"
                    for m in matches
                ])
        except Exception as e:
            logger.warning("Could not fetch similar cases for recommendations context: %s", e)

        # 5. Build prompt context
        crime_cat = "Unknown"
        for e in entities:
            if e.entity_type == "crime_category":
                crime_cat = e.entity_value
                break

        context = f"""
Case Number: {fir.case_number}
Original Filename: {fir.original_filename}
Crime Category: {crime_cat}

Extracted Plain Text:
\"\"\"
{fir_text}
\"\"\"

Extracted Entities:
{entities_str or "None"}

Similar Cases:
{similar_cases_str}
"""

        # Generate using Gemini (or fallback rule engine if key is not configured)
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key or api_key.startswith("your_") or api_key == "dummy":
            logger.info("Gemini key unavailable; executing local rule engine for recommendations.")
            return self._generate_fallback_recommendations(fir_text, entities, similar_cases_str)

        # Triggers live Gemini API call
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            
            prompt = f"""
You are an AI Criminal Investigator assisting a police detective.
Analyze the following case context and output a JSON list of prioritized, actionable investigation next steps.

CASE CONTEXT:
\"\"\"
{context}
\"\"\"

RULES:
1. Recommend ONLY actions directly supported by available evidence in the text or entities.
2. Never invent suspects or fabricate evidence.
3. If the context does not contain enough detailed information to generate reliable recommendations, respond with exactly: "Not enough evidence to generate reliable recommendations."
4. Every recommendation MUST belong to one of these categories: "Evidence Collection", "Witness Actions", "Location Investigation", "Suspect Investigation".
5. Assign a priority: "High", "Medium", or "Low".
6. Assign a confidence score (an integer in [0, 100]) expressing your confidence in the lead.
7. Return a valid JSON object matching the schema below. Do not wrap in markdown blocks, just raw JSON.

Response format:
{{
  "recommendations": [
    {{
      "title": "Clean concise action title",
      "priority": "High/Medium/Low",
      "confidence": 90,
      "reason": "Specific justification based on evidence or similar cases.",
      "category": "Evidence Collection"
    }}
  ]
}}
"""
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            resp_text = response.text.strip()
            
            # Clean JSON markers if present
            if resp_text.startswith("```"):
                lines = resp_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                resp_text = "\n".join(lines).strip()

            if "Not enough evidence to generate reliable recommendations" in resp_text:
                return {"recommendations": [], "message": "Not enough evidence to generate reliable recommendations."}

            data = json.loads(resp_text)
            return data

        except Exception as e:
            logger.exception("Failed to generate recommendations via Gemini API: %s", e)
            # Fallback to local rule engine on model failure
            return self._generate_fallback_recommendations(fir_text, entities, similar_cases_str)

    def _generate_fallback_recommendations(
        self, fir_text: str, entities: List[FIREntity], similar_cases_str: str
    ) -> Dict[str, Any]:
        """Offline backup parser to return structured recommendations based on entity keywords."""
        t_low = fir_text.lower()
        
        # Insufficient check
        if len(fir_text.split()) < 15:
            return {"recommendations": [], "message": "Not enough evidence to generate reliable recommendations."}

        recommendations = []

        # Find suspects, weapons, vehicles
        suspects = [e.entity_value for e in entities if e.entity_type == "suspect"]
        vehicles = [e.entity_value for e in entities if e.entity_type == "vehicle"]
        weapons = [e.entity_value for e in entities if e.entity_type == "weapon"]
        locations = [e.entity_value for e in entities if e.entity_type == "location" or e.entity_type == "address"]
        phones = [e.entity_value for e in entities if e.entity_type == "phone"]

        # Category: Evidence Collection
        if "cctv" in t_low or "camera" in t_low or "shop" in t_low or "robbery" in t_low:
            recommendations.append({
                "title": "Collect CCTV Footage",
                "priority": "High",
                "confidence": 92,
                "reason": "Examine footage near the crime scene to identify suspects or get vehicle numbers.",
                "category": "Evidence Collection"
            })
        
        if phones:
            recommendations.append({
                "title": f"Obtain Call Detail Records (CDR) for {phones[0]}",
                "priority": "High",
                "confidence": 88,
                "reason": f"Analyze call logs and tower location histories for mobile {phones[0]}.",
                "category": "Evidence Collection"
            })
        elif "call" in t_low or "phone" in t_low or "mobile" in t_low:
            recommendations.append({
                "title": "Obtain Call Detail Records",
                "priority": "Medium",
                "confidence": 80,
                "reason": "Verify call detail history and cell-tower logs of interest.",
                "category": "Evidence Collection"
            })

        # Category: Suspect Investigation
        if suspects:
            recommendations.append({
                "title": f"Verify Alibi of Suspect {suspects[0]}",
                "priority": "High",
                "confidence": 95,
                "reason": f"Investigate the location and movement details of {suspects[0]} during the time of the incident.",
                "category": "Suspect Investigation"
            })
            recommendations.append({
                "title": f"Cross-check Criminal Associates of {suspects[0]}",
                "priority": "Medium",
                "confidence": 85,
                "reason": f"Query existing databases for past crimes involving {suspects[0]} or known associates.",
                "category": "Suspect Investigation"
            })
        else:
            recommendations.append({
                "title": "Identify Potential Suspects",
                "priority": "Medium",
                "confidence": 75,
                "reason": "Analyze crime patterns and modus operandi in similar cases to identify possible suspects.",
                "category": "Suspect Investigation"
            })

        # Category: Location Investigation
        if locations:
            recommendations.append({
                "title": f"Examine Crime Scene in {locations[0]}",
                "priority": "High",
                "confidence": 90,
                "reason": f"Conduct physical forensics sweep and gather localized eye-witness accounts at {locations[0]}.",
                "category": "Location Investigation"
            })
        else:
            recommendations.append({
                "title": "Conduct Scene of Crime Investigation",
                "priority": "High",
                "confidence": 85,
                "reason": "Visit physical scene immediately to retrieve trace evidence.",
                "category": "Location Investigation"
            })

        # Category: Witness Actions
        if "victim" in t_low or "witness" in t_low:
            recommendations.append({
                "title": "Detailed Interview of Witnesses",
                "priority": "High",
                "confidence": 90,
                "reason": "Re-interview victims and eyewitnesses to resolve discrepancies in descriptions.",
                "category": "Witness Actions"
            })

        # Default fallback if nothing matches
        if not recommendations:
            recommendations.append({
                "title": "Collect Local Intelligence",
                "priority": "Medium",
                "confidence": 70,
                "reason": "Query local informants regarding recent crime waves.",
                "category": "Evidence Collection"
            })

        return {"recommendations": recommendations}
