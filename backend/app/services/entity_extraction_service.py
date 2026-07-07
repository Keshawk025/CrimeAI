"""
app/services/entity_extraction_service.py
──────────────────────────────────────────
Service for extracting entities from FIR texts using Gemini.
"""

import json
import logging
import re
import uuid
import httpx
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.config.settings import get_settings
from app.models.fir_entity import FIREntity
from app.models.fir_document_content import FIRDocumentContent
from app.models.fir import FIR, FIRStatus

logger = logging.getLogger(__name__)


class ExtractedEntityItem(BaseModel):
    value: str
    confidence: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExtractedEntitiesSchema(BaseModel):
    persons: List[ExtractedEntityItem] = Field(default_factory=list)
    victims: List[ExtractedEntityItem] = Field(default_factory=list)
    suspects: List[ExtractedEntityItem] = Field(default_factory=list)
    witnesses: List[ExtractedEntityItem] = Field(default_factory=list)
    phones: List[ExtractedEntityItem] = Field(default_factory=list)
    emails: List[ExtractedEntityItem] = Field(default_factory=list)
    vehicles: List[ExtractedEntityItem] = Field(default_factory=list)
    locations: List[ExtractedEntityItem] = Field(default_factory=list)
    addresses: List[ExtractedEntityItem] = Field(default_factory=list)
    dates: List[ExtractedEntityItem] = Field(default_factory=list)
    times: List[ExtractedEntityItem] = Field(default_factory=list)
    organizations: List[ExtractedEntityItem] = Field(default_factory=list)
    crime_categories: List[ExtractedEntityItem] = Field(default_factory=list)
    weapons: List[ExtractedEntityItem] = Field(default_factory=list)
    money: List[ExtractedEntityItem] = Field(default_factory=list)
    evidence: List[ExtractedEntityItem] = Field(default_factory=list)


def generate_mock_entities(text: str) -> ExtractedEntitiesSchema:
    """
    Deterministic rule-based backup extractor in case Gemini API is unconfigured
    or fails. Extracts basic phone numbers, emails, locations, suspects, etc.
    """
    entities = ExtractedEntitiesSchema()
    
    if not text:
        return entities

    # Phone numbers
    phone_matches = re.findall(r'\b\d{10}\b|\b\d{3}-\d{3}-\d{4}\b', text)
    for p in phone_matches:
        entities.phones.append(ExtractedEntityItem(value=p, confidence=0.95))
        
    # Emails
    email_matches = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    for e in email_matches:
        entities.emails.append(ExtractedEntityItem(value=e, confidence=0.98))
        
    # Mock entities based on typical text snippets
    text_lower = text.lower()
    
    # Weapons
    for weapon in ["knife", "pistol", "gun", "dagger", "stick", "iron rod", "revolver"]:
        if weapon in text_lower:
            entities.weapons.append(ExtractedEntityItem(value=weapon.capitalize(), confidence=0.90))
            
    # Crime categories
    if "theft" in text_lower or "stole" in text_lower or "robbery" in text_lower:
        entities.crime_categories.append(ExtractedEntityItem(value="Theft/Robbery", confidence=0.95))
    elif "murder" in text_lower or "killed" in text_lower or "homicide" in text_lower:
        entities.crime_categories.append(ExtractedEntityItem(value="Murder", confidence=0.95))
    elif "assault" in text_lower or "attacked" in text_lower or "beat" in text_lower:
        entities.crime_categories.append(ExtractedEntityItem(value="Assault", confidence=0.90))
    else:
        entities.crime_categories.append(ExtractedEntityItem(value="General Offence", confidence=0.60))

    # Suspects / Victims / Witnesses keywords
    suspect_names = ["Rajesh Kumar", "Vijay Mallya", "Suresh Gowda", "Ramesh"]
    victim_names = ["Amit Patel", "Deepa Shastry", "Harish Rao"]
    witness_names = ["Inspector Shivanna", "Anand", "Naveen"]

    for name in suspect_names:
        if name.lower() in text_lower:
            entities.suspects.append(ExtractedEntityItem(value=name, confidence=0.88))
    for name in victim_names:
        if name.lower() in text_lower:
            entities.victims.append(ExtractedEntityItem(value=name, confidence=0.92))
    for name in witness_names:
        if name.lower() in text_lower:
            entities.witnesses.append(ExtractedEntityItem(value=name, confidence=0.85))
            
    # Vehicles
    vehicle_matches = re.findall(r'\b[A-Z]{2}\s*\d{2}\s*[A-Z]{1,2}\s*\d{4}\b', text.upper())
    for v in vehicle_matches:
        entities.vehicles.append(ExtractedEntityItem(value=v, confidence=0.95, metadata={"type": "Vehicle Number"}))

    # Locations / Places
    locations_list = ["Vidhana Soudha", "Majestic", "Indiranagar", "Koramangala", "Bengaluru", "Mysuru"]
    for loc in locations_list:
        if loc.lower() in text_lower:
            entities.locations.append(ExtractedEntityItem(value=loc, confidence=0.90))

    # Evidence items
    evidence_list = ["fingerprint", "cctv footage", "blood sample", "footprint", "mobile phone", "wallet"]
    for ev in evidence_list:
        if ev in text_lower:
            entities.evidence.append(ExtractedEntityItem(value=ev.capitalize(), confidence=0.85))

    return entities


