import pytest
from pydantic import ValidationError
from katana.gaia.oracle.models import SpecialistProfile

def test_specialist_profile_creation():
    """
    Tests that a SpecialistProfile can be created with valid data.
    """
    profile = SpecialistProfile(
        username="testuser",
        technical_skills=["python", "fastapi"],
        cognitive_score=0.8
    )
    assert profile.username == "testuser"
    assert profile.technical_skills == ["python", "fastapi"]
    assert profile.cognitive_score == 0.8

def test_specialist_profile_invalid_data():
    """
    Tests that a SpecialistProfile raises a ValidationError with invalid data.
    """
    with pytest.raises(ValidationError):
        SpecialistProfile(
            username="testuser",
            technical_skills=["python", "fastapi"],
            cognitive_score="invalid_score"  # cognitive_score should be a float
        )

    with pytest.raises(ValidationError):
        SpecialistProfile(
            username="testuser",
            technical_skills="not_a_list",  # technical_skills should be a list
            cognitive_score=0.8
        )

    with pytest.raises(ValidationError):
        SpecialistProfile(
            username=123,  # username should be a string
            technical_skills=["python", "fastapi"],
            cognitive_score=0.8
        )

def test_specialist_profile_missing_fields():
    """
    Tests that a SpecialistProfile raises a ValidationError if fields are missing.
    """
    with pytest.raises(ValidationError):
        SpecialistProfile(
            username="testuser",
            technical_skills=["python", "fastapi"]
            # cognitive_score is missing
        )

    with pytest.raises(ValidationError):
        SpecialistProfile(
            username="testuser",
            cognitive_score=0.8
            # technical_skills is missing
        )

    with pytest.raises(ValidationError):
        SpecialistProfile(
            technical_skills=["python", "fastapi"],
            cognitive_score=0.8
            # username is missing
        )