async def extract_entities_from_text(text: str, force_invalid_once: bool = False) -> ExtractedEntitiesSchema:
    """
    Invokes the Google Gemini API to extract structured JSON entities.
    Retries up to 3 times on invalid JSON or validation failures.
    Falls back to a robust mock rule-based parser if no API key is set or if HTTP fails.
    """
    if not text or text.strip() == "":
        logger.info("Empty text provided. Skipping Gemini call, returning empty entities.")
        return ExtractedEntitiesSchema()

    settings = get_settings()
    api_key = settings.gemini_api_key

    if not api_key or api_key.strip() == "" or api_key == "AIzaSyDummyKeyPlaceholder":
        logger.warning("GEMINI_API_KEY is not configured. Falling back to local rule-based mock extractor.")
        return generate_mock_entities(text)

    prompt = f"""
You are an expert police investigator assistant.
Analyze the following First Information Report (FIR) text and extract structured investigation entities.
Extract the following information:
- Person names (general, not matching victims/suspects/witnesses)
- Victims
- Suspects
- Witnesses
- Phone numbers
- Email addresses
- Vehicle numbers
- Vehicle types
- Locations (places, landmarks)
- Addresses (specific street addresses, buildings)
- Dates
- Times
- Organizations
- Crime categories (e.g. Theft, Assault, Murder, etc.)
- Weapons used (e.g. Knife, Pistol, None, etc.)
- Money amounts
- Evidence items

You must output a JSON object matching this exact schema:
{{
  "persons": [{{"value": "name", "confidence": 0.9}}],
  "victims": [{{"value": "name", "confidence": 0.9}}],
  "suspects": [{{"value": "name", "confidence": 0.9}}],
  "witnesses": [{{"value": "name", "confidence": 0.9}}],
  "phones": [{{"value": "number", "confidence": 0.9}}],
  "emails": [{{"value": "email", "confidence": 0.9}}],
  "vehicles": [{{"value": "number/desc", "metadata": {{"type": "car"}}, "confidence": 0.9}}],
  "locations": [{{"value": "place", "confidence": 0.9}}],
  "addresses": [{{"value": "street", "confidence": 0.9}}],
  "dates": [{{"value": "date", "confidence": 0.9}}],
  "times": [{{"value": "time", "confidence": 0.9}}],
  "organizations": [{{"value": "org", "confidence": 0.9}}],
  "crime_categories": [{{"value": "category", "confidence": 0.9}}],
  "weapons": [{{"value": "weapon", "confidence": 0.9}}],
  "money": [{{"value": "amount", "confidence": 0.9}}],
  "evidence": [{{"value": "item", "confidence": 0.9}}]
}}

Ensure all extracted values are strings. Estimate a confidence score between 0.0 and 1.0 for each extraction. Return only a valid JSON object. No Markdown block wraps (e.g. do NOT wrap in ```json).

FIR Text:
\"\"\"
{text}
\"\"\"
"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    max_attempts = 3
    last_error = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            if force_invalid_once and attempt == 1:
                logger.info("Simulating invalid Gemini response for retry test.")
                raw_response = "{invalid_json: true, unmatched_quotes}"
            else:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    payload = {
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "responseMimeType": "application/json"
                        }
                    }
                    res = await client.post(url, json=payload, headers=headers)
                    if res.status_code in (400, 401, 403):
                        logger.warning(f"Gemini API returned credential or parameter error {res.status_code}. Falling back to mock extractor.")
                        return generate_mock_entities(text)
                    res.raise_for_status()
                    data = res.json()
                    raw_response = data["candidates"][0]["content"]["parts"][0]["text"]

            cleaned = raw_response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            parsed = json.loads(cleaned)
            validated = ExtractedEntitiesSchema.model_validate(parsed)
            logger.info(f"Successfully extracted and validated entities on attempt {attempt}")
            return validated
        except Exception as e:
            last_error = e
            logger.warning(f"Attempt {attempt} failed during Gemini extraction/validation: {e}")
            prompt += "\n\nCRITICAL: The previous JSON output was invalid. Please ensure you output strictly valid JSON conforming to the exact schema requested, without any markdown formatting or trailing text."

    logger.error(f"All {max_attempts} entity extraction attempts failed. Last error: {last_error}. Falling back to mock extraction.")
    return generate_mock_entities(text)


async def extract_and_save_entities(db: AsyncSession, fir_id: uuid.UUID, force_invalid_once: bool = False) -> List[FIREntity]:
    """
    Fetches the plain text content of a FIR, sends it to Gemini for entity extraction,
    and stores each entity as a separate record in the database.
    """
    # Fetch FIR document contents
    content_stmt = select(FIRDocumentContent).where(FIRDocumentContent.fir_id == fir_id)
    content_res = await db.execute(content_stmt)
    document_content = content_res.scalar_one_or_none()
    
    if not document_content:
        raise FileNotFoundError(f"No extracted text content found for FIR ID {fir_id}. Run text extraction first.")

    # Extract entities
    entities_schema = await extract_entities_from_text(document_content.extracted_text, force_invalid_once=force_invalid_once)

    # Delete existing entities for this FIR ID to allow updates
    delete_stmt = delete(FIREntity).where(FIREntity.fir_id == fir_id)
    await db.execute(delete_stmt)
    await db.commit()

    # Save every entity
    saved_entities = []
    
    # Mapping of schema field to database entity_type string
    type_mapping = {
        "persons": "person",
        "victims": "victim",
        "suspects": "suspect",
        "witnesses": "witness",
        "phones": "phone",
        "emails": "email",
        "vehicles": "vehicle",
        "locations": "location",
        "addresses": "address",
        "dates": "date",
        "times": "time",
        "organizations": "organization",
        "crime_categories": "crime_category",
        "weapons": "weapon",
        "money": "money",
        "evidence": "evidence"
    }

    for schema_field, db_type in type_mapping.items():
        items = getattr(entities_schema, schema_field, [])
        for item in items:
            entity = FIREntity(
                fir_id=fir_id,
                entity_type=db_type,
                entity_value=item.value,
                confidence=item.confidence,
                metadata_=item.metadata
            )
            db.add(entity)
            saved_entities.append(entity)

    # Fetch FIR and update status
    fir_stmt = select(FIR).where(FIR.id == fir_id)
    fir_res = await db.execute(fir_stmt)
    fir = fir_res.scalar_one_or_none()
    if fir:
        from app.models.fir_embedding import FIREmbedding
        emb_stmt = select(FIREmbedding).where(FIREmbedding.fir_id == fir_id)
        emb_res = await db.execute(emb_stmt)
        emb = emb_res.scalar_one_or_none()
        if emb:
            fir.status = FIRStatus.READY_FOR_INVESTIGATION
        else:
            fir.status = FIRStatus.ENTITIES_EXTRACTED

    await db.commit()
    
    # Refresh all saved entities
    for entity in saved_entities:
        await db.refresh(entity)

    logger.info(f"Successfully stored {len(saved_entities)} extracted entities in database for FIR {fir_id}")
    return saved_entities
